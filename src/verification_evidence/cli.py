import argparse
import json
import sys
from .model import EvidenceError, load, dump
from .core import merge, summarize, validate


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
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
