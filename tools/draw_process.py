#!/usr/bin/env python3
"""Draws the README's process diagram into docs/images/process.svg. Stdlib only.

The look follows a printed field guide: a gridded page, white cards with ink borders and hard shadows, black label
tabs, teal highlights. Archivo (tools/fonts, SIL OFL) is embedded so the drawing renders the same everywhere."""
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images" / "process.svg"
FONT_FILE = Path(__file__).resolve().parent / "fonts" / "archivo-latin.woff2"
W, H = 1320, 580

PAGE, GRID, PAPER, INK, SLATE, SHADE = "#e3ecf3", "#d3dfe9", "#ffffff", "#1b1d21", "#4f5d69", "#c4d1dc"
TEAL, TEAL_PALE = "#2EC4C0", "#d9f4f4"

PHASES = [
    ("1", "Requirements", "requirements.md", "behavior, rules"),
    ("2", "Data design", "data-design.md, schema", "schema"),
    ("3", "Architecture", "architecture-design.md", "calls, events"),
    ("4", "Stack selection", "stack-selection.md", "a library, runtime"),
    ("5", "Implementation", "code + tests, local commit", "nothing above"),
]
CYCLE = ["Draft", "Self-check", "Agent review", "Open items", "You approve"]

X0, GAP = 40, 28
START_W = 210              # the left column: where you start
AX = X0 + START_W + 44     # the right area: the cycle, the steps, triage, changes
BOX_W = (W - X0 - AX - 4 * GAP) / 5
TOP = 44                   # cycle row
PY, PH = 184, 118          # phase row
TY, TH = 392, 50           # triage bar
EY, EH = 488, 64           # entry row


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, c=INK, size=14, weight=400, anchor="middle", stretch=None):
    st = f' font-stretch="{stretch}%"' if stretch else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{c}" font-size="{size}" font-weight="{weight}"{st} '
            f'text-anchor="{anchor}">{esc(s)}</text>')


def box(x, y, w, h, fill=PAPER, shadow=4, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    s = f'<rect x="{x + shadow:.1f}" y="{y + shadow:.1f}" width="{w:.1f}" height="{h}" fill="{SHADE}"/>' if shadow else ""
    return s + f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" fill="{fill}" stroke="{INK}" stroke-width="1"{d}/>'


def tab(x, y, s):
    """A black label tab, sitting on the top edge of the card below it."""
    w = 14 + len(s) * 7.6
    return (f'<rect x="{x:.1f}" y="{y - 20:.1f}" width="{w:.1f}" height="20" fill="{INK}"/>'
            + text(x + 7, y - 5.5, s.upper(), PAPER, 11.5, 700, "start"))


def arrow(x1, y1, x2, y2, dash=None, width=1.6):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{INK}" stroke-width="{width}"{d} '
            f'marker-end="url(#head)"/>')


