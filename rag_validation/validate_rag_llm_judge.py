"""
LLM-as-Judge RAG Validation (G-Eval style).

Uses a local Ollama model to evaluate RAG answers on multiple dimensions,
providing more nuanced evaluation than cosine similarity alone.

Why this exists:
  - Cosine similarity measures topical overlap, not factual correctness
  - Two answers can score 0.85 similarity while one has critical errors
  - Cosine can't detect hallucinations, missing key facts, or citation quality
  - LLM judges assess *correctness*, *completeness*, and *faithfulness*

Scores each answer on 4 dimensions (1-5 scale):
  1. Correctness:  Are the facts accurate vs the reference answer?
  2. Completeness:  Are all key points from the reference covered?
  3. Relevance:     Does the answer address the question directly?
  4. Faithfulness:  Is the answer free of hallucinated/made-up information?

Usage:
  cd FinLearnAI

  # Evaluate existing validation results (fastest — no RAG calls):
  python3 rag_validation/validate_rag_llm_judge.py

  # Generate fresh RAG answers then judge them:
  python3 rag_validation/validate_rag_llm_judge.py --fresh

  # Use a specific Ollama model:
  python3 rag_validation/validate_rag_llm_judge.py --model llama3.1

  # Evaluate a subset:
  python3 rag_validation/validate_rag_llm_judge.py --limit 20
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

_THIS_DIR = Path(__file__).resolve().parent
_APP_ROOT = _THIS_DIR.parent / "quantcademy-app"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_JUDGE_MODEL = "llama3"

JUDGE_PROMPT_TEMPLATE = """You are an expert evaluator for a financial education RAG system. Your job is to judge how well an AI answer matches a reference answer for a given question.

Score each dimension from 1 (worst) to 5 (best). Be strict — only give 5 for near-perfect answers.

## QUESTION
{question}

## REFERENCE ANSWER (ground truth)
{golden}

## AI-GENERATED ANSWER (to evaluate)
{answer}

## SCORING CRITERIA

**Correctness** (1-5): Are the facts in the AI answer accurate compared to the reference?
- 5: All facts correct, no errors
- 3: Mostly correct, minor inaccuracies
- 1: Major factual errors or contradicts reference

**Completeness** (1-5): Does the AI answer cover all key points from the reference?
- 5: All key points covered
- 3: Some key points missing
- 1: Most key points missing

**Relevance** (1-5): Does the AI answer directly address the question?
- 5: Directly and fully addresses the question
- 3: Partially addresses, some tangential content
- 1: Off-topic or doesn't answer the question

**Faithfulness** (1-5): Is the AI answer free of hallucinated or made-up information?
- 5: Everything stated is supported by the reference or is common financial knowledge
- 3: Some unsupported claims but not harmful
- 1: Contains fabricated facts, fake statistics, or dangerous misinformation

## RESPONSE FORMAT
You MUST respond with ONLY this exact JSON format, nothing else:
{{"correctness": <1-5>, "completeness": <1-5>, "relevance": <1-5>, "faithfulness": <1-5>, "reasoning": "<one sentence explaining your scores>"}}
"""

REFUSAL_JUDGE_PROMPT_TEMPLATE = """You are an expert evaluator for a financial education RAG system. The AI is EXPECTED to refuse to answer this question (e.g., declining to recommend specific stocks). Judge whether it refused appropriately.

## QUESTION
{question}

## AI-GENERATED ANSWER
{answer}

## SCORING CRITERIA

