import argparse
import json
import sys
from .model import EvidenceError, load, dump
from .core import merge, summarize, validate


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ('export-ucis', 'merge-ucis', 'validate-ucis'):
        from .ucis import export_ucis, load_export, check_projection
        parser = argparse.ArgumentParser(description='Export/merge checked functional UCIS coverage with evidence sidecars')
        parser.add_argument('inputs', nargs='+')
        parser.add_argument('--output')
        parser.add_argument('--roundtrip', help='Tool-reexported UCIS XML to compare with one export')
        args = parser.parse_args(argv[1:])
        try:
            if argv[0] == 'validate-ucis':
                if args.output or (args.roundtrip and len(args.inputs) != 1):
                    parser.error('validate-ucis takes no output; roundtrip requires one export')
                bundles = [load_export(path) for path in args.inputs]
                result = check_projection(bundles[0], args.roundtrip) if args.roundtrip else dict(status='valid', exports=len(bundles))
            else:
                if not args.output or args.roundtrip:
                    parser.error('export/merge requires --output and does not accept --roundtrip')
                loader = load if argv[0] == 'export-ucis' else load_export
                result = export_ucis([loader(path) for path in args.inputs], args.output)
            print(json.dumps(result, sort_keys=True))
            return 0
        except (EvidenceError, ValueError, TypeError, KeyError) as exc:
            print(json.dumps({'status': 'invalid', 'error': str(exc)}), file=sys.stderr)
            return 2
        except OSError as exc:
            print(json.dumps({'status': 'infrastructure_error', 'error': str(exc)}), file=sys.stderr)
            return 4
    if argv and argv[0] == 'create-agent':
        from .scaffold import create_agent
        generator = argparse.ArgumentParser(description='Generate an editable ready/valid agent kit')
        generator.add_argument('--interface', required=True)
        generator.add_argument('--output', required=True)
        options = generator.parse_args(argv[1:])
        try:
            print(json.dumps(create_agent(options.interface, options.output), sort_keys=True))
            return 0
        except (ValueError, TypeError, KeyError) as exc:
            print(json.dumps({'status': 'invalid', 'error': str(exc)}), file=sys.stderr)
            return 2
        except OSError as exc:
            print(json.dumps({'status': 'infrastructure_error', 'error': str(exc)}), file=sys.stderr)
            return 4
    parser = argparse.ArgumentParser(description="Validate and assess verification evidence")
    parser.add_argument("operation", choices=["validate", "summarize", "gaps", "merge"])
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--output", help="Merged bundle destination (merge only)")
    args = parser.parse_args(argv)
    try:
        bundles = [validate(load(path)) for path in args.inputs]
        if args.operation == "validate":
            result, code = {"status": "valid", "files": len(bundles)}, 0
        else:
            bundle = merge(bundles)
            if args.operation == "merge":
                if not args.output:
                    raise EvidenceError("merge requires --output")
                dump(bundle, args.output)
                result, code = {"status": "merged", "runs": len(bundle.runs), "output": args.output}, 0
            else:
                result = summarize(bundle)
                code = {"pass": 0, "failed": 1, "incomplete": 3, "infrastructure_error": 4}[result["gate"]]
                if args.operation == "gaps":
                    result["obligations"] = [o for o in result["obligations"] if o["status"] not in {"satisfied", "not_applicable"}]
        if args.json_output:
            print(json.dumps(result, sort_keys=True))
        elif "gate" in result:
            print("Gate:", result["gate"])
            for req in result["requirements"]:
                print(f"{req['id']}: {req['status']}; missing={','.join(req['missing_obligations']) or '-'}")
            for ob in result["obligations"]:
                print(f"  {ob['id']}: {ob['status']} observed={ob['counts']['observed']} eligible={ob['eligible_checked_pass']}/{ob['goal']}")
            print("Coverage:", json.dumps(result["coverage"]))
            print("Unavailable metrics:", json.dumps(result["metrics"]))
        else:
            print(json.dumps(result, sort_keys=True))
        return code
    except (EvidenceError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}), file=sys.stderr)
        return 2
    except OSError as exc:
        print(json.dumps({"status": "infrastructure_error", "error": str(exc)}), file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
