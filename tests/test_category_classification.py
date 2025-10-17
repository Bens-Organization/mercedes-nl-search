"""
Pytest-based tests for category classification evaluation.

Compares:
1. Old approach: Confidence-based (division of results)
2. New approach: RAG-based (LLM with retrieved context)

Usage:
    # Run all tests
    pytest tests/test_category_classification.py -v

    # Run with detailed output
    pytest tests/test_category_classification.py -v -s

    # Run specific test types
    pytest tests/test_category_classification.py -v -k "exact_match"
    pytest tests/test_category_classification.py -v -k "generic"

    # Generate HTML report
    pytest tests/test_category_classification.py --html=report.html --self-contained-html

    # Run in parallel (faster)
    pytest tests/test_category_classification.py -v -n auto
"""

import pytest
import time
import json
from typing import Dict, Any, List, Tuple
from category_test_cases import CATEGORY_TEST_CASES, CategoryTestCase, QueryType

# Import both search implementations
from src.search import NaturalLanguageSearch as OldSearch
from src.search_rag import RAGNaturalLanguageSearch as RAGSearch


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def old_search_engine():
    """Initialize OLD search engine (confidence-based)."""
    return OldSearch()


@pytest.fixture(scope="module")
def rag_search_engine():
    """Initialize RAG search engine (LLM-based)."""
    return RAGSearch()