def draw():
    font = base64.b64encode(FONT_FILE.read_bytes()).decode()
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="Archivo, system-ui, sans-serif">',
           "<defs>",
           f'<style>@font-face{{font-family:"Archivo";src:url(data:font/woff2;base64,{font}) format("woff2");'
           f'font-weight:100 900;font-stretch:62% 125%}}</style>',
           f'<pattern id="grid" width="16" height="16" patternUnits="userSpaceOnUse">'
           f'<path d="M16 0 L0 0 0 16" fill="none" stroke="{GRID}" stroke-width="1"/></pattern>',
           f'<marker id="head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
           f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>',
           "</defs>",
           f'<rect width="{W}" height="{H}" fill="{PAGE}"/>',
           f'<rect width="{W}" height="{H}" fill="url(#grid)"/>']

    # the cycle every step runs
    lx = AX
    lw = W - X0 - lx
    out.append(box(lx, TOP, lw, 64))
    out.append(tab(lx, TOP, "Every step runs the same cycle"))
    step_w = (lw - 40 + 26) / len(CYCLE)
    for i, s in enumerate(CYCLE):
        sx = lx + 20 + i * step_w
        last = i == len(CYCLE) - 1
        out.append(f'<rect x="{sx:.1f}" y="{TOP + 20}" width="{step_w - 26:.1f}" height="26" '
                   f'fill="{TEAL if last else PAPER}" stroke="{INK}" stroke-width="1"/>')
        out.append(text(sx + (step_w - 26) / 2, TOP + 38, s, INK, 13, 700 if last else 400))
        if not last:
            out.append(arrow(sx + step_w - 24, TOP + 33, sx + step_w - 4, TOP + 33))

    # where you start: both entry points, side by side in one column
    sc = X0 + START_W / 2
    out.append(tab(X0, PY, "Start here"))
    out.append(box(X0, PY, START_W, PH, TEAL))
    out.append(text(sc, PY + 50, "New service", INK, 21, 700, stretch=75))
    out.append(text(sc, PY + 73, "a business ask or a PRD", INK, 13))
    out.append(arrow(X0 + START_W + 6, PY + PH / 2, AX - 4, PY + PH / 2, width=2))
    out.append(text(sc, (PY + PH + EY) / 2 + 6, "or", SLATE, 15, 700))
    out.append(tab(X0, EY, "Start here"))
    out.append(box(X0, EY, START_W, EH, TEAL))
    out.append(text(sc, EY + 27, "Existing repo", INK, 21, 700, stretch=75))
    out.append(text(sc, EY + 48, "docs written from its code", INK, 13))

    # the steps
    out.append(tab(AX, PY, "The steps"))
    centers = []
    for i, (n, name, deliv, _) in enumerate(PHASES):
        x = AX + i * (BOX_W + GAP)
        centers.append(x + BOX_W / 2)
        out.append(box(x, PY, BOX_W, PH))
        out.append(f'<rect x="{x + 14:.1f}" y="{PY + 14}" width="24" height="22" fill="{INK}"/>')
        out.append(text(x + 26, PY + 30, n, PAPER, 13, 700))
        out.append(text(x + 48, PY + 31, name, INK, 19, 700, "start", stretch=75))
        out.append(text(x + 14, PY + 60, deliv, SLATE, 13, 400, "start"))
        out.append(f'<rect x="{x + 14:.1f}" y="{PY + 78}" width="108" height="24" fill="{TEAL}" '
                   f'stroke="{INK}" stroke-width="1"/>')
        out.append(text(x + 68, PY + 95, "✓ you approve", INK, 12.5, 700))
        if i < len(PHASES) - 1:
            out.append(arrow(x + BOX_W + 6, PY + PH / 2, x + BOX_W + GAP - 4, PY + PH / 2, width=2))

    # triage: a change enters at the first step it touches
    out.append(box(AX, TY, W - X0 - AX, TH, TEAL_PALE))
    out.append(tab(AX, TY, "Triage"))
    out.append(text((AX + W - X0) / 2, TY + 31, "What does the change touch? It enters there, and only the steps it touches run.",
                    INK, 15, 600))
    for cx, (_, _, _, touches) in zip(centers, PHASES):
        out.append(arrow(cx, TY - 22, cx, PY + PH + 10, "5 4"))
        out.append(text(cx + 8, TY - 30, touches, SLATE, 12.5, 700, "start"))

    # how changes arrive: an imported repo's docs are approved as they stand, then changes come in like any other
    cw = W - X0 - AX
    out.append(arrow(X0 + START_W + 6, EY + EH / 2, AX - 4, EY + EH / 2, width=2))
    out.append(box(AX, EY, cw, EH))
    out.append(text(AX + cw / 2, EY + 27, "A new feature, change or fix", INK, 19, 700, stretch=75))
    out.append(text(AX + cw / 2, EY + 48,
                    "on a service built this way, or an imported repo once you approve its docs as they stand",
                    SLATE, 13))
    out.append(arrow(AX + cw / 2, EY - 2, AX + cw / 2, TY + TH + 8, width=2))

    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(draw(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
