# Contributing

Read AGENTS.md and the evidence contract before changing behavior. Run `python -m unittest discover -s tests -v` for core changes. For simulation changes, run the directed, M3 and M4 suites in the recorded environment and retain their qualification results.

Preserve independent sampled checking, X/Z values, negative outcomes and pending operations. Do not weaken thresholds to close coverage. Changes to checker or bin semantics require a distinct evidence identity. Do not commit virtual environments, credentials, generated simulator builds or raw machine-specific logs.

Keep source changes focused and describe the problem, implementation, executed tests and limitations. This project uses the MIT license in LICENSE. Contributions should use that license. Dependencies retain their own licenses.
