# Category Classification Tests

Pytest-based evaluation framework for comparing category classification approaches.

## Overview

This test suite compares two approaches to category classification:

1. **OLD Approach** (Confidence-based): Uses result distribution (matching_count / total_results)
2. **RAG Approach** (LLM-based): Uses LLM with retrieved context to classify categories

## Test Structure

### Test Files

- `category_test_cases.py` - 26 test cases covering diverse query types
- `test_category_classification.py` - Pytest tests for evaluation
- `pytest.ini` - Pytest configuration

### Test Categories

1. **Category Detection Tests**
   - `test_old_approach_category_detection` - OLD approach accuracy
   - `test_rag_approach_category_detection` - RAG approach accuracy

2. **Filter Decision Tests**
   - `test_old_approach_filter_decision` - OLD filter application logic
   - `test_rag_approach_filter_decision` - RAG filter application logic

3. **Comparison Tests**
   - `test_comparison_category_accuracy` - Detect regressions/improvements

4. **Performance Tests**
   - `test_rag_performance_acceptable` - Ensure RAG stays under 5s/query

5. **Benchmark Tests** (optional)
   - `test_benchmark_old_vs_rag` - Detailed performance comparison

## Running Tests

### Basic Usage

```bash
# Run all tests
pytest tests/test_category_classification.py -v

# Run with detailed output (shows search responses)
pytest tests/test_category_classification.py -v -s

# Run with pytest-html report
pytest tests/test_category_classification.py --html=report.html --self-contained-html
```

### Filter by Test Type

```bash
# Run only exact match tests
pytest tests/test_category_classification.py -v -k "exact_match"

# Run only generic query tests
pytest tests/test_category_classification.py -v -k "generic"

# Run only ambiguous query tests
pytest tests/test_category_classification.py -v -k "ambiguous"

# Run only OLD approach tests
pytest tests/test_category_classification.py -v -k "old_approach"

# Run only RAG approach tests
pytest tests/test_category_classification.py -v -k "rag_approach"

# Run only comparison tests
pytest tests/test_category_classification.py -v -k "comparison"
```

### Run Specific Queries

```bash
# Run tests for specific query
pytest tests/test_category_classification.py -v -k "nitrile gloves"

# Run tests for Ansell gloves
pytest tests/test_category_classification.py -v -k "Ansell"
```

### Performance & Parallel Execution

```bash
# Run tests in parallel (faster, requires pytest-xdist)
pytest tests/test_category_classification.py -v -n auto

# Run benchmark tests only
pytest tests/test_category_classification.py -v -m benchmark

# Skip benchmark tests
pytest tests/test_category_classification.py -v -m "not benchmark"
```

### Quick Tests (First 5 Cases)

```bash
# Quick validation - run first test only
pytest tests/test_category_classification.py -v --maxfail=1

# Run first 5 test cases only
pytest tests/test_category_classification.py -v -k "Ansell or nitrile or pipettes or microscope or lab"
```

## Understanding Test Results

### Test Output Format

Each test shows:
- **Query**: The search query being tested
- **Expected**: Expected category (or "None" for ambiguous)
- **Detected**: Category detected by the system
- **Confidence**: Confidence score (0.0-1.0)
- **Filter Applied**: Whether category filter was applied
- **Reasoning** (RAG only): LLM's explanation

### Success Criteria

