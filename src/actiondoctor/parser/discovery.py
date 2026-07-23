"""Deterministic GitHub Actions workflow discovery."""

from pathlib import Path

WORKFLOW_DIRECTORY = Path(".github") / "workflows"
SUPPORTED_WORKFLOW_SUFFIXES = frozenset({".yml", ".yaml"})


def workflow_directory(repository_path: Path) -> Path:
    """Return the conventional workflow directory for a repository."""
    return repository_path / WORKFLOW_DIRECTORY


def discover_workflow_files(repository_path: Path) -> list[Path]:
    """Find supported workflow files directly inside the workflow directory."""
    directory = workflow_directory(repository_path)
    if not directory.is_dir():
        return []

    workflows = (
        path
        for path in directory.iterdir()
        if not path.is_symlink()
        and path.is_file()
        and path.suffix.lower() in SUPPORTED_WORKFLOW_SUFFIXES
    )
    return sorted(workflows, key=lambda path: (path.name.casefold(), path.name))
