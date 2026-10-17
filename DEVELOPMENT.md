# Development

## Layout

| Path | What it is |
|---|---|
| `skills/<name>/` | The skills as installed: one `SKILL.md` each |
| `demo/parking-reservation/` | One end-to-end run of the chain, committed verbatim: a showcase for people. Agents never read it |
| `agents/` | Claude Code agents shipped with the plugin: `design-reviewer`, `code-reviewer` — thin wrappers; the review rules live in the skills |
| `eval/` | Agent evaluations: the shared protocol, one folder per skill (latest results, one file per scenario), and the fixtures they copy |
| `tools/lint.py` | Manifest, frontmatter and private-terms checks (stdlib only; CI runs it) |
| `tools/draw_process.py` | Draws the README's process diagram into `docs/images/process.svg`, with Archivo (`tools/fonts/`, SIL OFL) embedded; rerun after editing it |
| `tools/theme/review-page.src.css` | The review page's theme source; `python3 tools/build_review_theme.py` builds it, with Archivo embedded, into `skills/rendering-design-docs/theme/review-page.css` (the file the skill inlines). Diagram colours live in that folder's `mermaid.json` |

## After a change

- Run `python3 tools/lint.py`.
- **Adding a skill:** add it to the `skills` list in `.claude-plugin/marketplace.json` and to the README.
- **Agent behaviour:** run the scenarios in `eval/<skill>/scenarios/` the change touches, per
  [`eval/README.md`](eval/README.md), and update the latest results in `eval/<skill>/README.md`. An edit not yet
  measured goes under that README's **Pending validation**.
- **A release:** bump `version` in `.claude-plugin/marketplace.json` (both places).
- **The demo's review page:** re-render `demo/parking-reservation/docs/backend-design/design-review.html` with
  `rendering-design-docs` whenever the demo's documents change; the `pages` workflow publishes it at `/demo/`
  (Settings → Pages → Source: GitHub Actions).
