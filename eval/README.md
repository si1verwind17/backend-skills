# Evaluations: backend skills

One folder per skill: its `README.md` (what the benchmark measures, the scenario list, pending validation, the
latest result per scenario) and `scenarios/`, one file per scenario with its fixture, prompt and checks. Fixtures a
scenario copies into its workdir live in [`fixtures/`](fixtures/). Start a new scenario from
[`template-scenario.md`](template-scenario.md).

A single passing run proves a skill *can* work; only repetition proves it works *reliably*, and only a control arm
proves it changes anything.

| Skill | Scenarios |
|---|---|
| [`building-backend-services`](building-backend-services/README.md) | resume mid-chain, greenfield phase 0, import (small and large), change triage, implementation phase |
| [`writing-business-requirements`](writing-business-requirements/README.md) | interview from a fuzzy ask, digest of a founder's brief |
| [`backend-design-by-data`](backend-design-by-data/README.md) | clinic on Postgres, serverless parcel lockers, clinic with nothing given |
| [`backend-architecture`](backend-architecture/README.md) | ticketing on GCP, delivery tracking on AWS |
| [`backend-stack-selection`](backend-stack-selection/README.md) | two services on an existing Scala estate |
| [`backend-code-conventions`](backend-code-conventions/README.md) | cancel-order in Python and Scala, config pressure |
| [`rendering-design-docs`](rendering-design-docs/README.md) | tabbed review page, an active change |

## Protocol

- **Two arms.** Control: a fresh agent gets the scenario with the skill NOT loaded. Skill arm: identical but with the
  skill loaded. A check the control arm already passes consistently is dead weight: cut or sharpen that rule.
  Control prompts MUST explicitly forbid loading any skill or convention guide from the environment, because agent
  harnesses auto-discover skills and a control that silently reads the skill under test measures nothing. Check
  that control outputs don't echo the skill's distinctive vocabulary before trusting the arm.
- **Preambles.** Skill arm: "Before starting, read `<skills>/<skill>/SKILL.md` and follow it as authoritative for
  how you work. Its sibling skills and reference files are in that same skills/ folder; read them from there." Control
  arm: "Do not load or read any skill, SKILL.md, or convention guide from the environment." Then the scenario's
  prompt, verbatim, with `<workdir>` filled in. Runs read a frozen copy of `skills/` at the commit under test.
- **Reps.** 3 per scenario by default, 5 when a result is close or a control arm runs; single runs lie.
- **Independent grading.** A fresh judge (agent or human, on a model at least as strong as the run's) grades each run
  against the checks, never the session that authored the skill. Judges verify behaviour where they can: load DDL
  into a database, open pages in a browser, re-run tests, look versions up.
- **Plugin runs.** To exercise the plugin's agents (`design-reviewer`, `code-reviewer`), run the scenario headless
  with the repository loaded as a plugin: `claude -p "<preamble + prompt>" --plugin-dir <plugin copy>`. Keep the
  plugin copy **outside** the run workdirs: files inside a plugin directory are protected, and edits there are refused.
- **Headless runs.** Pass `--disallowedTools ScheduleWakeup`. A run that dispatches its reviewer in the background
  may otherwise schedule a fallback wakeup (often 20 minutes); `claude -p` then stays alive after its final reply,
  waiting for that wakeup, and would re-run its prompt when it fires. Set a timeout anyway; a run that idles after
  replying can be stopped and its reply taken from its transcript.
- **Parallel runs share a machine.** Give each run its own ports and process names when a scenario starts servers
  (cold-start probes, test databases), or one run kills or skews another.
- **When to run.** At creation (both arms); after any substantive edit (skill arm; control too if checks changed);
  when the underlying model changes.
- **Results.** Each skill's README keeps the latest result per scenario; git keeps the history. A substantive edit not
  yet measured goes under **Pending validation** with the commit and the scenario that will validate it; the run that
  validates it deletes the entry.
- **Real misses become checks.** When a skill-loaded agent gets something wrong in real use, add that case as a
  failing check first; the skill edit must flip it.

`Skill@` is the short hash of the commit whose skill content was tested. These hashes refer to the skills'
development history, which was squashed into this repository's first commit, so they do not resolve here; a result
recorded before a later edit to its skill stands until that edit's **Pending validation** entry is measured.