@pytest.fixture(scope="module")
def test_results():
    """Store test results for summary report."""
    return []


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_category_correct(
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


def evaluate_approach(
    test_case: CategoryTestCase,
    search_engine,
    approach_name: str,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Evaluate a single approach on a test case.

    Args:
        test_case: Test case to evaluate
        search_engine: Search engine instance
        approach_name: Name of approach ("old" or "rag")
        debug: Enable debug output

    Returns:
        Dictionary with evaluation metrics
    """
    start_time = time.time()

    # Execute search
    response = search_engine.search(
        test_case.query,
        max_results=20,
        debug=debug
    )

    query_time = (time.time() - start_time) * 1000

    # Extract metrics
    detected_category = response.detected_category
    confidence = response.category_confidence or 0.0
    filter_applied = response.category_applied or False

    # Get reasoning for RAG approach
    reasoning = ""
    if approach_name == "rag" and hasattr(response, 'typesense_query'):
        reasoning = response.typesense_query.get("llm_reasoning", "")

    # Evaluate correctness
    category_correct = is_category_correct(
        detected_category,
        test_case.expected_category,
        test_case.alternative_categories
    )

    filter_decision_correct = (filter_applied == test_case.should_apply_filter)

    confidence_meets_threshold = (
        confidence >= test_case.min_confidence
        if test_case.should_apply_filter
        else True
    )

    return {
        "detected_category": detected_category,
        "confidence": confidence,
        "filter_applied": filter_applied,
        "query_time_ms": query_time,
        "reasoning": reasoning,
        "category_correct": category_correct,
        "filter_decision_correct": filter_decision_correct,
        "confidence_meets_threshold": confidence_meets_threshold,
    }


# ============================================================================
# PARAMETRIZED TESTS
# ============================================================================

@pytest.mark.parametrize("test_case", CATEGORY_TEST_CASES, ids=lambda tc: tc.query)
def test_old_approach_category_detection(test_case, old_search_engine):
    """Test OLD approach (confidence-based) category detection."""
    result = evaluate_approach(test_case, old_search_engine, "old", debug=False)

    # Assert category detection is correct
    assert result["category_correct"], (
        f"OLD approach detected wrong category for '{test_case.query}'\n"
        f"  Expected: {test_case.expected_category}\n"
        f"  Detected: {result['detected_category']}\n"
        f"  Confidence: {result['confidence']:.2f}\n"
        f"  Notes: {test_case.notes}"
    )


@pytest.mark.parametrize("test_case", CATEGORY_TEST_CASES, ids=lambda tc: tc.query)
def test_rag_approach_category_detection(test_case, rag_search_engine):
    """Test RAG approach (LLM-based) category detection."""
    result = evaluate_approach(test_case, rag_search_engine, "rag", debug=False)

    # Assert category detection is correct
    assert result["category_correct"], (
        f"RAG approach detected wrong category for '{test_case.query}'\n"
        f"  Expected: {test_case.expected_category}\n"
        f"  Detected: {result['detected_category']}\n"
        f"  Confidence: {result['confidence']:.2f}\n"
        f"  Reasoning: {result['reasoning'][:200]}...\n"
        f"  Notes: {test_case.notes}"
    )


@pytest.mark.parametrize("test_case", CATEGORY_TEST_CASES, ids=lambda tc: tc.query)
def test_old_approach_filter_decision(test_case, old_search_engine):
    """Test OLD approach filter application decision."""
    result = evaluate_approach(test_case, old_search_engine, "old", debug=False)

    # Assert filter decision is correct
    assert result["filter_decision_correct"], (
        f"OLD approach made wrong filter decision for '{test_case.query}'\n"
        f"  Should apply filter: {test_case.should_apply_filter}\n"
        f"  Actually applied: {result['filter_applied']}\n"
        f"  Confidence: {result['confidence']:.2f}\n"
        f"  Notes: {test_case.notes}"
    )


@pytest.mark.parametrize("test_case", CATEGORY_TEST_CASES, ids=lambda tc: tc.query)
def test_rag_approach_filter_decision(test_case, rag_search_engine):
    """Test RAG approach filter application decision."""
    result = evaluate_approach(test_case, rag_search_engine, "rag", debug=False)

    # Assert filter decision is correct
    assert result["filter_decision_correct"], (
        f"RAG approach made wrong filter decision for '{test_case.query}'\n"
        f"  Should apply filter: {test_case.should_apply_filter}\n"
        f"  Actually applied: {result['filter_applied']}\n"
        f"  Confidence: {result['confidence']:.2f}\n"
        f"  Reasoning: {result['reasoning'][:200]}...\n"
        f"  Notes: {test_case.notes}"
    )


@pytest.mark.parametrize("test_case", CATEGORY_TEST_CASES, ids=lambda tc: tc.query)
def test_comparison_category_accuracy(test_case, old_search_engine, rag_search_engine):
    """Compare OLD vs RAG category detection accuracy."""
    old_result = evaluate_approach(test_case, old_search_engine, "old", debug=False)
    rag_result = evaluate_approach(test_case, rag_search_engine, "rag", debug=False)

    # If OLD is wrong and RAG is right, this is an improvement
    # If both are right, no regression
    # If OLD is right and RAG is wrong, this is a regression

    if not old_result["category_correct"] and rag_result["category_correct"]:
        # Improvement - RAG fixed a case that OLD got wrong
        pytest.skip(f"RAG improved on OLD for '{test_case.query}'")

    elif old_result["category_correct"] and not rag_result["category_correct"]:
        # Regression - RAG broke a case that OLD got right
        pytest.fail(
            f"RAG regression: OLD was correct but RAG failed for '{test_case.query}'\n"
            f"  Expected: {test_case.expected_category}\n"
            f"  OLD detected: {old_result['detected_category']} ✓\n"
            f"  RAG detected: {rag_result['detected_category']} ✗\n"
            f"  RAG reasoning: {rag_result['reasoning'][:200]}..."
        )


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.parametrize("test_case", CATEGORY_TEST_CASES, ids=lambda tc: tc.query)
def test_rag_performance_acceptable(test_case, rag_search_engine):
    """Ensure RAG approach performance is acceptable (< 5s per query)."""
    result = evaluate_approach(test_case, rag_search_engine, "rag", debug=False)

    max_acceptable_time = 5000  # 5 seconds

    assert result["query_time_ms"] < max_acceptable_time, (
        f"RAG approach too slow for '{test_case.query}'\n"
        f"  Query time: {result['query_time_ms']:.0f}ms\n"
        f"  Max acceptable: {max_acceptable_time}ms"
    )


# ============================================================================
# CONFTEST HOOKS FOR SUMMARY REPORTING
# ============================================================================

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Generate summary report after all tests complete."""

    # Collect statistics from test results
    passed = len(terminalreporter.stats.get('passed', []))
    failed = len(terminalreporter.stats.get('failed', []))
    skipped = len(terminalreporter.stats.get('skipped', []))
    total = passed + failed + skipped

    terminalreporter.write_sep("=", "Category Classification Evaluation Summary")
    terminalreporter.write_line(f"\nTotal Test Cases: {len(CATEGORY_TEST_CASES)}")
    terminalreporter.write_line(f"Total Assertions: {total}")
    terminalreporter.write_line(f"  Passed: {passed}")
    terminalreporter.write_line(f"  Failed: {failed}")
    terminalreporter.write_line(f"  Skipped (Improvements): {skipped}")

    if failed > 0:
        terminalreporter.write_line(f"\n⚠️  {failed} tests failed - review regression details above")

    if skipped > 0:
        terminalreporter.write_line(f"\n✨ {skipped} tests show RAG improvements over OLD approach")

    terminalreporter.write_sep("=", "End of Summary")


# ============================================================================
# BENCHMARK TESTS (Optional - run with -m benchmark)
# ============================================================================

@pytest.mark.benchmark
@pytest.mark.parametrize("test_case", CATEGORY_TEST_CASES[:5], ids=lambda tc: tc.query)
def test_benchmark_old_vs_rag(test_case, old_search_engine, rag_search_engine, benchmark):
    """Benchmark comparison of OLD vs RAG approaches."""

    def run_both_searches():
        old_result = evaluate_approach(test_case, old_search_engine, "old", debug=False)
        rag_result = evaluate_approach(test_case, rag_search_engine, "rag", debug=False)
        return old_result, rag_result

    old_result, rag_result = benchmark(run_both_searches)

    # Print comparison
    print(f"\n'{test_case.query}':")
    print(f"  OLD: {old_result['query_time_ms']:.0f}ms, Category: {old_result['detected_category']}")
    print(f"  RAG: {rag_result['query_time_ms']:.0f}ms, Category: {rag_result['detected_category']}")
