# RLM rule

The `rlm` and `rlm_subquery` tools are installed and available.
Before using `read`, `grep`, or `glob` repeatedly, assess whether the input is
large. You MUST call `rlm` first when a task involves a log, a directory,
repository-wide search, an unknown-size file, or more than two related files.
Use `read` and `grep` directly only for one or two known small files and
precise follow-up slices. Do not perform repeated read/grep loops over a large
input. Use `rlm_subquery` only when a real extracted slice needs semantic
judgement that Python cannot express.
