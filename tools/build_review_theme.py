#!/usr/bin/env python3
"""Builds skills/rendering-design-docs/theme/review-page.css from tools/theme/review-page.src.css, embedding Archivo
(skills/rendering-design-docs/theme/archivo-latin.woff2, SIL OFL). Stdlib only."""
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEME = ROOT / "skills" / "rendering-design-docs" / "theme"

if __name__ == "__main__":
    font = base64.b64encode((THEME / "archivo-latin.woff2").read_bytes()).decode()
    css = (ROOT / "tools" / "theme" / "review-page.src.css").read_text().replace("@@FONT@@", font)
    (THEME / "review-page.css").write_text(css)
    print(f"wrote {(THEME / 'review-page.css').relative_to(ROOT)} ({len(css) // 1024} KB)")
