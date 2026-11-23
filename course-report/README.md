# CVPR report source

`main.tex` uses the official CVPR 2026 style from `template/`, pinned to author-kit
commit `12909ae437f6dbc7435069cfdb4ca44c18e6a02f`.

Build from the repository root:

```bash
uv run python scripts/build_course_report.py
```

The script regenerates figures, runs Tectonic, verifies an eight-page PDF and
checks for unresolved references and unchanged author placeholders.
