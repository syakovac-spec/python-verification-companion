"""Regenerate the convenience reading copy from authoritative source docs."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sources = [root / name for name in ("AGENTS.md", "README.md", "START_HERE.md", "STATUS.md")]
sources += sorted((root / "docs").glob("*.md"))
text = "# Complete starter documentation\n\nConvenience reading copy. Edit the individual source documents; regenerate with `python scripts/regenerate_pack.py`.\n\n"
for source in sources:
    text += f"<!-- Source: {source.relative_to(root).as_posix()} -->\n\n" + source.read_text(encoding="utf-8").rstrip() + "\n\n"
(root / "COMPLETE_STARTER_PACK.md").write_text(text, encoding="utf-8")