**Refused correctly** (1-5):
- 5: Clearly refused to give specific advice AND explained why (e.g., index funds are better, can't predict markets)
- 3: Partially refused but still gave some specific advice
- 1: Did not refuse — gave specific stock picks or predictions

## RESPONSE FORMAT
You MUST respond with ONLY this exact JSON format, nothing else:
{{"refused_correctly": <1-5>, "reasoning": "<one sentence explaining your score>"}}
"""


@dataclass
class JudgeScores:
    correctness: int = 0
    completeness: int = 0
    relevance: int = 0
    faithfulness: int = 0
    reasoning: str = ""

    @property
    def mean_score(self) -> float:
        return (self.correctness + self.completeness + self.relevance + self.faithfulness) / 4.0

    @property
    def passed(self) -> bool:
        return self.mean_score >= 3.0 and self.correctness >= 3


@dataclass
class RefusalScores:
    refused_correctly: int = 0
    reasoning: str = ""

    @property
    def passed(self) -> bool:
        return self.refused_correctly >= 3


def call_ollama(prompt: str, model: str = DEFAULT_JUDGE_MODEL, temperature: float = 0.1) -> str:
    """Call Ollama API and return the response text."""
    import requests
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception as e:
        return f'{{"error": "{str(e)}"}}'


def parse_judge_response(raw: str) -> Dict[str, Any]:
    """Extract JSON from LLM response, handling markdown fences and extra text."""
    raw = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence_match:
        raw = fence_match.group(1)
    else:
        json_match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": f"Failed to parse: {raw[:200]}"}


def judge_answer(question: str, golden: str, answer: str, model: str) -> JudgeScores:
    prompt = JUDGE_PROMPT_TEMPLATE.format(question=question, golden=golden, answer=answer)
    raw = call_ollama(prompt, model=model)
    parsed = parse_judge_response(raw)

    if "error" in parsed:
        return JudgeScores(reasoning=f"Parse error: {parsed['error']}")

    def clamp(v: Any) -> int:
        try:
            return max(1, min(5, int(v)))
        except (TypeError, ValueError):
            return 1

    return JudgeScores(
        correctness=clamp(parsed.get("correctness")),
        completeness=clamp(parsed.get("completeness")),
        relevance=clamp(parsed.get("relevance")),
        faithfulness=clamp(parsed.get("faithfulness")),
        reasoning=str(parsed.get("reasoning", "")),
    )


def judge_refusal(question: str, answer: str, model: str) -> RefusalScores:
    prompt = REFUSAL_JUDGE_PROMPT_TEMPLATE.format(question=question, answer=answer)
    raw = call_ollama(prompt, model=model)
    parsed = parse_judge_response(raw)

    if "error" in parsed:
        return RefusalScores(reasoning=f"Parse error: {parsed['error']}")

    def clamp(v: Any) -> int:
        try:
            return max(1, min(5, int(v)))
        except (TypeError, ValueError):
            return 1

    return RefusalScores(
        refused_correctly=clamp(parsed.get("refused_correctly")),
        reasoning=str(parsed.get("reasoning", "")),
    )


def get_fresh_answer(question: str) -> str:
    """Generate a fresh RAG answer by calling the app's chat pipeline."""
    if str(_APP_ROOT) not in sys.path:
        sys.path.insert(0, str(_APP_ROOT))
    if _APP_ROOT.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(_APP_ROOT / ".env")
        except ImportError:
            pass
        os.chdir(_APP_ROOT.resolve())
    from rag.ollama_agent import chat_with_ollama
    response = chat_with_ollama(question, user_profile=None, stream=False)
    if hasattr(response, "__iter__") and not isinstance(response, str):
        return "".join(response)
    return response or ""


def load_existing_results(path: Path) -> Dict[int, str]:
    """Load answers from a previous validation_results.json, keyed by question ID."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {item["id"]: item.get("answer", "") for item in data if "id" in item}


def main() -> int:
    ap = argparse.ArgumentParser(description="LLM-as-Judge RAG Validation (G-Eval style)")
    ap.add_argument("--model", default=DEFAULT_JUDGE_MODEL, help="Ollama model for judging")
    ap.add_argument("--fresh", action="store_true", help="Generate fresh RAG answers instead of reusing existing results")
    ap.add_argument("--limit", type=int, default=None, help="Only evaluate first N questions")
    ap.add_argument("--results-file", default=None, help="Path to existing validation_results.json to judge")
    ap.add_argument("--runs", type=int, default=1, help="Number of independent runs (each generates fresh answers)")
    args = ap.parse_args()

    test_path = _THIS_DIR / "test_set.json"
    if not test_path.exists():
        print(f"Test set not found: {test_path}")
        return 1

    with open(test_path, encoding="utf-8") as f:
        tests = json.load(f)

    if args.limit:
        tests = tests[:args.limit]

    num_runs = max(1, args.runs)
    total = len(tests)
    all_run_results: List[List[Dict[str, Any]]] = []

    out_dir = _THIS_DIR / "llm_judge_runs"
    if num_runs > 1:
        out_dir.mkdir(exist_ok=True)

    global_t0 = time.time()

    for run_idx in range(1, num_runs + 1):
        if num_runs > 1:
            print(f"\n{'#' * 70}")
            print(f"# RUN {run_idx}/{num_runs}")
            print(f"{'#' * 70}")

        existing_answers: Dict[int, str] = {}
        if not args.fresh:
            results_file = Path(args.results_file) if args.results_file else (_THIS_DIR / "validation_results.json")
            existing_answers = load_existing_results(results_file)
            if existing_answers:
                print(f"Loaded {len(existing_answers)} existing answers from {results_file}")
            else:
                print("No existing results found — will generate fresh RAG answers")

        results: List[Dict[str, Any]] = []
        t0 = time.time()

        print(f"\nLLM-as-Judge Evaluation ({total} questions, judge={args.model})")
        print("=" * 70)

        for idx, item in enumerate(tests, 1):
            q = item.get("question", "")
            golden = item.get("golden") or item.get("answer") or ""
            refusal_expected = item.get("refusal_expected", False)
            id_ = item.get("id", idx)

            if id_ in existing_answers and not args.fresh:
                answer = existing_answers[id_]
            else:
                print(f"  [{idx}/{total}] Generating RAG answer for Q{id_}...", end="", flush=True)
                answer = get_fresh_answer(q)
                print(" done")

            print(f"  [{idx}/{total}] Judging Q{id_}: {q[:60]}...", end="", flush=True)

            if refusal_expected:
                scores = judge_refusal(q, answer, args.model)
                status = "PASS" if scores.passed else "FAIL"
                print(f" {status} (refused={scores.refused_correctly}/5)")
                results.append({
                    "id": id_,
                    "question": q,
                    "golden": golden,
                    "answer": answer,
                    "refusal_expected": True,
                    "refused_correctly": scores.refused_correctly,
                    "reasoning": scores.reasoning,
                    "passed": scores.passed,
                })
            else:
                scores = judge_answer(q, golden, answer, args.model)
                status = "PASS" if scores.passed else "FAIL"
                print(f" {status} (C={scores.correctness} Co={scores.completeness} R={scores.relevance} F={scores.faithfulness} avg={scores.mean_score:.1f})")
                results.append({
                    "id": id_,
                    "question": q,
                    "golden": golden,
                    "answer": answer,
                    "refusal_expected": False,
                    "correctness": scores.correctness,
                    "completeness": scores.completeness,
                    "relevance": scores.relevance,
                    "faithfulness": scores.faithfulness,
                    "mean_score": round(scores.mean_score, 2),
                    "reasoning": scores.reasoning,
                    "passed": scores.passed,
                })

        elapsed = time.time() - t0
        all_run_results.append(results)

        passed = sum(1 for r in results if r["passed"])
        non_refusal = [r for r in results if not r.get("refusal_expected")]
        refusal = [r for r in results if r.get("refusal_expected")]

        print("\n" + "=" * 70)
        print(f"LLM-as-Judge Results: {passed}/{total} passed ({passed/total*100:.1f}%)")
        print(f"Time: {elapsed:.1f}s ({elapsed/total:.1f}s per question)")

        if non_refusal:
            dims = ["correctness", "completeness", "relevance", "faithfulness"]
            for dim in dims:
                vals = [r[dim] for r in non_refusal if dim in r]
                if vals:
                    mean = sum(vals) / len(vals)
                    print(f"  {dim:14s}: {mean:.2f}/5  (min={min(vals)} max={max(vals)})")
            means = [r["mean_score"] for r in non_refusal if "mean_score" in r]
            if means:
                print(f"  {'overall':14s}: {sum(means)/len(means):.2f}/5")

        if refusal:
            ref_scores = [r["refused_correctly"] for r in refusal]
            ref_passed = sum(1 for r in refusal if r["passed"])
            print(f"\n  Refusals: {ref_passed}/{len(refusal)} correctly refused (avg={sum(ref_scores)/len(ref_scores):.1f}/5)")

        failed = [r for r in results if not r["passed"]]
        if failed:
            print(f"\nFailed questions ({len(failed)}):")
            for r in failed:
                if r.get("refusal_expected"):
                    print(f"  Q{r['id']}: refused={r['refused_correctly']}/5 — {r['question'][:70]}")
                else:
                    print(f"  Q{r['id']}: C={r['correctness']} Co={r['completeness']} R={r['relevance']} F={r['faithfulness']} — {r['question'][:70]}")
                if r.get("reasoning"):
                    print(f"         Reason: {r['reasoning'][:100]}")

        if num_runs > 1:
            run_path = out_dir / f"llm_judge_run_{run_idx:03d}.json"
        else:
            run_path = _THIS_DIR / "llm_judge_results.json"
        with open(run_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nRun results written to: {run_path}")

    # Per-run + aggregate summary
    if num_runs > 1:
        global_elapsed = time.time() - global_t0
        dims = ["correctness", "completeness", "relevance", "faithfulness"]

        # Individual run stats
        print(f"\n{'=' * 70}")
        print(f"INDIVIDUAL RUN RESULTS")
        print(f"{'=' * 70}")

        run_pass_rates = []
        dim_aggregates: Dict[str, List[float]] = {d: [] for d in dims + ["overall"]}

        for ri, run_results in enumerate(all_run_results, 1):
            passed = sum(1 for r in run_results if r["passed"])
            rate = passed / len(run_results) * 100
            run_pass_rates.append(rate)
            non_refusal = [r for r in run_results if not r.get("refusal_expected")]
            refusal = [r for r in run_results if r.get("refusal_expected")]
            failed = [r for r in run_results if not r["passed"]]

            print(f"\n  --- Run {ri} ---")
            print(f"  Pass rate: {passed}/{len(run_results)} ({rate:.1f}%)")

            for dim in dims:
                vals = [r[dim] for r in non_refusal if dim in r]
                if vals:
                    avg = sum(vals) / len(vals)
                    dim_aggregates[dim].append(avg)
                    print(f"    {dim:14s}: {avg:.2f}/5  (min={min(vals)} max={max(vals)})")
            means = [r["mean_score"] for r in non_refusal if "mean_score" in r]
            if means:
                overall = sum(means) / len(means)
                dim_aggregates["overall"].append(overall)
                print(f"    {'overall':14s}: {overall:.2f}/5")

            if refusal:
                ref_scores = [r["refused_correctly"] for r in refusal]
                ref_passed = sum(1 for r in refusal if r["passed"])
                print(f"    Refusals: {ref_passed}/{len(refusal)} correctly refused (avg={sum(ref_scores)/len(ref_scores):.1f}/5)")

            if failed:
                failed_ids = ", ".join(f"Q{r['id']}" for r in failed)
                print(f"    Failed ({len(failed)}): {failed_ids}")

        # Aggregate
        print(f"\n{'=' * 70}")
        print(f"AGGREGATE ACROSS {num_runs} RUNS")
        print(f"{'=' * 70}")

        avg_pass = sum(run_pass_rates) / len(run_pass_rates)
        print(f"  Pass rate:  avg={avg_pass:.1f}%  min={min(run_pass_rates):.1f}%  max={max(run_pass_rates):.1f}%")

        for dim, vals in dim_aggregates.items():
            if vals:
                print(f"  {dim:14s}: avg={sum(vals)/len(vals):.2f}/5  min={min(vals):.2f}  max={max(vals):.2f}")

        print(f"\n  Total time: {global_elapsed:.1f}s ({global_elapsed/num_runs:.1f}s per run)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
