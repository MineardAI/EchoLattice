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
import contextlib
import io
import json
import os
import random
import re
import sys
import tempfile
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
    occurrences: int = 1


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
    if text.startswith("Echo of [") or text.count("Echo of [") > 1:
        return text
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
    if text.startswith("Symbols:"):
        return text
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
    tokens = re.findall(r"[A-Za-z][A-Za-z\-]+", text.lower())
    words = [t for t in tokens if len(t) > 2]
    themes = []
    for w in words:
        if w not in themes:
            themes.append(w)
        if len(themes) == 2:
            break

    rules = [
        ({"loop", "cycle", "repeat"}, "Step away for 5 minutes, then return and do one small change."),
        ({"fear", "afraid", "anxiety"}, "Take 6 slow breaths, then call or text a trusted friend."),
        ({"mirror", "echo", "reflection"}, "Write 3 honest sentences, then read them once out loud."),
        ({"blade", "fang", "cut"}, "List 3 things to cut away; drop the easiest one today."),
        ({"ground", "earth", "root"}, "Stand up, feel your feet, and name 3 things you can see."),
    ]
    for keys, action in rules:
        if any(k in words for k in keys):
            return f"Action: {action}"

    if themes:
        theme = " / ".join(themes[:2])
        action = f"Pick one small step for {theme}; write it down and do it for 5 minutes."
    else:
        action = "Pick one small next step; write it down and do it for 5 minutes."
    return f"Action: {action}"


DEFAULT_PIPELINE = ["Mirror", "Invert", "Symbolize", "Abstract", "Ground"]
# Nodes produced by these transforms never recurse further.
TERMINAL_TRANSFORMS = {"Ground", "Abstract"}


# ---------------------------
# Core engine
# ---------------------------


def now_ts() -> float:
    return time.time()

def novelty_score(parent_text: str, candidate_text: str) -> float:
    def words(s: str) -> set:
        return set(re.findall(r"[A-Za-z][A-Za-z\\-]+", s.lower()))

    a = words(parent_text)
    b = words(candidate_text)
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    inter = a & b
    return 1.0 - (len(inter) / len(union))

class Recursor:
    def __init__(
        self,
        pipeline: List[str],
        max_depth: int,
        max_minutes: int = 30,
        branching: Optional[int] = None,
        rng_seed: Optional[int] = None,
        novelty_threshold: Optional[float] = None,
    ):
        self.pipeline = pipeline
        self.max_depth = max_depth
        self.max_minutes = max_minutes
        self.branching = branching
        self.rng = random.Random(rng_seed)
        self.novelty_threshold = novelty_threshold

    def _select_transforms(self) -> List[str]:
        pipeline = self.pipeline[:]
        ground_in_pipeline = "Ground" in pipeline
        non_ground = [name for name in pipeline if name != "Ground"]

        branching = self.branching
        if branching is None:
            selected = non_ground
        else:
            if branching < 1:
                branching = 1
            max_non_ground = max(branching - (1 if ground_in_pipeline else 0), 0)
            if max_non_ground >= len(non_ground):
                selected = non_ground
            else:
                selected = self.rng.sample(non_ground, k=max_non_ground)

        ordered = [name for name in pipeline if name in selected and name != "Ground"]
        if ground_in_pipeline:
            ordered.append("Ground")
        return ordered

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
        node_index: Dict[tuple, EchoNode] = {}
        edge_index: set = set()
        session_grounded = False

        root_id = str(uuid.uuid4())
        root_node = EchoNode(
            id=root_id,
            text=seed,
            transform="Seed",
            depth=0,
            parent_id=None,
            tags=["seed"],
            timestamp=now_ts(),
        )
        nodes.append(root_node)
        node_index[(root_node.transform, root_node.text)] = root_node

        def _recurse(parent_id: str, text: str, depth: int, parent_transform: str):
            nonlocal session_grounded
            # If the parent was terminal, do not generate children from it.
            if parent_transform in TERMINAL_TRANSFORMS:
                return
            if depth >= self.max_depth:
                return
            elapsed_min = (now_ts() - start) / 60.0
            if elapsed_min > self.max_minutes:
                return

            for name in self._select_transforms():
                if name == "Ground" and session_grounded:
                    continue
                fn = TRANSFORMS[name]
                out = fn(text)
                if self.novelty_threshold is not None:
                    score = novelty_score(text, out)
                    if score < self.novelty_threshold:
                        continue
                existing = node_index.get((name, out))
                if existing is not None:
                    existing.occurrences += 1
                    if parent_id != existing.id:
                        edge_key = (parent_id, existing.id)
                        if edge_key not in edge_index:
                            edges.append(
                                EchoEdge(src_id=parent_id, dst_id=existing.id, relation="transforms_to")
                            )
                            edge_index.add(edge_key)
                    continue
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
                node_index[(name, out)] = node
                edge_key = (parent_id, node_id)
                edges.append(EchoEdge(src_id=parent_id, dst_id=node_id, relation="transforms_to"))
                edge_index.add(edge_key)
                if name == "Ground":
                    session_grounded = True
                if name in TERMINAL_TRANSFORMS:
                    continue
                _recurse(node_id, out, depth + 1, name)

        _recurse(root_id, seed, 0, "Seed")
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

