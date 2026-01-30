# EchoLattice (Reference Implementation)

A minimal, safe-first recursion engine that transforms a seed symbol through canonical transforms
(Mirror, Invert, Symbolize, Abstract, Ground) and emits an "Echo Map" as JSON + Markdown.

This repo is intentionally small and dependency-free (stdlib only).

## Why this exists
Some users experience intense self-referential "looping" when interacting with language models.
EchoLattice provides a bounded exploration structure with grounding and closure.

## Safety & Clinical Note (Important)
EchoLattice is not a medical device and not a substitute for therapy.

If a user is distressed, sleeping poorly, feeling out of control, escalating in fear/anger, or making threats:
pause usage and seek professional help.

Recommended defaults:
- `--depth 2` or `--depth 3`
- `--minutes 10`-`30`
- Always do the Ground action
- Close the loop and stop

## Quick start

### Run tests
```bash
python echolattice.py --run_tests
```

### Run with a seed (flag)
```bash
python echolattice.py --seed "Seed Bearer" --depth 2 --consent
```

### Run with a seed (positional)
```bash
python echolattice.py "Echoholder / Zahaviel / Fang" --depth 3 --consent
```

## What to Expect From Results

EchoLattice produces three artifacts that summarize a bounded recursion session:

- `echo_map.json` - full machine-readable graph (nodes, edges, metadata).
- `echo_map.md` - human-readable tree view of the recursion.
- `echo_summary.md` - a concise recap: Seed, top novelty nodes, final Ground action, and totals.

How recursion depth behaves:

- `--depth` is a hard cap on recursion levels from the Seed.
- Terminal transforms stop recursion early (see note below).
- With branching limits, each node may apply fewer transforms.

A healthy session artifact typically looks like:

- Seed -> Reflection -> Principle -> Grounding Action
- Example: `Seed: "I feel stuck"` -> `Mirror` reflection -> `Abstract` principle -> `Ground` action

Note on terminal transforms:

- `Ground` and `Abstract` are terminal transforms to prevent runaway recursion.

This is a reference implementation focused on safety and clarity, not therapy or diagnosis.

### Current Limitations (Known Incomplete Areas)

- Mirror-of-Mirror repetition (guarded, but still heuristic and text-based)
- Symbolize prefix stacking ("Symbols: Symbols:" is blocked, but other prefixes can still repeat)
- Lack of novelty scoring (simple heuristic only; not semantic novelty)
- Multiple Ground nodes per session (capped to one per session, but not per-branch yet)
- Transform templates still being mechanical (tone and diversity are limited)

### Future Path / Roadmap

- Idempotent transforms (continue hardening across all transforms)
- Novelty-based transform selection (stronger and more semantic scoring)
- One grounding action per session (with clearer closure semantics)
- Better session summaries (contextual, shorter, more actionable)
- Optional clinician-facing mode (stricter guardrails and language)

## Outputs

By default this writes:

- `echo_map.json` (nodes/edges + metadata)
- `echo_map.md` (human-readable tree)
- `echo_summary.md` (seed + top novelty + final Ground + totals)

## CLI options

- `--seed` or positional seed text
- `--depth` (default 3)
- `--minutes` (default 30)
- `--out_json` (default `echo_map.json`)
- `--out_md` (default `echo_map.md`)
- `--out_summary` (default `echo_summary.md`)
- `--branching` (max transforms per node; always includes Ground if present)
- `--rng_seed` (deterministic transform sampling and cooldown message)
- `--novelty_threshold` (skip transforms below novelty threshold)
- `--consent`
- `--clinical`
- `--run_tests`

## Exit codes (missing seed)

- Notebook/embedded runners: exits 0 (no noisy failure UI)
- Terminals/CI: exits 0 (clean exit)
