# Primary references and investigation guide

Sources consulted for the starter design on 2026-10-23. Repository pages and documentation can evolve; implementation must record exact dependency versions/commits and consult their matching documentation. The scope and architecture in this pack are proposed engineering choices.

| Source | Use |
| --- | --- |
| [pyuvm repository](https://github.com/pyuvm/pyuvm) | Project purpose, implemented UVM areas, examples and public code |
| [pyuvm documentation](https://pyuvm.readthedocs.io/en/latest/) | Validate concrete APIs against the selected release |
| [cocotb documentation](https://docs.cocotb.org/en/stable/) | Runner, tasks, simulator access and supported platform details |
| [cocotb timing model](https://docs.cocotb.org/en/stable/timing_model.html) | Scheduling and signal-sampling semantics |
| [PyVSC repository](https://github.com/fvutils/pyvsc) | Candidate stimulus and functional coverage backend |
| [cocotb-coverage repository](https://github.com/mciepluc/cocotb-coverage) | Alternative functional coverage and constrained-random backend |
| [PyUCIS repository](https://github.com/fvutils/pyucis) | Candidate UCIS integration for later qualification |
| [Accellera UVM](https://www.accellera.org/downloads/standards/uvm) | UVM reference material; no compliance claim implied |
| [Accellera UCIS](https://www.accellera.org/downloads/standards/ucis) | Coverage interchange semantics |
| [Icarus source](https://github.com/steveicarus/iverilog) | Compiler/runtime implementation and contribution rules |
| [Icarus flags](https://steveicarus.github.io/iverilog/usage/command_line_flags.html) | Language selection and assertion/specify controls; verify actual runtime behavior |
| [Icarus quirks](https://steveicarus.github.io/iverilog/usage/icarus_verilog_quirks.html) | Documented semantic differences to consider in probes |
| [Arm AMBA specifications](https://developer.arm.com/Architectures/AMBA) | Locate and identify the APB specification used by the pilot |

pyuvm's project description establishes a Python UVM implementation layered on cocotb; it is not evidence that every UVM feature is implemented in a given release. PyVSC and PyUCIS are existing projects to evaluate, not prequalified dependencies. cocotb's timing model establishes the need for explicit scheduling; the pilot still needs protocol-specific sampling validation.

## M0 evidence to add

For each selected dependency, record package/version/commit, official documentation URL, license identifier from the actual source, install platform, public APIs exercised, probe command/result and known limitations. Separate a dependency that merely installs from one that passes the required behavior probe.

Record an APB specification document identifier/revision and the supported signal subset before implementation claims protocol compliance. Link the exact tool documentation used for any later SDF, structural coverage or UCIS integration. Do not infer simulator support from cocotb support alone.