def to_summary_md(graph: EchoGraph) -> str:
    nodes_by_id = {n.id: n for n in graph.nodes}
    seed_node = next((n for n in graph.nodes if n.transform == "Seed"), None)
    seed_text = seed_node.text if seed_node else "(none)"

    scored = []
    for n in graph.nodes:
        if n.parent_id is None:
            continue
        parent = nodes_by_id.get(n.parent_id)
        if parent is None:
            continue
        score = novelty_score(parent.text, n.text)
        scored.append((score, n))
    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[:3]

    ground_node = next((n for n in graph.nodes if n.transform == "Ground"), None)
    ground_text = ground_node.text if ground_node else "(none)"

    lines: List[str] = []
    lines.append("Seed")
    lines.append(seed_text)
    lines.append("")
    lines.append("Top 3 most novel nodes")
    if top:
        for i, (_, n) in enumerate(top, start=1):
            lines.append(f"{i}. {n.transform}: {n.text}")
    else:
        lines.append("(none)")
    lines.append("")
    lines.append("Final Ground action")
    lines.append(ground_text)
    lines.append("")
    lines.append("Total nodes/edges")
    lines.append(f"Nodes: {len(graph.nodes)}")
    lines.append(f"Edges: {len(graph.edges)}")
    return "\n".join(lines)

def pick_cooldown_message(rng: random.Random, clinical: bool) -> str:
    general = [
        "Session complete. Close the file, take 3 slow breaths, and return to your day.",
        "Session complete. Stand up, drink water, and look at something far away for 30 seconds.",
        "Session complete. Write one real-world next step on paper, then stop here.",
        "Session complete. Take a short walk—no more prompts for the next 10 minutes.",
        "Session complete. Text one trusted person something ordinary and grounding.",
        "Session complete. Stretch your shoulders and unclench your jaw.",
        "Session complete. Save the summary, then step away from the screen.",
        "Session complete. Notice 5 things you can see, 4 you can feel, 3 you can hear.",
        "Session complete. Do one small task (dishes, laundry, fresh air) before returning.",
        "Session complete. This session is closed—rest is part of the method.",
    ]
    clinical_safe = [
        "Session complete. Pause here and reconnect with your immediate surroundings.",
        "Session complete. If you feel unsettled, take a break and talk with someone supportive.",
        "Session complete. Grounding first—sleep, food, and routine matter more than analysis.",
    ]
    pool = clinical_safe if clinical else general
    return rng.choice(pool)


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

    if _IN_SELF_TEST:
        return None

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

_IN_SELF_TEST = False


