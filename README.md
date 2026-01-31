# EchoLattice

EchoLattice is a deterministic, bounded recursion engine designed to study and control recursive symbolic processes in language-model-driven systems. It provides explicit mechanisms for recursion limiting, grounding, benchmarking, and aggregate-only governance signaling.

The project is intended as a reference implementation for researchers and engineers exploring safe recursion, symbolic interruption, and reproducible evaluation of recursive behavior. It is dependency-free (Python standard library only) and emphasizes auditability, determinism, and clarity over performance or productization.

---

## Core Concepts

### Bounded Recursion
EchoLattice constructs recursive symbolic graphs (lattices) while enforcing strict bounds on:
- depth
- branching
- transform reuse
- repetition patterns

This prevents runaway recursion and enables controlled experimentation.

### Grounding / Interruption
Each recursive run is designed to terminate with at most one Ground node:
- a small, concrete, non-escalatory action
- deterministic under fixed inputs
- treated as a structural closure, not an interpretation

Grounding acts as a recursion interrupt, ensuring closure without adjudicating meaning or intent.

### Determinism & Reproducibility
Given the same:
- seed
- configuration
- RNG seed

EchoLattice produces identical graphs, metrics, and selected Ground paths. This property is enforced and verified through benchmarking and regression tooling.

### Aggregate-Only Governance Signals
EchoLattice emits numeric, aggregate metrics only, such as:
- loopiness indicators
- nesting depth
- deduplication ratios
- novelty-to-ground scores

No raw text, prompts, or user data are used in governance decisions.

---

## Repository Structure

Key components include:

- `echolattice.py`
  Core recursion engine, transform logic, grounding rules, and CLI interface.

- `governance_policy.py`
  Aggregate-only policy evaluation layer that maps stability metrics to advisory actions (e.g. CONTINUE, PRUNE, GROUND_NOW). This layer does not inspect text or memory.

- `tests/`
  Unit tests for governance policy determinism and bounds.

- `tools/verify_benchmark.py`
  Verification script to ensure benchmark outputs conform to schema and expectations.

- `docs/`
  Design notes, schema documentation, and instability pathway explanations.

- Example artifacts
  - lattice replay JSON
  - benchmark summaries
  - schema definitions

---

## Benchmarking

EchoLattice includes a built-in benchmarking mode to evaluate recursion behavior under different configurations.

### Running Benchmarks

```bash
python echolattice.py --benchmark
```

This produces:

- `bench_results.jsonl` — machine-readable benchmark records
- `bench_summary.md` — human-readable summary and highlights

Benchmarks compare:

- novelty disabled vs. thresholded novelty
- loop suppression effectiveness
- grounding reachability
- determinism across runs

### Verification

```bash
python tools/verify_benchmark.py
```

The verifier checks:

- required metrics are present
- schemas are respected
- policy outputs are recorded
- determinism invariants hold

---

## Governance & Safety Model

EchoLattice intentionally separates measurement from decision-making.

- The engine measures recursion properties.
- The policy layer evaluates aggregate metrics.
- No enforcement or interpretation is performed.

Outputs are advisory and recorded for auditability.

This design supports public transparency while avoiding:

- identity inference
- psychological claims
- private data handling
- hidden control logic

Policy outputs are:

- stored in benchmark artifacts
- summarized in human-readable form
- reduced to pointers in CLI output

---

## Lattice Replay & ARC Gating

EchoLattice supports replay and analysis of completed lattices, including:

- node and edge structure
- transform distribution
- grounding paths

ARC-style gating is used to:

- suppress redundant probes
- limit transform stacking
- prevent recursive amplification of identical patterns

These mechanisms are structural, not semantic.

---

## Status & Scope

EchoLattice is a research and engineering reference implementation.

It is:

- suitable for experimentation
- suitable for auditing and demonstration
- intentionally minimal

It is not:

- a production agent
- a clinical or diagnostic system
- a memory or identity framework

Future extensions are expected to occur in downstream systems that consume EchoLattice outputs, not inside the core engine.

---

## Safety Notice

EchoLattice is not a medical device and is not intended for clinical use.

If a user is distressed, sleeping poorly, feeling out of control, escalating in fear or anger, or making threats: pause usage and seek professional help.