A test **PASSES** if:
- Detected category matches expected (or acceptable alternatives)
- Filter decision matches expected (apply vs. don't apply)
- Confidence meets minimum threshold (if filter should be applied)

A test **FAILS** if:
- Wrong category detected
- Wrong filter decision (applied when shouldn't, or vice versa)
- Confidence too low for queries that should be confident

A test is **SKIPPED** if:
- RAG improved over OLD (shows progress)

### Example Output

```
PASSED  test_rag_approach_category_detection[nitrile gloves]
  RAG correctly detected "Gloves" with confidence 0.92

FAILED  test_old_approach_category_detection[Ansell]
  OLD detected "Gloves" but should be None (ambiguous brand query)

SKIPPED test_comparison_category_accuracy[filters]
  RAG improved on OLD (correctly detected ambiguity)
```

## Summary Report

After all tests complete, a summary is shown:

```
==================== Category Classification Evaluation Summary ====================

Total Test Cases: 26
Total Assertions: 130
  Passed: 115
  Failed: 5
  Skipped (Improvements): 10

⚠️  5 tests failed - review regression details above
✨ 10 tests show RAG improvements over OLD approach

==================== End of Summary ====================
```

## Interpreting Results

### Accuracy Metrics

**Category Detection Accuracy** = (Correct Detections) / (Total Test Cases)
- Measures how often the system detects the right category

**Filter Decision Accuracy** = (Correct Decisions) / (Total Test Cases)
- Measures how often the system correctly decides to apply/skip filter

### Performance Metrics

**Query Time** = Time from request to response
- OLD: ~100-200ms (1 LLM call to Typesense NL)
- RAG: ~300-500ms (2 LLM calls: retrieval + classification)
- Acceptable: < 5000ms

### Comparison

**Improvements (Skipped Tests)**: Cases where RAG is better than OLD
**Regressions (Failed Tests)**: Cases where RAG is worse than OLD
**No Change (Passed Tests)**: Cases where both are correct

## Test Case Breakdown

### Exact Match (1 test)
- `"Ansell gloves ANS 5789911"` - Should find exact product

### Generic (7 tests)
- `"nitrile gloves"`, `"pipettes"`, `"microscope slides"`, etc.
- Should detect category with high confidence

### Specific (6 tests)
- `"blue nitrile gloves size medium"`
- `"sterile surgical gloves"`
- Should detect category with attributes

### Brand (3 tests)
- `"Mercedes Scientific"` - Too broad, shouldn't filter
- `"Ansell"` - Brand only, shouldn't filter
- `"Thermo Fisher pipettes"` - Brand + type, should filter

### Ambiguous (7 tests)
- `"filters"`, `"tubes"`, `"containers"`
- Should NOT apply filter (low confidence)

### Multi-Category (2 tests)
- `"safety goggles"`, `"autoclave sterilization bags"`
- Could be in multiple categories, should still detect primary

## Generating Reports

### HTML Report (Recommended)

```bash
# Generate HTML report
pytest tests/test_category_classification.py --html=report.html --self-contained-html

# Open in browser
open report.html  # macOS
xdg-open report.html  # Linux
start report.html  # Windows
```

### JSON Report

```bash
# Generate JSON report
pytest tests/test_category_classification.py --json-report --json-report-file=report.json

# Or use pytest-json-report plugin
pip install pytest-json-report
pytest tests/test_category_classification.py --json-report
```

### JUnit XML (for CI/CD)

```bash
# Generate JUnit XML (for Jenkins, GitLab CI, etc.)
pytest tests/test_category_classification.py --junitxml=junit.xml
```

## Debugging Failed Tests

```bash
# Show full output for failed tests
pytest tests/test_category_classification.py -v -s --tb=long

# Drop into debugger on failure
pytest tests/test_category_classification.py -v --pdb

# Show local variables in traceback
pytest tests/test_category_classification.py -v -l

# Stop on first failure
pytest tests/test_category_classification.py -v -x
```

## Requirements

```bash
# Install pytest
pip install pytest

# Optional: Install plugins for better reporting
pip install pytest-html pytest-xdist pytest-benchmark pytest-json-report

# Run tests
pytest tests/test_category_classification.py -v
```

## Adding New Test Cases

To add new test cases:

1. Edit `tests/category_test_cases.py`
2. Add new `CategoryTestCase` to `CATEGORY_TEST_CASES` list
3. Run tests to validate

Example:
```python
CategoryTestCase(
    query="your new query",
    query_type=QueryType.GENERIC,
    expected_category="Expected Category",
    should_apply_filter=True,
    min_confidence=0.7,
    notes="Why this test case is important",
    alternative_categories=["Alt Category 1", "Alt Category 2"]
)
```

## CI/CD Integration

```yaml
# Example GitHub Actions workflow
- name: Run category classification tests
  run: |
    pytest tests/test_category_classification.py -v --junitxml=junit.xml

- name: Upload test results
  uses: actions/upload-artifact@v2
  with:
    name: test-results
    path: junit.xml
```

---

**Last Updated**: 2025-10-17
**Branch**: `feature/rag-category-classification`