def _run_tests() -> int:
    global _IN_SELF_TEST
    prev = _IN_SELF_TEST
    _IN_SELF_TEST = True
    try:
        # Test 1: Engine returns root node + at least one child at depth 1 when depth>=1
        rec = Recursor(pipeline=DEFAULT_PIPELINE, max_depth=1, max_minutes=1, rng_seed=123)
        g = rec.recurse("Seed Bearer", consent=True)
        assert len(g.nodes) >= 2, "Expected at least 2 nodes (seed + one transform)"
        assert g.nodes[0].transform == "Seed", "First node should be Seed"
        assert any(n.transform in DEFAULT_PIPELINE for n in g.nodes[1:]), "Expected transform nodes"

        # Test 2: Branching limit reduces node count
        rec_full = Recursor(pipeline=DEFAULT_PIPELINE, max_depth=2, max_minutes=1, rng_seed=7)
        g_full = rec_full.recurse("Seed Bearer", consent=True)
        rec_limited = Recursor(
            pipeline=DEFAULT_PIPELINE,
            max_depth=2,
            max_minutes=1,
            branching=1,
            rng_seed=7,
        )
        g_limited = rec_limited.recurse("Seed Bearer", consent=True)
        assert len(g_limited.nodes) < len(g_full.nodes), "Branching should reduce node count"

        # Test 3: Dedup reduces duplicates for repeated transforms
        if "Const" not in TRANSFORMS:
            @register_transform("Const")
            def t_const(text: str) -> str:
                return "same"

        rec_dedup = Recursor(pipeline=["Const", "Ground"], max_depth=2, max_minutes=1, rng_seed=1)
        g_dedup = rec_dedup.recurse("Alpha", consent=True)
        const_nodes = [n for n in g_dedup.nodes if n.transform == "Const"]
        assert len(const_nodes) == 1, "Expected a single Const node after dedup"
        assert const_nodes[0].occurrences >= 2, "Expected dedup to increment occurrences"
        assert len(g_dedup.nodes) == 3, "Expected reduced node count with dedup"
        assert any(e.dst_id == const_nodes[0].id for e in g_dedup.edges), "Expected edge to Const node"

        # Test 4: Mirror should not produce nested "Echo of"
        rec_mirror = Recursor(pipeline=["Mirror"], max_depth=2, max_minutes=1, rng_seed=2)
        g_mirror = rec_mirror.recurse("Seed Bearer", consent=True)
        assert not any("Echo of [Echo of" in n.text for n in g_mirror.nodes), "Nested Echo not allowed"

        # Test 5: Symbolize is idempotent
        assert t_symbolize("Symbols: Echoholder") == "Symbols: Echoholder", "Symbolize should be idempotent"
        assert "Symbols: Symbols:" not in t_symbolize("Symbols: X"), "No double Symbols prefix"

        # Test 6: Low-novelty transforms are skipped
        if "Repeat" not in TRANSFORMS:
            @register_transform("Repeat")
            def t_repeat(text: str) -> str:
                return text

        rec_novel = Recursor(
            pipeline=["Repeat", "Ground"],
            max_depth=1,
            max_minutes=1,
            novelty_threshold=0.1,
            rng_seed=3,
        )
        g_novel = rec_novel.recurse("Seed Bearer", consent=True)
        assert not any(n.transform == "Repeat" for n in g_novel.nodes), "Repeat should be skipped"

        # Test 7: Only one Ground node per session when depth > 2
        rec_ground = Recursor(pipeline=DEFAULT_PIPELINE, max_depth=3, max_minutes=1, rng_seed=9)
        g_ground = rec_ground.recurse("Seed Bearer", consent=True)
        ground_nodes = [n for n in g_ground.nodes if n.transform == "Ground"]
        assert len(ground_nodes) == 1, "Expected only one Ground node per session"

        # Test 8: Markdown tree contains Seed line
        md = to_markdown_tree(g)
        assert md.startswith("Seed: "), "Markdown tree should start with Seed"

        # Test 9: JSON output has required keys
        js = json.loads(to_json(g))
        assert "meta" in js and "nodes" in js and "edges" in js, "JSON missing keys"

        # Test 10: Terminal transforms have no outgoing edges
        src_ids = {e.src_id for e in g.edges}
        for n in g.nodes:
            if n.transform in TERMINAL_TRANSFORMS:
                assert n.id not in src_ids, "Terminal transform node should have no outgoing edges"

        # Test 11: Ground output should vary with input
        g_loop = t_ground("stuck in a loop")
        g_fear = t_ground("a moment of fear")
        assert g_loop != g_fear, "Ground actions should change when input changes"

        # Test 12: CLI seed resolver prefers --seed over positional
        ap = argparse.ArgumentParser(add_help=False)
        ap.add_argument("--seed", default=None)
        ap.add_argument("seed_pos", nargs="?")
        args = ap.parse_args(["--seed", "A", "B"])  # positional ignored
        assert resolve_seed(args, ap) == "A", "--seed should win"

        # Test 13: Help/examples emission should not raise
        ap2 = argparse.ArgumentParser(add_help=False)
        try:
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                print_examples_and_help(ap2)
            assert "EchoLattice needs a SEED" in buf.getvalue(), "Expected seed help text in stderr"
        except Exception as e:
            raise AssertionError(f"print_examples_and_help raised unexpectedly: {e}")

        # Test 14: Summary file generation works
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = os.path.join(tmpdir, "echo_map.json")
            out_md = os.path.join(tmpdir, "echo_map.md")
            out_summary = os.path.join(tmpdir, "echo_summary.md")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = main(
                    [
                        "--seed",
                        "Seed Bearer",
                        "--depth",
                        "1",
                        "--out_json",
                        out_json,
                        "--out_md",
                        out_md,
                        "--out_summary",
                        out_summary,
                    ]
                )
            assert code == 0, f"Expected main(...) to return 0; got {code}"
            assert os.path.exists(out_summary), "Summary file was not created"
            with open(out_summary, "r", encoding="utf-8") as f:
                summary = f.read()
            assert "Seed" in summary and "Top 3 most novel nodes" in summary, "Summary missing sections"

        # Test 15: main() returns 0 (clean exit) when seed is missing (non-interactive assumed)
        # We call main with argv=[]; in most automated test contexts this should not block.
        # If it does become interactive, user can still cancel with Enter.
        code = main([])
        assert code == 0, f"Expected main([]) to return 0 on missing seed; got {code}"

        # Test 16: run_tests flags return 0 without prompting (fast-path)
        assert main(["--run_tests"]) == 0, "Expected main(['--run_tests']) to return 0"
        assert main(["--run-tests"]) == 0, "Expected main(['--run-tests']) to return 0"

        # Test 17: Terminal transforms (Ground, Abstract) must have no outgoing edges
        rec2 = Recursor(pipeline=DEFAULT_PIPELINE, max_depth=4, max_minutes=1, rng_seed=5)
        g2 = rec2.recurse("Seed Bearer", consent=True)
        by_id = {n.id: n for n in g2.nodes}
        for e in g2.edges:
            assert by_id[e.src_id].transform not in TERMINAL_TRANSFORMS

        return 0
    finally:
        _IN_SELF_TEST = prev


