"""
Evaluation script to compare category classification approaches.

Compares:
1. Old approach: Confidence-based (division of results)
2. New approach: RAG-based (LLM with retrieved context)

Usage:
    python tests/evaluate_category_classification.py
    python tests/evaluate_category_classification.py --queries 5
    python tests/evaluate_category_classification.py --debug
"""

import sys
import time
import argparse
import json
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from category_test_cases import CATEGORY_TEST_CASES, CategoryTestCase, QueryType

# Import both search implementations
from src.search import NaturalLanguageSearch as OldSearch
from src.search_rag import RAGNaturalLanguageSearch as RAGSearch


@dataclass
class EvaluationResult:
    """Result of evaluating a single test case."""
    query: str
    query_type: str
    expected_category: str
    should_apply_filter: bool
    min_confidence: float

    # Old approach results
    old_detected_category: str
    old_confidence: float
    old_filter_applied: bool
    old_query_time_ms: float

    # RAG approach results
    rag_detected_category: str
    rag_confidence: float
    rag_filter_applied: bool
    rag_query_time_ms: float
    rag_reasoning: str

    # Evaluation metrics
    old_category_correct: bool
    rag_category_correct: bool
    old_filter_decision_correct: bool
    rag_filter_decision_correct: bool
    old_confidence_meets_threshold: bool
    rag_confidence_meets_threshold: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class CategoryClassificationEvaluator:
    """Evaluator for comparing category classification approaches."""

    def __init__(self, debug: bool = False):
        """Initialize evaluator with both search engines."""
        self.debug = debug
        self.old_search = OldSearch()
        self.rag_search = RAGSearch()

    def evaluate_test_case(self, test_case: CategoryTestCase) -> EvaluationResult:
        """
        Evaluate a single test case with both approaches.

        Args:
            test_case: Test case to evaluate

        Returns:
            EvaluationResult with comparison metrics
        """
        query = test_case.query

        print(f"\n{'='*70}")
        print(f"Query: '{query}'")
        print(f"Type: {test_case.query_type.value}")
        print(f"Expected: {test_case.expected_category or 'None (ambiguous)'}")
        print('='*70)

        # Run old approach
        print("\n[1/2] Running OLD approach (confidence-based)...")
        old_response = self.old_search.search(query, max_results=20, debug=self.debug)

        # Run RAG approach
        print("\n[2/2] Running RAG approach (LLM-based)...")
        rag_response = self.rag_search.search(query, max_results=20, debug=self.debug)

        # Extract metrics from responses
        old_detected = old_response.detected_category
        old_confidence = old_response.category_confidence or 0.0
        old_applied = old_response.category_applied or False
        old_time = old_response.query_time_ms

        rag_detected = rag_response.detected_category
        rag_confidence = rag_response.category_confidence or 0.0
        rag_applied = rag_response.category_applied or False
        rag_time = rag_response.query_time_ms
        rag_reasoning = rag_response.typesense_query.get("llm_reasoning", "N/A")

        # Evaluate correctness
        old_category_correct = self._is_category_correct(
            old_detected,
            test_case.expected_category,
            test_case.alternative_categories
        )
        rag_category_correct = self._is_category_correct(
            rag_detected,
            test_case.expected_category,
            test_case.alternative_categories
        )

        old_filter_correct = (old_applied == test_case.should_apply_filter)
        rag_filter_correct = (rag_applied == test_case.should_apply_filter)

        old_confidence_ok = (old_confidence >= test_case.min_confidence) if test_case.should_apply_filter else True
        rag_confidence_ok = (rag_confidence >= test_case.min_confidence) if test_case.should_apply_filter else True

        # Print comparison
        print(f"\n--- Comparison ---")
        print(f"OLD: Category='{old_detected}', Confidence={old_confidence:.2f}, Applied={old_applied}, Time={old_time:.0f}ms")
        print(f"RAG: Category='{rag_detected}', Confidence={rag_confidence:.2f}, Applied={rag_applied}, Time={rag_time:.0f}ms")
        print(f"RAG Reasoning: {rag_reasoning[:100]}...")

        print(f"\n--- Evaluation ---")
        print(f"OLD Category Correct: {'✓' if old_category_correct else '✗'}")
        print(f"RAG Category Correct: {'✓' if rag_category_correct else '✗'}")
        print(f"OLD Filter Decision: {'✓' if old_filter_correct else '✗'}")
        print(f"RAG Filter Decision: {'✓' if rag_filter_correct else '✗'}")

        return EvaluationResult(
            query=query,
            query_type=test_case.query_type.value,
            expected_category=test_case.expected_category or "None",
            should_apply_filter=test_case.should_apply_filter,
            min_confidence=test_case.min_confidence,
            old_detected_category=old_detected or "None",
            old_confidence=old_confidence,
            old_filter_applied=old_applied,
            old_query_time_ms=old_time,
            rag_detected_category=rag_detected or "None",
            rag_confidence=rag_confidence,
            rag_filter_applied=rag_applied,
            rag_query_time_ms=rag_time,
            rag_reasoning=rag_reasoning,
            old_category_correct=old_category_correct,
            rag_category_correct=rag_category_correct,
            old_filter_decision_correct=old_filter_correct,
            rag_filter_decision_correct=rag_filter_correct,
            old_confidence_meets_threshold=old_confidence_ok,
            rag_confidence_meets_threshold=rag_confidence_ok,
        )

    def _is_category_correct(
        self,
        detected: str,
        expected: str,
        alternatives: List[str]
    ) -> bool:
        """
        Check if detected category matches expected or alternatives.

        Args:
            detected: Category detected by system
            expected: Expected category
            alternatives: Alternative acceptable categories

        Returns:
            True if match (exact or partial)
        """
        if not expected:
            # No expected category (ambiguous query)
            # We consider it "correct" if no category was detected
            return detected is None

        if not detected:
            # Expected a category but none detected
            return False

        # Exact match
        if detected == expected:
            return True

        # Check alternatives
        if detected in alternatives:
            return True

        # Partial match (case-insensitive substring)
        detected_lower = detected.lower()
        expected_lower = expected.lower()

        if expected_lower in detected_lower or detected_lower in expected_lower:
            return True

        # Check alternatives partial
        for alt in alternatives:
            alt_lower = alt.lower()
            if alt_lower in detected_lower or detected_lower in alt_lower:
                return True

        return False

    def evaluate_all(self, test_cases: List[CategoryTestCase]) -> List[EvaluationResult]:
        """
        Evaluate all test cases.

        Args:
            test_cases: List of test cases to evaluate

        Returns:
            List of evaluation results
        """
        results = []

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n\n{'#'*70}")
            print(f"# Test Case {i}/{len(test_cases)}")
            print(f"{'#'*70}")

            result = self.evaluate_test_case(test_case)
            results.append(result)

            # Small delay to avoid rate limiting
            time.sleep(0.5)

        return results

    def generate_report(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        Generate evaluation report with aggregate metrics.

        Args:
            results: List of evaluation results

        Returns:
            Report dictionary
        """
        total = len(results)

        # OLD approach metrics
        old_category_correct = sum(1 for r in results if r.old_category_correct)
        old_filter_correct = sum(1 for r in results if r.old_filter_decision_correct)
        old_confidence_ok = sum(1 for r in results if r.old_confidence_meets_threshold)
        old_avg_time = sum(r.old_query_time_ms for r in results) / total

        # RAG approach metrics
        rag_category_correct = sum(1 for r in results if r.rag_category_correct)
        rag_filter_correct = sum(1 for r in results if r.rag_filter_decision_correct)
        rag_confidence_ok = sum(1 for r in results if r.rag_confidence_meets_threshold)
        rag_avg_time = sum(r.rag_query_time_ms for r in results) / total

        report = {
            "total_test_cases": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "old_approach": {
                "category_accuracy": old_category_correct / total,
                "filter_decision_accuracy": old_filter_correct / total,
                "confidence_threshold_met": old_confidence_ok / total,
                "avg_query_time_ms": old_avg_time,
            },
            "rag_approach": {
                "category_accuracy": rag_category_correct / total,
                "filter_decision_accuracy": rag_filter_correct / total,
                "confidence_threshold_met": rag_confidence_ok / total,
                "avg_query_time_ms": rag_avg_time,
            },
            "comparison": {
                "category_accuracy_improvement": (rag_category_correct - old_category_correct) / total,
                "filter_decision_improvement": (rag_filter_correct - old_filter_correct) / total,
                "time_overhead_ms": rag_avg_time - old_avg_time,
            },
            "detailed_results": [r.to_dict() for r in results],
        }

        return report

    def print_summary(self, report: Dict[str, Any]):
        """Print summary of evaluation results."""
        print("\n\n" + "="*70)
        print("EVALUATION SUMMARY")
        print("="*70)

        total = report["total_test_cases"]
        old = report["old_approach"]
        rag = report["rag_approach"]
        comp = report["comparison"]

        print(f"\nTotal Test Cases: {total}")
        print(f"Timestamp: {report['timestamp']}")

        print(f"\n--- OLD Approach (Confidence-Based) ---")
        print(f"Category Accuracy:        {old['category_accuracy']*100:.1f}% ({int(old['category_accuracy']*total)}/{total})")
        print(f"Filter Decision Accuracy: {old['filter_decision_accuracy']*100:.1f}% ({int(old['filter_decision_accuracy']*total)}/{total})")
        print(f"Confidence Threshold Met: {old['confidence_threshold_met']*100:.1f}%")
        print(f"Avg Query Time:           {old['avg_query_time_ms']:.0f}ms")

        print(f"\n--- RAG Approach (LLM-Based) ---")
        print(f"Category Accuracy:        {rag['category_accuracy']*100:.1f}% ({int(rag['category_accuracy']*total)}/{total})")
        print(f"Filter Decision Accuracy: {rag['filter_decision_accuracy']*100:.1f}% ({int(rag['filter_decision_accuracy']*total)}/{total})")
        print(f"Confidence Threshold Met: {rag['confidence_threshold_met']*100:.1f}%")
        print(f"Avg Query Time:           {rag['avg_query_time_ms']:.0f}ms")

        print(f"\n--- Improvement (RAG vs OLD) ---")
        improvement = comp['category_accuracy_improvement'] * 100
        print(f"Category Accuracy:        {'+' if improvement >= 0 else ''}{improvement:.1f}%")

        filter_improvement = comp['filter_decision_improvement'] * 100
        print(f"Filter Decision Accuracy: {'+' if filter_improvement >= 0 else ''}{filter_improvement:.1f}%")

        print(f"Time Overhead:            +{comp['time_overhead_ms']:.0f}ms")

        print("\n" + "="*70)


def main():
    """Main evaluation function."""
    parser = argparse.ArgumentParser(description="Evaluate category classification approaches")
    parser.add_argument("--queries", type=int, default=None, help="Number of test queries to run (default: all)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--output", type=str, default="evaluation_results.json", help="Output JSON file")

    args = parser.parse_args()

    # Select test cases
    test_cases = CATEGORY_TEST_CASES
    if args.queries:
        test_cases = test_cases[:args.queries]

    print(f"Running evaluation on {len(test_cases)} test cases...")
    print(f"Debug mode: {'ON' if args.debug else 'OFF'}")

    # Run evaluation
    evaluator = CategoryClassificationEvaluator(debug=args.debug)
    results = evaluator.evaluate_all(test_cases)

    # Generate report
    report = evaluator.generate_report(results)

    # Print summary
    evaluator.print_summary(report)

    # Save to JSON
    with open(args.output, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed results saved to: {args.output}")


if __name__ == "__main__":
    main()
