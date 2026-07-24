"""Safe atomic report-file output."""

import os
import tempfile
from contextlib import suppress
from pathlib import Path


class ReportWriteError(OSError):
    """Raised when a completed report cannot be atomically written."""


def write_report_atomic(path: Path, content: str) -> None:
    """Write UTF-8 content through a same-directory temporary replacement."""
    if path.exists() and path.is_dir():
        raise ReportWriteError(f"Output path is a directory: {path}")

    temporary_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
        temporary_path = None
    except OSError as error:
        raise ReportWriteError(f"Could not write report to {path}: {error}") from error
    finally:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)
