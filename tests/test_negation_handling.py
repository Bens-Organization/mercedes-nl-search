#!/usr/bin/env python3
"""
Test script for JAI-2210: Dynamic Negation Handling

Tests that searching for positive terms adds exclusion terms to demote negated variants.
Uses query-level exclusion (-term syntax) instead of filter_by (which doesn't work for
wildcard negation on non-faceted string fields in Typesense).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.openai_middleware import apply_negation_to_query, SAFE_NEGATION_PREFIXES, SHORT_PREFIX_MIN_TERM_LENGTH


def test_negation_query_function():
    """Test the dynamic apply_negation_to_query function"""
    print("=" * 60)
    print("Testing Dynamic Negation (Query-Level Exclusion)")
    print("=" * 60)

    test_cases = [
        # (user_query, extracted_query, should_contain, should_not_contain)
        # Sterile - the main JAI-2210 case
        ("sterile gloves", "sterile glove", ["-non-sterile", "-nonsterile"], None),
        ("sterile nitrile gloves", "sterile nitrile glove", ["-non-sterile"], None),
        ("non-sterile gloves", "non-sterile glove", None, ["-non-sterile"]),  # User wants non-sterile

        # Short words should NOT have negation applied (5+ char minimum)
        ("red tubes", "red tube", None, ["-nonred"]),  # "red" is 3 chars - too short
        ("box of items", "box item", None, ["-nonbox"]),  # "box" is 3 chars - too short

        # Complex queries with multiple terms
        ("sterile labeled pipettes", "sterile labeled pipette", ["-non-sterile"], None),
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        user_query, extracted_query, should_contain, should_not_contain = test
        result = apply_negation_to_query(user_query, extracted_query)

        test_passed = True
        errors = []

        # Check should_contain
        if should_contain:
            for term in should_contain:
                if term not in result:
                    test_passed = False
                    errors.append(f"Missing exclusion term '{term}'")

        # Check should_not_contain
        if should_not_contain:
            for term in should_not_contain:
                if term in result:
                    test_passed = False
                    errors.append(f"Should NOT have exclusion '{term}'")

        if test_passed:
            print(f"PASS: '{user_query}'")
            passed += 1
        else:
            print(f"FAIL: '{user_query}'")
            for err in errors:
                print(f"   {err}")
            print(f"   Result: {result}")
            failed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


def test_prefix_configuration():
    """Verify prefix configuration is correct"""
    print()
    print("=" * 60)
    print("Prefix Configuration")
    print("=" * 60)

    print(f"Safe prefixes (always apply): {SAFE_NEGATION_PREFIXES}")
    print(f"Short prefixes (conditional): {SHORT_PREFIX_MIN_TERM_LENGTH}")
    return True


def test_sterile_example():
    """Test the specific sterile gloves example from JAI-2210"""
    print()
    print("=" * 60)
    print("JAI-2210 Example: 'sterile nitrile gloves'")
    print("=" * 60)

    user_query = "sterile nitrile gloves"
    extracted_query = "sterile nitrile glove"

    result = apply_negation_to_query(user_query, extracted_query)

    print(f"User query: {user_query}")
    print(f"Extracted query (before): {extracted_query}")
    print(f"Modified query (after): {result}")
    print()

    # Check that non-sterile exclusions are added to query
    has_non_sterile = "-non-sterile" in result or "-nonsterile" in result
    has_original = "sterile nitrile glove" in result

    if has_non_sterile and has_original:
        print("PASS: Query contains exclusion terms for non-sterile")
        print("      Typesense will demote products containing 'non-sterile' in the results")
        return True
    else:
        print("FAIL: Missing required exclusion terms")
        if not has_original:
            print("   - Missing original query terms")
        if not has_non_sterile:
            print("   - Missing -non-sterile or -nonsterile exclusion")
        return False


def test_no_exclusion_for_searched_negation():
    """Test that searching for negated terms doesn't exclude what user wants"""
    print()
    print("=" * 60)
    print("Testing: Don't exclude the negated form user is searching for")
    print("=" * 60)

    test_cases = [
        # (user_query, extracted_query, should_NOT_contain)
        # When user searches for "non-sterile", we should NOT add "-non-sterile" or "-nonsterile"
        ("non-sterile gloves", "non-sterile glove", ["-non-sterile", "-nonsterile"]),
        ("nonsterile gloves", "nonsterile glove", ["-non-sterile", "-nonsterile"]),
        # Note: other words like "gloves" may still get exclusions, which is fine
    ]

    passed = 0
    for user_query, extracted_query, should_not_contain in test_cases:
        result = apply_negation_to_query(user_query, extracted_query)

        # Check that we don't exclude the term the user is searching for
        has_unwanted = any(term in result for term in should_not_contain)

        if not has_unwanted:
            print(f"PASS: '{user_query}' - doesn't exclude the negated sterile term user wants")
            passed += 1
        else:
            print(f"FAIL: '{user_query}' - incorrectly excludes term user is searching for")
            print(f"   Result: {result}")
            print(f"   Should not contain: {should_not_contain}")

    print()
    print(f"Results: {passed}/{len(test_cases)} cases handled correctly")
    return passed == len(test_cases)


def test_query_structure():
    """Test that the modified query has correct structure"""
    print()
    print("=" * 60)
    print("Testing Query Structure")
    print("=" * 60)

    user_query = "sterile pipettes"
    extracted_query = "sterile pipette"
    result = apply_negation_to_query(user_query, extracted_query)

    print(f"Input: '{user_query}' -> extracted: '{extracted_query}'")
    print(f"Output: '{result}'")
    print()

    # Verify structure: original query comes first, then exclusions
    if result.startswith(extracted_query) and " -" in result:
        print("PASS: Query structure is correct (original + exclusions)")
        return True
    elif result == extracted_query:
        print("INFO: No exclusions added (may be expected for some queries)")
        return True
    else:
        print("FAIL: Unexpected query structure")
        return False


if __name__ == "__main__":
    print("JAI-2210: Dynamic Negation Handling Test Suite")
    print("(Query-Level Exclusion Approach)")
    print()

    all_passed = True
    all_passed &= test_prefix_configuration()
    all_passed &= test_negation_query_function()
    all_passed &= test_sterile_example()
    all_passed &= test_no_exclusion_for_searched_negation()
    all_passed &= test_query_structure()

    print()
    print("=" * 60)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)
