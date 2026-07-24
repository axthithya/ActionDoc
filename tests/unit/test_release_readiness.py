"""Release-readiness contracts for the public v0.1.0 surface."""

import re
import tomllib
from pathlib import Path

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[2]
SHA_PATTERN = re.compile(r"^[a-f0-9]{40}$")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def test_package_version_has_one_authoritative_source() -> None:
    """Hatch reads the version directly from the package module."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package = (ROOT / "src" / "actiondoctor" / "__init__.py").read_text(
        encoding="utf-8"
    )

    assert re.search(r'__version__ = "0\.1\.0"', package)
    assert project["project"]["dynamic"] == ["version"]
    assert project["tool"]["hatch"]["version"]["path"] == (
        "src/actiondoctor/__init__.py"
    )


def test_packaging_metadata_declares_the_public_distribution_contract() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    metadata = project["project"]

    assert metadata["name"] == "actiondoctor"
    assert metadata["readme"] == "README.md"
    assert metadata["requires-python"] == ">=3.12"
    assert metadata["license"] == {"file": "LICENSE"}
    assert metadata["scripts"]["actiondoctor"] == "actiondoctor.cli:app"
    assert {"Documentation", "Issues", "Source"} <= set(metadata["urls"])
    assert {"build>=1.2", "twine>=6.0"} <= set(metadata["optional-dependencies"]["dev"])
    assert project["build-system"]["build-backend"] == "hatchling.build"
    assert project["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "src/actiondoctor"
    ]


def test_public_community_and_release_files_exist() -> None:
    expected_paths = [
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "SUPPORT.md",
        "docs/ROADMAP.md",
        "docs/RELEASING.md",
        "docs/RELEASE_CHECKLIST.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/config.yml",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/workflows/release-validation.yml",
        "action.yml",
    ]

    assert all((ROOT / path).is_file() for path in expected_paths)


def test_readme_describes_current_release_surface() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "22 built-in rules" in readme
    assert "0--100 health score" in readme
    assert "actiondoctor scan ." in readme
    assert "docs/GITHUB_ACTION.md" in readme
    assert "SECURITY.md" in readme


def test_selected_markdown_links_resolve_inside_the_repository() -> None:
    documents = [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
        ROOT / "SUPPORT.md",
        ROOT / "docs" / "RELEASING.md",
        ROOT / "docs" / "RELEASE_CHECKLIST.md",
    ]

    for document in documents:
        for target in MARKDOWN_LINK_PATTERN.findall(
            document.read_text(encoding="utf-8")
        ):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            local_target = target.split("#", maxsplit=1)[0]
            assert (document.parent / local_target).is_file(), (
                f"{document.relative_to(ROOT)} links to missing {target}"
            )


def test_changelog_records_the_first_release() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "## [0.1.0] - 2026-07-24" in changelog
    assert "## [Unreleased]" in changelog


def test_release_validation_is_pinned_and_builds_a_clean_wheel() -> None:
    yaml = YAML(typ="safe")
    workflow_path = ROOT / ".github" / "workflows" / "release-validation.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["validate"]["steps"]
    action_steps = [step for step in steps if "uses" in step]
    rendered = workflow_path.read_text(encoding="utf-8")

    assert workflow["on"]["push"]["tags"] == ["v*"]
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["validate"]["timeout-minutes"] == 20
    assert action_steps
    assert all(
        SHA_PATTERN.fullmatch(step["uses"].split("@", maxsplit=1)[1])
        for step in action_steps
    )
    assert "continue-on-error" not in rendered
    assert "python -m build" in rendered
    assert "python -m twine check dist/*" in rendered
    assert "python -m venv .release-venv" in rendered
    assert "dist/*.whl" in rendered
