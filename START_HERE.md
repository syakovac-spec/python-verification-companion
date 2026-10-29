# Start here

For planned future work, use [the prioritized extension TODO backlog](docs/20_EXTENSION_BACKLOG.md). Its unchecked items are proposals to implement and qualify, not shipped capabilities.

Follow README.md for installation and verification commands. Read STATUS.md for completed scope and docs/06_IMPLEMENTATION_PLAN.md for the next milestone. M0–M4 are already implemented; do not restart them from the historical design prompts. Follow AGENTS.md when changing code.

For a different DUT, bus or interface, start with docs/17_EXTENDING_TO_OTHER_INTERFACES.md and the executable examples/ready_valid environment. It maps standard UVM components to code and includes an agent handoff prompt. Toolchain reproduction is in docs/18_TOOLCHAIN_QUALIFICATION.md.

For VCS or another simulator, an existing conda environment, or constraint-solver profiling, read docs/19_SIMULATOR_PORTABILITY.md. Never assume a cocotb RisingEdge callback exposes pre-update values; use the documented HDL snapshot sampling contract for acceptance checks.
