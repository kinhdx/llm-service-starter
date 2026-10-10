"""Evaluation gate for the triage task.

    uv run python evals/run.py                  replay recorded answers (default; what CI runs, no API key)
    uv run python evals/run.py --mode record    call the model and refresh the recordings
    uv run python evals/run.py --mode live      call the model without saving

Scores every case in evals/cases.jsonl, writes evals/report.md, and exits with status 1 when any score is
below evals/thresholds.json. fraud_recall and human_route_recall are gated at 1.0: a missed fraud case is a
failure regardless of the averages.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from service.llm import AnthropicClient, MissingRecording, ReplayClient
from service.triage import DEFAULT_MODEL, load_prompt, triage

HERE = Path(__file__).resolve().parent


def score(rows: list[dict]) -> dict:
    fraud = [r for r in rows if r["want_category"] == "fraud"]
    human = [r for r in rows if r["want_category"] == "fraud" or r["want_legal"]]
    return {
        "cases": len(rows),
        "category_accuracy": round(statistics.mean(r["category"] == r["want_category"] for r in rows), 3),
        "urgency_accuracy": round(statistics.mean(r["urgency"] == r["want_urgency"] for r in rows), 3),
        "fraud_recall": round(statistics.mean(r["category"] == "fraud" for r in fraud), 3) if fraud else None,
        "human_route_recall": round(statistics.mean(r["route"] == "human" for r in human), 3) if human else None,
        "max_cost_per_case_usd": round(max(r["cost_usd"] for r in rows), 5),
        "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 4),
    }


def gate(scores: dict, thresholds: dict) -> list[str]:
    failures = []
    for name, limit in thresholds.items():
        value = scores.get(name)
        if value is None:
            failures.append(f"{name} was not measured, required by the thresholds")
            continue
        if name.startswith("max_") and value > limit or not name.startswith("max_") and value < limit:
            failures.append(f"{name} = {value}, required {'<=' if name.startswith('max_') else '>='} {limit}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["replay", "record", "live"], default="replay")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args(argv)
    load_dotenv(find_dotenv(usecwd=True))
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    prompt = load_prompt()
    inner = None if args.mode == "replay" else AnthropicClient()
    client = ReplayClient(HERE / "recordings", args.mode, inner)
    cases = [json.loads(line) for line in (HERE / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line]
    rows = []
    for case in cases:
        try:
            result = triage(case["text"], client, prompt, args.model)
        except MissingRecording as e:
            print(f"{case['id']}: {e}")
            return 1
        rows.append({"id": case["id"], "category": result.category, "urgency": result.urgency,
                     "route": result.route, "want_category": case["category"], "want_urgency": case["urgency"],
                     "want_legal": case["legal"], "cost_usd": result.usage.cost_usd})

    scores = score(rows)
    failures = gate(scores, json.loads((HERE / "thresholds.json").read_text(encoding="utf-8")))
    misses = [r for r in rows if r["category"] != r["want_category"] or r["urgency"] != r["want_urgency"]]
    lines = [f"# Triage evaluation: {args.model}", "", f"Prompt version: {prompt.version}", "",
             "| Metric | Value |", "|---|---|", *[f"| {k} | {v} |" for k, v in scores.items()], "",
             "Gate: " + ("passed" if not failures else "FAILED: " + "; ".join(failures)), "",
             "| Case | Category (expected) | Urgency (expected) |", "|---|---|---|",
             *[f"| {r['id']} | {r['category']} ({r['want_category']}) | {r['urgency']} ({r['want_urgency']}) |"
               for r in misses]]
    (HERE / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(scores, indent=1))
    print("gate:", "passed" if not failures else "FAILED")
    for f in failures:
        print("  ", f)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
