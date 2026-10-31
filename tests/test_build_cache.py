import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from verification_evidence.build_cache import dependencies, descriptor, digest, materialize


class BuildCacheTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform=='linux','Linux process lock')
    def test_two_processes_build_once(self):
        import multiprocessing
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def worker(name):
                target=root/name
                def build():
                    with (root/'calls').open('a') as log: log.write('build\n')
                    target.mkdir(); (target/'artifact').write_text('compiled')
                result=materialize(root/'cache',lambda:{'source':'shared'},target,build)
                (root/(name+'.json')).write_text(json.dumps(result))
            context=multiprocessing.get_context('fork')
            children=[context.Process(target=worker,args=(name,)) for name in ('one','two')]
            for child in children: child.start()
            for child in children:
                child.join(10); self.assertEqual(child.exitcode,0)
            self.assertEqual((root/'calls').read_text(),'build\n')
            self.assertEqual({json.loads((root/(n+'.json')).read_text())['status'] for n in ('one','two')},{'hit','miss'})

    def test_include_parameter_define_tool_and_flag_invalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'top.sv'; header=root/'defs.svh'
            source.write_text('`include "defs.svh"\nmodule top; endmodule')
            header.write_text('`define N 1')
            base=descriptor([source], [], {}, 'top', {}, [], {'simulator':'test'})
            first=digest(base)
            header.write_text('`define N 2')
            self.assertNotEqual(first, digest(descriptor([source], [], {}, 'top', {}, [], {'simulator':'test'})))
            for key in ('parameters','defines','tools','flags','top'):
                changed=dict(base); changed[key]='changed'
                self.assertNotEqual(first,digest(changed))
            source.write_text('`include HEADER')
            with self.assertRaises(ValueError): dependencies([source])

    def test_seed_does_not_change_build_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'top.sv'; p.write_text('module top; endmodule')
            with patch.dict(os.environ, {'RANDOM_SEED':'1', 'WSL_INTEROP':'session-one', 'SHLVL':'1', '_':'python'}):
                first=descriptor([p], [], {}, 'top', {}, [], {})
            with patch.dict(os.environ, {'RANDOM_SEED':'2', 'WSL_INTEROP':'session-two', 'SHLVL':'2', '_':'bash'}):
                self.assertEqual(first, descriptor([p], [], {}, 'top', {}, [], {}))
            with patch.dict(os.environ, {'CXXFLAGS':'-DCHANGED'}):
                self.assertNotEqual(first, descriptor([p], [], {}, 'top', {}, [], {}))

    @unittest.skipUnless(sys.platform=='linux','Linux process lock')
    def test_hit_corruption_and_failed_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); cache=root/'cache'; calls=[]
            def run(name, fail=False):
                target=root/name
                def build():
                    calls.append(name)
                    if fail: raise RuntimeError('compiler failed')
                    target.mkdir(); (target/'artifact').write_text('compiled')
                return materialize(cache,lambda:{'source':'one'},target,build)
            first=run('first'); self.assertEqual(first['status'],'miss')
            self.assertEqual(run('second')['status'],'hit')
            (root/'second/artifact').write_text('private mutation')
            self.assertEqual((cache/first['key']/'build/artifact').read_text(),'compiled')
            (cache/first['key']/'build/artifact').write_text('corrupted')
            self.assertEqual(run('third')['status'],'miss')
            self.assertEqual(calls,['first','third'])
            def fail(): raise RuntimeError('compiler failed')
            with self.assertRaises(RuntimeError): materialize(cache,lambda:{'new':True},root/'failed',fail)
            self.assertFalse((cache/digest({'new':True})).exists())
