#!/usr/bin/env python3
"""Benchmark script for Legal QA API.

Evaluates model/API quality across multiple metrics:
- intent accuracy
- answer exact-match accuracy
- answer contains accuracy
- answer token-level F1
- success/message/endpoint accuracies
- strict pass rate (all expected checks per case)
- latency metrics

Usage:
  python evaluation/qa_benchmark.py \
    --dataset evaluation/qa_eval_dataset.example.json \
    --base-url http://localhost:8080 \
    --output evaluation/reports/qa_benchmark_report.json
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_ENDPOINT = "/api/ask/debug"


def normalize_text(value: str) -> str:
    text = (value or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(value: str) -> list[str]:
    normalized = normalize_text(value)
    if not normalized:
        return []
    return normalized.split()


def token_f1(prediction: str, reference: str) -> float:
    pred_tokens = tokenize(prediction)
    ref_tokens = tokenize(reference)
    if not pred_tokens and not ref_tokens:
        return 1.0
    if not pred_tokens or not ref_tokens:
        return 0.0

    pred_counter = Counter(pred_tokens)
    ref_counter = Counter(ref_tokens)
    overlap = sum((pred_counter & ref_counter).values())
    if overlap == 0:
        return 0.0

    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)
    return (2 * precision * recall) / (precision + recall)


def safe_float_mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * p
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return sorted_values[low]
    weight = rank - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def post_question(url: str, question: str, timeout_sec: int) -> tuple[dict[str, Any], float, str | None]:
    payload = json.dumps({"question": question}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8")
        latency_ms = (time.perf_counter() - start) * 1000.0
        return json.loads(raw), latency_ms, None
    except urllib.error.HTTPError as err:
        latency_ms = (time.perf_counter() - start) * 1000.0
        body = err.read().decode("utf-8", errors="replace")
        return {}, latency_ms, f"HTTP {err.code}: {body[:400]}"
    except Exception as err:  # pylint: disable=broad-except
        latency_ms = (time.perf_counter() - start) * 1000.0
        return {}, latency_ms, f"Request failed: {err}"


def evaluate_case(case: dict[str, Any], response: dict[str, Any], request_error: str | None) -> dict[str, Any]:
    question = case.get("question", "")
    answer = response.get("answer", "") if isinstance(response, dict) else ""

    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}

    if request_error is not None:
        checks["request_ok"] = False
        details["request_error"] = request_error
    else:
        checks["request_ok"] = True

    expected_intent = case.get("expected_intent")
    if expected_intent is not None:
        checks["intent_match"] = response.get("intent") == expected_intent
        details["pred_intent"] = response.get("intent")

    if "expected_success" in case:
        checks["success_match"] = response.get("success") == case.get("expected_success")
        details["pred_success"] = response.get("success")

    expected_message = case.get("expected_message")
    if expected_message is not None:
        checks["message_match"] = response.get("message") == expected_message
        details["pred_message"] = response.get("message")

    expected_endpoint_contains = case.get("expected_endpoint_contains")
    if expected_endpoint_contains is not None:
        endpoint = str(response.get("endpoint", ""))
        checks["endpoint_match"] = expected_endpoint_contains in endpoint
        details["pred_endpoint"] = endpoint

    expected_min_result_count = case.get("expected_min_result_count")
    if expected_min_result_count is not None:
        results = response.get("results") if isinstance(response.get("results"), list) else []
        checks["result_count_match"] = len(results) >= int(expected_min_result_count)
        details["pred_result_count"] = len(results)

    expected_answer_exact = case.get("expected_answer_exact")
    if expected_answer_exact is not None:
        checks["answer_exact_match"] = normalize_text(answer) == normalize_text(expected_answer_exact)

    expected_answer_contains = case.get("expected_answer_contains")
    if isinstance(expected_answer_contains, list) and expected_answer_contains:
        normalized_answer = normalize_text(answer)
        contains_all = all(normalize_text(item) in normalized_answer for item in expected_answer_contains)
        checks["answer_contains_match"] = contains_all

    expected_answer_regex = case.get("expected_answer_regex")
    if expected_answer_regex is not None:
        try:
            checks["answer_regex_match"] = re.search(expected_answer_regex, answer, re.IGNORECASE) is not None
        except re.error:
            checks["answer_regex_match"] = False
            details["regex_error"] = f"Invalid regex: {expected_answer_regex}"

    expected_answer_reference = case.get("expected_answer_reference")
    if expected_answer_reference is not None:
        details["answer_token_f1"] = token_f1(answer, expected_answer_reference)

    # Precision/Recall/F1 for result retrieval
    results = response.get("results") if isinstance(response.get("results"), list) else []
    expected_result_titles = case.get("expected_result_titles")
    if isinstance(expected_result_titles, list) and expected_result_titles:
        normalized_expected = [normalize_text(str(x)) for x in expected_result_titles]
        pred_result_titles = [normalize_text(str(r.get("title", ""))) for r in results] if results else []
        if pred_result_titles:
            relevant_found = sum(1 for title in pred_result_titles if any(exp in title for exp in normalized_expected))
            precision = relevant_found / len(pred_result_titles)
            recall = relevant_found / len(normalized_expected)
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            details["precision"] = round(precision, 4)
            details["recall"] = round(recall, 4)
            details["f1"] = round(f1, 4)

            expected_min_f1 = case.get("expected_min_f1")
            if expected_min_f1 is not None:
                checks["f1_match"] = f1 >= float(expected_min_f1)
    elif isinstance(expected_answer_contains, list) and expected_answer_contains:
        normalized_expected = [normalize_text(str(x)) for x in expected_answer_contains]
        normalized_answer = normalize_text(answer)
        matched = sum(1 for item in normalized_expected if item and item in normalized_answer)
        ratio = matched / len(normalized_expected)
        details["precision"] = round(ratio, 4)
        details["recall"] = round(ratio, 4)
        details["f1"] = round(ratio, 4)

    # Legal correctness check (manual annotation)
    auto_legal_correct = bool(checks.get("request_ok", False)) and bool(checks.get("intent_match", False))
    if "success_match" in checks:
        auto_legal_correct = auto_legal_correct and bool(checks["success_match"])
    if "message_match" in checks:
        auto_legal_correct = auto_legal_correct and bool(checks["message_match"])

    if "legal_correctness" in case:
        expected_legal_correctness = bool(case.get("legal_correctness"))
        checks["legal_correctness"] = expected_legal_correctness == auto_legal_correct
        details["legal_correctness"] = expected_legal_correctness
    else:
        checks["legal_correctness"] = auto_legal_correct
        details["legal_correctness_auto"] = auto_legal_correct

    # Completeness check (manual annotation)
    answer_length = len(answer.strip())
    if bool(response.get("success", False)):
        auto_complete = answer_length >= 50
    else:
        auto_complete = bool(answer.strip())

    if "completeness" in case:
        expected_complete = bool(case.get("completeness"))
        checks["completeness"] = expected_complete == auto_complete
        details["completeness"] = expected_complete
    else:
        checks["completeness"] = auto_complete
        details["completeness_auto"] = auto_complete
    details["answer_length"] = answer_length

    # Hallucination check (manual annotation)
    normalized_answer = normalize_text(answer)
    auto_hallucinating = bool(response.get("success", False)) and (
        not bool(results)
        or not bool(response.get("endpoint"))
        or not bool(answer.strip())
        or "khong ro" in normalized_answer
    )

    if "has_hallucination" in case:
        expected_hallucination = bool(case.get("has_hallucination", False))
        checks["no_hallucination"] = (not expected_hallucination) == (not auto_hallucinating)
        details["has_hallucination"] = expected_hallucination
    else:
        checks["no_hallucination"] = not auto_hallucinating
        details["hallucination_auto"] = auto_hallucinating


    strict_pass = all(checks.values()) if checks else False

    return {
        "id": case.get("id"),
        "question": question,
        "checks": checks,
        "strict_pass": strict_pass,
        "details": details,
        "prediction": {
            "intent": response.get("intent"),
            "success": response.get("success"),
            "message": response.get("message"),
            "endpoint": response.get("endpoint"),
            "answer": answer,
            "result_count": len(response.get("results", [])) if isinstance(response.get("results"), list) else 0,
        },
        "raw_response": response,
        "request_error": request_error,
    }


def summarize(case_results: list[dict[str, Any]], latencies_ms: list[float]) -> dict[str, Any]:
    def compute_intent_prf() -> tuple[float | None, float | None, float | None]:
        eligible = [
            r
            for r in case_results
            if isinstance(r.get("details", {}).get("pred_intent"), str) and "intent_match" in r.get("checks", {})
        ]
        if not eligible:
            return None, None, None

        tp = sum(1 for r in eligible if r["checks"]["intent_match"])
        fp = len(eligible) - tp
        fn = fp

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0
        return round(precision, 4), round(recall, 4), round(f1, 4)

    def ratio_for_check(check_name: str) -> dict[str, Any]:
        eligible = [r for r in case_results if check_name in r["checks"]]
        if not eligible:
            return {"eligible": 0, "correct": 0, "accuracy": 0.0}
        correct = sum(1 for r in eligible if r["checks"][check_name])
        return {
            "eligible": len(eligible),
            "correct": correct,
            "accuracy": round(correct / len(eligible), 4),
        }

    strict_pass_count = sum(1 for r in case_results if r["strict_pass"])
    intent_precision, intent_recall, intent_f1 = compute_intent_prf()

    token_f1_values: list[float] = []
    for row in case_results:
        f1 = row.get("details", {}).get("answer_token_f1")
        if isinstance(f1, (float, int)):
            token_f1_values.append(float(f1))

    # Precision/Recall/F1 averaging
    precision_values: list[float] = []
    recall_values: list[float] = []
    f1_values: list[float] = []
    for row in case_results:
        details = row.get("details", {})
        if "precision" in details and isinstance(details["precision"], (float, int)):
            precision_values.append(float(details["precision"]))
        if "recall" in details and isinstance(details["recall"], (float, int)):
            recall_values.append(float(details["recall"]))
        if "f1" in details and isinstance(details["f1"], (float, int)):
            f1_values.append(float(details["f1"]))

    if not precision_values and intent_precision is not None:
        precision_values.append(intent_precision)
    if not recall_values and intent_recall is not None:
        recall_values.append(intent_recall)
    if not f1_values and intent_f1 is not None:
        f1_values.append(intent_f1)

    token_f1_avg = round(safe_float_mean(token_f1_values), 4) if token_f1_values else (
        round(safe_float_mean(f1_values), 4) if f1_values else 0.0
    )
    precision_avg = round(safe_float_mean(precision_values), 4) if precision_values else 0.0
    recall_avg = round(safe_float_mean(recall_values), 4) if recall_values else 0.0
    f1_retrieval_avg = round(safe_float_mean(f1_values), 4) if f1_values else 0.0


    return {
        "total_cases": len(case_results),
        "strict_pass": {
            "passed": strict_pass_count,
            "rate": round(strict_pass_count / len(case_results), 4) if case_results else 0.0,
        },
        "metrics": {
            "intent_accuracy": ratio_for_check("intent_match"),
            "success_accuracy": ratio_for_check("success_match"),
            "message_accuracy": ratio_for_check("message_match"),
            "endpoint_accuracy": ratio_for_check("endpoint_match"),
            "result_count_accuracy": ratio_for_check("result_count_match"),
            "answer_exact_accuracy": ratio_for_check("answer_exact_match"),
            "answer_contains_accuracy": ratio_for_check("answer_contains_match"),
            "answer_regex_accuracy": ratio_for_check("answer_regex_match"),
            "request_success_rate": ratio_for_check("request_ok"),
            "answer_token_f1": {
                "eligible": len(token_f1_values),
                "average_f1": token_f1_avg,
            },
            "precision": {
                "eligible": len(precision_values),
                "average": precision_avg,
            },
            "recall": {
                "eligible": len(recall_values),
                "average": recall_avg,
            },
            "f1_retrieval": {
                "eligible": len(f1_values),
                "average": f1_retrieval_avg,
            },
            "legal_correctness": ratio_for_check("legal_correctness"),
            "completeness": ratio_for_check("completeness"),
            "no_hallucination": ratio_for_check("no_hallucination"),
        },
        "latency_ms": {
            "avg": round(safe_float_mean(latencies_ms), 2) if latencies_ms else 0.0,
            "p50": round(percentile(latencies_ms, 0.5), 2) if latencies_ms else 0.0,
            "p95": round(percentile(latencies_ms, 0.95), 2) if latencies_ms else 0.0,
            "max": round(max(latencies_ms), 2) if latencies_ms else 0.0,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Legal QA API with custom evaluation dataset")
    parser.add_argument("--dataset", required=True, help="Path to evaluation dataset JSON")
    parser.add_argument("--base-url", default="http://localhost:8080", help="Base API URL")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="QA endpoint path")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--max-cases", type=int, default=0, help="Run only first N cases (0 means all)")
    parser.add_argument(
        "--output",
        default="evaluation/reports/qa_benchmark_report.json",
        help="Path to output report JSON",
    )
    parser.add_argument(
        "--confidence-output",
        default="",
        help=(
            "Optional path for confidence-only metrics JSON. "
            "If omitted, auto-generates <output_stem>.confidence.json in the same folder."
        ),
    )
    return parser.parse_args()


def build_confidence_report(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary", {})
    metrics = summary.get("metrics", {})

    def num(value: Any) -> float:
        return round(float(value), 4) if isinstance(value, (int, float)) else 0.0

    confidence_metrics = {
        "intent_accuracy": num(metrics.get("intent_accuracy", {}).get("accuracy")),
        "answer_exact_accuracy": num(metrics.get("answer_exact_accuracy", {}).get("accuracy")),
        "answer_contains_accuracy": num(metrics.get("answer_contains_accuracy", {}).get("accuracy")),
        "answer_regex_accuracy": num(metrics.get("answer_regex_accuracy", {}).get("accuracy")),
        "answer_token_f1": num(metrics.get("answer_token_f1", {}).get("average_f1")),
        "success_accuracy": num(metrics.get("success_accuracy", {}).get("accuracy")),
        "message_accuracy": num(metrics.get("message_accuracy", {}).get("accuracy")),
        "endpoint_accuracy": num(metrics.get("endpoint_accuracy", {}).get("accuracy")),
        "request_success_rate": num(metrics.get("request_success_rate", {}).get("accuracy")),
        "strict_pass_rate": num(summary.get("strict_pass", {}).get("rate")),
        "precision": num(metrics.get("precision", {}).get("average")),
        "recall": num(metrics.get("recall", {}).get("average")),
        "f1_retrieval": num(metrics.get("f1_retrieval", {}).get("average")),
        "legal_correctness": num(metrics.get("legal_correctness", {}).get("accuracy")),
        "completeness": num(metrics.get("completeness", {}).get("accuracy")),
        "hallucination_rate": round(1.0 - num(metrics.get("no_hallucination", {}).get("accuracy")), 4),
    }

    scored_values = [value for value in confidence_metrics.values() if isinstance(value, (float, int))]
    overall_confidence = round(safe_float_mean([float(v) for v in scored_values]), 4) if scored_values else None

    return {
        "meta": {
            "target_url": report.get("meta", {}).get("target_url"),
            "dataset": report.get("meta", {}).get("dataset"),
            "executed_at_epoch": report.get("meta", {}).get("executed_at_epoch"),
            "cases_executed": report.get("meta", {}).get("cases_executed"),
            "source_report": None,
        },
        "confidence": {
            "overall_confidence_score": overall_confidence,
            "metrics": confidence_metrics,
            "latency_ms": summary.get("latency_ms", {}),
        },
    }


def main() -> None:
    args = parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        raise SystemExit(f"Dataset file not found: {dataset_path}")

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(dataset, list):
        raise SystemExit("Dataset JSON must be a list of test cases.")

    if args.max_cases and args.max_cases > 0:
        dataset = dataset[: args.max_cases]

    url = args.base_url.rstrip("/") + "/" + args.endpoint.lstrip("/")

    case_results: list[dict[str, Any]] = []
    latencies_ms: list[float] = []

    for index, case in enumerate(dataset, start=1):
        question = str(case.get("question", "")).strip()
        if not question:
            case_results.append(
                {
                    "id": case.get("id"),
                    "question": "",
                    "checks": {"request_ok": False},
                    "strict_pass": False,
                    "details": {"request_error": "Empty question in dataset."},
                    "prediction": {},
                    "raw_response": {},
                    "request_error": "Empty question in dataset.",
                }
            )
            continue

        response, latency_ms, req_err = post_question(url, question, timeout_sec=args.timeout)
        latencies_ms.append(latency_ms)
        row = evaluate_case(case, response, req_err)
        case_results.append(row)

        print(
            f"[{index}/{len(dataset)}] id={case.get('id', index)} "
            f"strict_pass={row['strict_pass']} latency={latency_ms:.1f}ms"
        )

    summary = summarize(case_results, latencies_ms)

    failed_cases = [
        {
            "id": r.get("id"),
            "question": r.get("question"),
            "failed_checks": [name for name, passed in r.get("checks", {}).items() if not passed],
            "request_error": r.get("request_error"),
            "prediction": r.get("prediction"),
        }
        for r in case_results
        if not r.get("strict_pass")
    ]

    report = {
        "meta": {
            "target_url": url,
            "dataset": str(dataset_path),
            "executed_at_epoch": int(time.time()),
            "cases_executed": len(case_results),
        },
        "summary": summary,
        "failed_cases": failed_cases,
        "case_results": case_results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    confidence_path = Path(args.confidence_output) if args.confidence_output else output_path.with_suffix(".confidence.json")
    confidence_path.parent.mkdir(parents=True, exist_ok=True)

    confidence_report = build_confidence_report(report)
    confidence_report["meta"]["source_report"] = str(output_path)
    confidence_path.write_text(json.dumps(confidence_report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== Benchmark Summary ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nReport written to: {output_path}")
    print(f"Confidence report written to: {confidence_path}")


if __name__ == "__main__":
    main()
