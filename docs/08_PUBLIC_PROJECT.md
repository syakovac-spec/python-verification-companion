# Public package and upstream strategy

## Proposed boundary

Maintain a separate companion package and contribute narrowly scoped fixes to existing projects. Build on public interfaces and coordinate significant shared changes before depending on them. Maintainer acceptance and project roadmaps have not been established by these documents.

| Work | Likely destination |
| --- | --- |
| Standard UVM behavior, phases, sequencing and register core fixes | pyuvm |
| Python-side simulator integration defects | cocotb |
| Missing required SV semantics, native event/VPI/timing defects | Icarus Verilog, after minimal reproducer and layer diagnosis |
| Constraint engine or coverage primitive defects | Selected coverage/constraint project |
| UCIS library defects | Selected UCIS project |
| Requirements/evidence semantics, run manifests, replay and closure reporting | Companion package |
| APB reference environment and reusable methodology examples | Companion package initially; share upstream examples by agreement |

Avoid a permanent dependency fork. If a public API needs extension, document the use case and propose a focused change. A local compatibility adapter is acceptable when its version bounds and removal condition are explicit.

## First public repository contents

Working code and tests; one complete pilot; installation instructions; an evidence example; a support matrix; architecture and schema docs; contribution instructions; limitations; release notes and an owner-selected license. Keep one repository until independently reusable components justify splitting it.

Use a descriptive project identity. Explain that it complements cocotb/pyuvm and identify what it adds. Do not imply official endorsement, complete IEEE compliance, universal simulator support or signoff certification.

## License decision

Owner decision required before public distribution. Record project ownership and intended license, inspect actual dependency/source licenses, preserve notices and avoid copying incompatible material. Do not choose a license based solely on the fact that dependencies are public. This starter pack makes no license selection.

## Maintainer discussion outline

Prepare a short proposal describing the evidence problem, the companion boundary, proposed adapter points, the working pilot and any required upstream changes. Ask about overlap and preferred integration direction. Keep the proposal concrete enough for maintainers to review. This document is an outline, not authorization to send a message.

## Maintenance policy

Pin tested development environments; define supported version ranges from executed combinations. Version serialized schemas independently of Python APIs. Treat changes in checker/bin semantics as new verification baselines. Preserve replay fixtures across releases and explain when a historical run requires its historical environment.
