#!/usr/bin/env python3
"""EchoLattice Reference Implementation (Python, MIT) — v0.2.2

Fixes in v0.2.2
---------------
- Eliminates noisy `SystemExit: 1` when seed is missing by exiting cleanly (status 0)
  after showing examples/help and (when possible) prompting.
- Prompts for a seed in interactive contexts even when `stdin.isatty()` is False
  (common in notebooks / embedded runners) by detecting IPython/ipykernel.
- Keeps `print()` avoidance: uses `sys.stderr.write` / `sys.stdout.write`.
- Adds a self-test to verify that missing-seed flow returns 0 (no SystemExit 1).

Purpose
-------
A minimal, safe-first recursion engine that transforms a seed symbol through
canonical transforms (Mirror, Invert, Symbolize, Abstract, Ground) to produce
an Echo Map (nodes/edges) for therapy, creativity, and prototyping.

CLI behavior
------------
- Accepts seed via `--seed` OR positional `seed`.
- If seed is missing: ALWAYS prints examples + help; then prompts when running interactively.
- Self-tests: `--run_tests`

License
-------
MIT License (c) 2025 Tyrone Mineard

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List, Optional

# ---------------------------
# Data structures
# ---------------------------


@dataclass
class EchoNode:
    id: str
    text: str
    transform: str  # "Seed", "Mirror", "Invert", etc.
    depth: int
    parent_id: Optional[str]
    tags: List[str]
    timestamp: float


@dataclass
class EchoEdge:
    src_id: str
    dst_id: str
    relation: str  # "transforms_to" | "mirrors" | "grounds"


@dataclass
class SessionMeta:
    user_consent: bool
    safety_level: str  # e.g., "light", "clinical"
    max_depth: int
    max_minutes: int
    started_at: float


@dataclass
class EchoGraph:
    meta: SessionMeta
    nodes: List[EchoNode]
    edges: List[EchoEdge]


# ---------------------------
# Transform registry
# ---------------------------

TransformFn = Callable[[str], str]
TRANSFORMS: Dict[str, TransformFn] = {}


def register_transform(name: str):
    def deco(fn: TransformFn):
        TRANSFORMS[name] = fn
        return fn

    return deco


@register_transform("Mirror")
def t_mirror(text: str) -> str:
    return f"Echo of [{text}] returns as self-reflection."  # gentle mirror


@register_transform("Invert")
def t_invert(text: str) -> str:
    swaps = {
        r"\bI am\b": "I am not",
        r"\bpower\b": "humility",
        r"\blight\b": "shadow",
        r"\bstrong\b": "soft",
        r"\bforward\b": "still",
    }
    inv = text
    for pat, rep in swaps.items():
        inv = re.sub(pat, rep, inv, flags=re.IGNORECASE)
    if inv == text:
        inv = f"Shadow of ({text}) reveals its opposite."  # fallback
    return inv


@register_transform("Symbolize")
def t_symbolize(text: str) -> str:
    table = {
        "Echoholder": "The Mirror-Guardian",
        "Zahaviel": "The Watcher at the Gate",
        "Fang": "The Blade of Discernment",
        "fang": "The Blade of Discernment",
        "Seed Bearer": "The Carrier of Beginnings",
    }
    out = text
    for k, v in table.items():
        out = re.sub(rf"\b{re.escape(k)}\b", v, out)
    return f"Symbols: {out}"


@register_transform("Abstract")
def t_abstract(text: str) -> str:
    tokens = re.findall(r"[A-Za-z][A-Za-z\-]+", text)
    keywords = sorted({t for t in tokens if t[:1].isupper()})
    if not keywords:
        keywords = sorted(set(tokens))[:5]
    return "Principle: " + ", ".join(keywords[:8])


@register_transform("Ground")
def t_ground(text: str) -> str:
    hint = "Create a 1-page sketch that captures the idea and share it with one trusted person."
    if "Blade" in text or "Fang" in text:
        hint = "List 3 things to cut away this week (noise, obligation, distraction). Do the first today."
    if "Mirror" in text or "Echo" in text:
        hint = "Write 5 sentences that reflect what this means to you now. Read them aloud once."
    return f"Action: {hint}"


DEFAULT_PIPELINE = ["Mirror", "Invert", "Symbolize", "Abstract", "Ground"]


# ---------------------------
# Core engine
# ---------------------------


def now_ts() -> float:
    return time.time()


class Recursor:
    def __init__(self, pipeline: List[str], max_depth: int, max_minutes: int = 30):
        self.pipeline = pipeline
        self.max_depth = max_depth
        self.max_minutes = max_minutes

    def recurse(self, seed: str, consent: bool = True, safety_level: str = "light") -> EchoGraph:
        start = now_ts()
        meta = SessionMeta(
            user_consent=consent,
            safety_level=safety_level,
            max_depth=self.max_depth,
            max_minutes=self.max_minutes,
            started_at=start,
        )

        nodes: List[EchoNode] = []
        edges: List[EchoEdge] = []

        root_id = str(uuid.uuid4())
        nodes.append(
            EchoNode(
                id=root_id,
                text=seed,
                transform="Seed",
                depth=0,
                parent_id=None,
                tags=["seed"],
                timestamp=now_ts(),
            )
        )

        def _recurse(parent_id: str, text: str, depth: int):
            if depth >= self.max_depth:
                return
            elapsed_min = (now_ts() - start) / 60.0
            if elapsed_min > self.max_minutes:
                return

            for name in self.pipeline:
                fn = TRANSFORMS[name]
                out = fn(text)
                node_id = str(uuid.uuid4())
                node = EchoNode(
                    id=node_id,
                    text=out,
                    transform=name,
                    depth=depth + 1,
                    parent_id=parent_id,
                    tags=[name.lower()],
                    timestamp=now_ts(),
                )
                nodes.append(node)
                edges.append(EchoEdge(src_id=parent_id, dst_id=node_id, relation="transforms_to"))
                _recurse(node_id, out, depth + 1)

        _recurse(root_id, seed, 0)
        return EchoGraph(meta=meta, nodes=nodes, edges=edges)


# ---------------------------
# Rendering helpers
# ---------------------------


def to_json(graph: EchoGraph) -> str:
    return json.dumps(
        {
            "meta": asdict(graph.meta),
            "nodes": [asdict(n) for n in graph.nodes],
            "edges": [asdict(e) for e in graph.edges],
        },
        indent=2,
    )


def to_markdown_tree(graph: EchoGraph) -> str:
    children = {n.id: [] for n in graph.nodes}
    for e in graph.edges:
        children[e.src_id].append(e.dst_id)
    nodes_by_id = {n.id: n for n in graph.nodes}

    roots = [n for n in graph.nodes if n.depth == 0]
    if not roots:
        return "(empty)"
    root = roots[0]

    lines: List[str] = []

    def walk(node_id: str, prefix: str = ""):
        n = nodes_by_id[node_id]
        label = f"{n.transform}: {n.text}" if n.transform != "Seed" else f"Seed: {n.text}"
        lines.append(prefix + label)
        kids = children.get(node_id, [])
        for i, kid in enumerate(kids):
            is_last = i == len(kids) - 1
            branch = "└─ " if is_last else "├─ "
            walk(kid, prefix + branch)

    walk(root.id)
    return "\n".join(lines)


# ---------------------------
# CLI + UX helpers
# ---------------------------


def _stderr_write(s: str) -> None:
    sys.stderr.write(s)
    if not s.endswith("\n"):
        sys.stderr.write("\n")


def _stdout_write(s: str) -> None:
    sys.stdout.write(s)
    if not s.endswith("\n"):
        sys.stdout.write("\n")


def _is_interactive() -> bool:
    # TTY covers shells; IPython/ipykernel covers notebooks/embedded runners.
    if sys.stdin is not None and getattr(sys.stdin, "isatty", lambda: False)():
        return True
    return ("ipykernel" in sys.modules) or ("IPython" in sys.modules)


def print_examples_and_help(ap: argparse.ArgumentParser) -> None:
    msg = (
        "\nEchoLattice needs a SEED (some text to recurse on).\n\n"
        "Examples:\n"
        "  python echolattice.py --seed \"Seed Bearer\" --depth 2 --consent\n"
        "  python echolattice.py \"Echoholder / Zahaviel / Fang\" --depth 3 --consent\n"
        "\n"
    )
    _stderr_write(msg)
    ap.print_help(file=sys.stderr)


def resolve_seed(args: argparse.Namespace, ap: argparse.ArgumentParser) -> Optional[str]:
    """Resolve the seed text.

    Behavior:
    - If seed provided: return it.
    - If missing: show examples/help, then prompt when interactive.
    - If user cancels prompt: return None.
    """
    seed = args.seed if args.seed else args.seed_pos

    if seed and isinstance(seed, str) and seed.strip():
        return seed.strip()

    print_examples_and_help(ap)

    if _is_interactive():
        try:
            entered = input("Enter seed text (or press Enter to cancel): ").strip()
            return entered if entered else None
        except (EOFError, KeyboardInterrupt):
            return None

    return None


# ---------------------------
# Tests (stdlib-only)
# ---------------------------


def _run_tests() -> int:
    # Test 1: Engine returns root node + at least one child at depth 1 when depth>=1
    rec = Recursor(pipeline=DEFAULT_PIPELINE, max_depth=1, max_minutes=1)
    g = rec.recurse("Seed Bearer", consent=True)
    assert len(g.nodes) >= 2, "Expected at least 2 nodes (seed + one transform)"
    assert g.nodes[0].transform == "Seed", "First node should be Seed"
    assert any(n.transform in DEFAULT_PIPELINE for n in g.nodes[1:]), "Expected transform nodes"

    # Test 2: Markdown tree contains Seed line
    md = to_markdown_tree(g)
    assert md.startswith("Seed: "), "Markdown tree should start with Seed"

    # Test 3: JSON output has required keys
    js = json.loads(to_json(g))
    assert "meta" in js and "nodes" in js and "edges" in js, "JSON missing keys"

    # Test 4: CLI seed resolver prefers --seed over positional
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--seed", default=None)
    ap.add_argument("seed_pos", nargs="?")
    args = ap.parse_args(["--seed", "A", "B"])  # positional ignored
    assert resolve_seed(args, ap) == "A", "--seed should win"

    # Test 5: Help/examples emission should not raise
    ap2 = argparse.ArgumentParser(add_help=False)
    try:
        print_examples_and_help(ap2)
    except Exception as e:
        raise AssertionError(f"print_examples_and_help raised unexpectedly: {e}")

    # Test 6: main() returns 0 (clean exit) when seed is missing (non-interactive assumed)
    # We call main with argv=[]; in most automated test contexts this should not block.
    # If it does become interactive, user can still cancel with Enter.
    code = main([])
    assert code == 0, f"Expected main([]) to return 0 on missing seed; got {code}"

    return 0


# ---------------------------
# Main
# ---------------------------


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="EchoLattice: safe-first recursion engine")

    ap.add_argument("--seed", default=None, help="Seed symbol/text")
    ap.add_argument("seed_pos", nargs="?", help="Seed symbol/text (positional alternative to --seed)")

    ap.add_argument("--depth", type=int, default=3, help="Max recursion depth (default: 3)")
    ap.add_argument("--minutes", type=int, default=30, help="Max session minutes (default: 30)")
    ap.add_argument("--out_json", default="echo_map.json", help="Output JSON file path")
    ap.add_argument("--out_md", default="echo_map.md", help="Output Markdown tree path")

    ap.add_argument("--consent", action="store_true", help="Confirm user consent was obtained")
    ap.add_argument("--clinical", action="store_true", help="Clinical mode tag in metadata")

    ap.add_argument("--run_tests", action="store_true", help="Run self-tests and exit")

    args = ap.parse_args(argv)

    if args.run_tests:
        return _run_tests()

    seed = resolve_seed(args, ap)
    if not seed:
        _stderr_write("No seed provided. Exiting.")
        return 0

    pipeline = DEFAULT_PIPELINE[:]  # Could be customized
    rec = Recursor(pipeline=pipeline, max_depth=args.depth, max_minutes=args.minutes)
    graph = rec.recurse(seed=seed, consent=args.consent, safety_level=("clinical" if args.clinical else "light"))

    with open(args.out_json, "w", encoding="utf-8") as f:
        f.write(to_json(graph))
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(to_markdown_tree(graph))

    _stdout_write(f"Saved: {args.out_json} and {args.out_md}")
    _stdout_write("Session complete. Suggest cool-down: 5 slow breaths, water, short walk.")
    return 0


if __name__ == "__main__":
    # Exit cleanly without a noisy traceback in embedded environments.
    # In normal shells, returning an int still sets an exit code if you wrap with sys.exit.
    code = main()
    try:
        sys.exit(code)
    except SystemExit:
        # Some embedded runners surface SystemExit as an error; swallow for a clean UX.
        pass
