# Bench Results Schema

This describes the JSON Lines objects written to `bench_results.jsonl`.

## Required top-level keys

- `seed` (string)
- `category` (string)
- `config` (object)
- `structure` (object)
- `loopiness` (object)
- `ground` (object)
- `policy` (object)
- `human_closure_rating` (null)

## Config

- `novelty` (number or null)
  - `null` means novelty gating is off.
- `depth` (number)
- `branching` (number or null)
- `rng_seed` (number)

## Structure

- `node_count` (number)
- `edge_count` (number)
- `unique_nodes` (number)
- `max_depth_reached` (number)
- `transform_counts` (object)
- `dedup_saved` (number)

## Loopiness

- `loop_pattern_hits` (object)
  - `echo_of` (number) = count of "Echo of [" occurrences
  - `shadow_of` (number) = count of "Shadow of (" occurrences
  - `symbols` (number) = count of "Symbols:" occurrences
  - `total` (number) = `echo_of + shadow_of + symbols`
- `invert_nesting_max` (number)

## Ground

- `ground_nodes_count` (number)
- `selected_ground_text` (string or null)
- `ground_channel` (enum: `writing`, `breath`, `movement`, `social`, `environment`)
- `ground_sigils` (array of strings)
- `ground_path` (array of node id strings or null)
- `branches_ending_in_ground` (number)
- `avg_novelty_to_ground` (number or null)
- `ground_hash` (string or null)

## Policy

- `version` (string)
- `mode` (string)
- `public_safe` (boolean, always true)
- `redactions` (array of strings)
- `notes` (string)
- `decision` (object)
  - `action` (string)
  - `severity` (number)
  - `reason_codes` (array of strings)
  - `inputs` (object, aggregate-only)

## Determinism guarantee

For identical inputs (`seed`, `config`, and `rng_seed`), the outputs are deterministic:
the same `ground_hash` and the same `ground_path` must be produced.
