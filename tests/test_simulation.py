import argparse
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch, Mock
from verification_evidence import simulation


class SimulationTests(unittest.TestCase):
    def test_selected_backend_has_no_icarus_flags(self):
        with patch.dict(os.environ, {"SIM": "vcs", "PVC_BUILD_ARGS": "[]"}):
            self.assertEqual(simulation.build_flags(), [])
        with patch.dict(os.environ, {"SIM": "icarus", "PVC_BUILD_ARGS": '["-Wall"]'}):
            self.assertEqual(simulation.build_flags(), ["-g2012", "-Wall"])

    def test_worker_retains_user_options(self):
        with patch.dict(os.environ, {"SIM": "vcs", "PVC_BUILD_ARGS": '["-full64"]'}):
            parser = argparse.ArgumentParser()
            simulation.configure(parser)
            simulation.select(parser.parse_args([]))
            self.assertEqual(simulation.build_flags(), ["-full64"])

    def test_vcs_command_uses_vcs_parameters_and_active_cocotb(self):
        config = types.ModuleType("cocotb_tools.config")
        config.makefiles_dir = Path("/active-conda/cocotb/makefiles")
        with patch.dict("sys.modules", {"cocotb_tools.config": config}), patch.dict(os.environ, {"SIM": "vcs", "PVC_BUILD_ARGS": "[]", "PVC_TEST_ARGS": "[]"}):
            cmd = simulation.vcs_make_command(sources=[Path("design.sv")], top="top",
                parameters={"DEPTH": 4}, out=Path("/out"), module="test_top", plusargs=[])
        self.assertIn("SIM=vcs", cmd)
        self.assertIn("COMPILE_ARGS=-pvalue+top.DEPTH=4", cmd)
        self.assertNotIn("-g2012", " ".join(cmd))
        self.assertIn(str(Path("/active-conda/cocotb/makefiles/Makefile.sim")), cmd)

    def test_runner_preserves_conda_environment(self):
        runner = Mock()
        module = types.ModuleType("cocotb_tools.runner")
        module.get_runner = Mock(return_value=runner)
        env = {"SIM": "questa", "CONDA_PREFIX": "/user/conda", "PVC_BUILD_ARGS": "[]", "PVC_TEST_ARGS": "[]"}
        with tempfile.TemporaryDirectory() as directory, patch.dict("sys.modules", {"cocotb_tools.runner": module}), patch.dict(os.environ, env):
            before = os.environ.get("VIRTUAL_ENV")
            simulation.run(sources=[Path("top.sv")], top="top", parameters={}, out=directory,
                           module="test_top", test_dir=Path(directory), extra_env={})
            self.assertEqual(os.environ.get("VIRTUAL_ENV"), before)
            self.assertEqual(os.environ["CONDA_PREFIX"], "/user/conda")
            module.get_runner.assert_called_once_with("questa")
            self.assertTrue((Path(directory) / "timing.json").exists())

    def test_missing_selected_tool_is_actionable(self):
        with patch.dict(os.environ, {"SIM": "vcs"}), patch.object(simulation.metadata, "version", return_value="2"), patch.object(simulation.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "vcs.*unavailable"):
                simulation.identity()
