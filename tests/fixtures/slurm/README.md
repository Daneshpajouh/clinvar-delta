# Slurm fixtures

These files were written by hand in the `sacct --parsable2` format documented at
https://slurm.schedmd.com/sacct.html (fields separated by `|`, no trailing `|`; times as
`[days-]hours:minutes:seconds[.microseconds]`). They are not output from a real cluster:
this project has not yet been run on Slurm. Field order matches `cvnf.profiling.SACCT_FIELDS`:

    sacct -j <ids> --parsable2 --noheader \
      --format=JobID,JobName,State,ExitCode,Elapsed,Timelimit,AllocCPUS,TotalCPU,ReqMem,MaxRSS
