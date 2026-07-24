# v0.1.0 Release Checklist

- [ ] Git status is clean.
- [ ] `src/actiondoctor/__init__.py` contains `0.1.0`.
- [ ] `actiondoctor version` reports `0.1.0`.
- [ ] `CHANGELOG.md` contains dated `0.1.0` release notes.
- [ ] Documentation and internal links are reviewed.
- [ ] `ruff check .`, `ruff format --check .`, `mypy src`, and `pytest` pass.
- [ ] `python -m build` produces a wheel and source distribution.
- [ ] `python -m twine check dist/*` passes.
- [ ] A clean environment installs the built wheel and passes CLI smoke tests.
- [ ] GitHub Action integration passes.
- [ ] `actiondoctor scan . --fail-on high --no-color` passes.
- [ ] Remaining advisory self-scan findings are documented and accepted.
- [ ] No tag, GitHub Release, or PyPI publication has occurred yet.
