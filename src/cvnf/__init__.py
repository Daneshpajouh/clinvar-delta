import sys

# Checked here because pipeline tasks run `python3 -m cvnf` with whatever python3 is on
# PATH, and the first failure would otherwise be an ImportError for enum.StrEnum.
if sys.version_info < (3, 11):  # noqa: UP036
    found = sys.version.split()[0]
    raise SystemExit(f"cvnf needs Python 3.11 or newer; {sys.executable} is {found}")

__version__ = "1.0.1"
