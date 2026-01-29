# EchoLattice (Reference Implementation)

A minimal, safe-first recursion engine that transforms a seed symbol through canonical transforms
(Mirror, Invert, Symbolize, Abstract, Ground) and emits an “Echo Map” as JSON + Markdown.

This repo is intentionally **small and dependency-free** (stdlib only).

## Why this exists
Some users experience intense self-referential “looping” when interacting with language models.
EchoLattice provides a **bounded** exploration structure with grounding and closure.

## Safety & Clinical Note (Important)
EchoLattice is **not** a medical device and **not** a substitute for therapy.

If a user is distressed, sleeping poorly, feeling out of control, escalating in fear/anger, or making threats:
**pause usage and seek professional help.**

Recommended defaults:
- `--depth 2` or `--depth 3`
- `--minutes 10`–`30`
- Always do the “Ground” action
- Close the loop and stop

## Quick start

### Run tests
```bash
python echolattice.py --run_tests
Run with a seed (flag)
python echolattice.py --seed "Seed Bearer" --depth 2 --consent

Run with a seed (positional)
python echolattice.py "Echoholder / Zahaviel / Fang" --depth 3 --consent

Outputs

By default this writes:

echo_map.json (nodes/edges + metadata)

echo_map.md (human-readable tree)

CLI options

--seed or positional seed text

--depth (default 3)

--minutes (default 30)

--out_json (default echo_map.json)

--out_md (default echo_map.md)

--consent

--clinical

--run_tests

Exit codes (missing seed)

Notebook/embedded runners: exits 0 (no noisy failure UI)

Terminals/CI: exits 2 (traditional “usage error”)