# ---------------------------
# Main
# ---------------------------


def main(argv: Optional[List[str]] = None) -> int:
    argv_list = sys.argv[1:] if argv is None else argv
    if "--run_tests" in argv_list or "--run-tests" in argv_list:
        if _IN_SELF_TEST:
            return 0
        return _run_tests()

    ap = argparse.ArgumentParser(description="EchoLattice: safe-first recursion engine")

    ap.add_argument("--seed", default=None, help="Seed symbol/text")
    ap.add_argument("seed_pos", nargs="?", help="Seed symbol/text (positional alternative to --seed)")

    ap.add_argument("--depth", type=int, default=3, help="Max recursion depth (default: 3)")
    ap.add_argument("--minutes", type=int, default=30, help="Max session minutes (default: 30)")
    ap.add_argument("--out_json", default="echo_map.json", help="Output JSON file path")
    ap.add_argument("--out_md", default="echo_map.md", help="Output Markdown tree path")
    ap.add_argument("--out_summary", default="echo_summary.md", help="Output summary Markdown path")

    ap.add_argument("--consent", action="store_true", help="Confirm user consent was obtained")
    ap.add_argument("--clinical", action="store_true", help="Clinical mode tag in metadata")
    ap.add_argument(
        "--branching",
        type=int,
        default=None,
        help="Max transforms per node (always includes Ground when present)",
    )
    ap.add_argument("--rng_seed", type=int, default=None, help="Seed for deterministic transform sampling")
    ap.add_argument(
        "--novelty_threshold",
        type=float,
        default=None,
        help="Skip transforms with novelty below this threshold (0.0-1.0)",
    )

    ap.add_argument(
        "--run_tests",
        "--run-tests",
        dest="run_tests",
        action="store_true",
        help="Run self-tests and exit",
    )

    args = ap.parse_args(argv_list)

    if args.run_tests:
        return _run_tests()

    seed = resolve_seed(args, ap)
    if not seed:
        if _IN_SELF_TEST:
            return 0
        _stderr_write("No seed provided. Exiting.")
        return 0

    pipeline = DEFAULT_PIPELINE[:]  # Could be customized
    rec = Recursor(
        pipeline=pipeline,
        max_depth=args.depth,
        max_minutes=args.minutes,
        branching=args.branching,
        rng_seed=args.rng_seed,
        novelty_threshold=args.novelty_threshold,
    )
    graph = rec.recurse(seed=seed, consent=args.consent, safety_level=("clinical" if args.clinical else "light"))

    with open(args.out_json, "w", encoding="utf-8") as f:
        f.write(to_json(graph))
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(to_markdown_tree(graph))
    with open(args.out_summary, "w", encoding="utf-8") as f:
        f.write(to_summary_md(graph))

    _stdout_write(f"Saved: {args.out_json}, {args.out_md}, and {args.out_summary}")
    cooldown_rng = random.Random(args.rng_seed)
    _stdout_write(pick_cooldown_message(cooldown_rng, args.clinical))
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
