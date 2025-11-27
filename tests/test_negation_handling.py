#!/usr/bin/env python3
"""
Test script for JAI-2210: Targeted Negation Handling

Tests that searching for attribute terms adds exclusion terms to demote negated variants.
Uses a TARGETED approach - only applies to attribute words that commonly have negated
variants in product catalogs (sterile, latex, powdered, coated, etc.)

NOT applied to product type words (gloves, slides, pipettes).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.openai_middleware import apply_negation_to_query


def test_sterile_negation():
    """Test the main JAI-2210 case: sterile should exclude non-sterile"""
    print("=" * 60)
    print("Testing: sterile → excludes non-sterile")
    print("=" * 60)

    test_cases = [
        # (user_query, extracted_query, should_contain)
        ("sterile gloves", "sterile glove", ["-non-sterile", "-nonsterile"]),
        ("sterile nitrile gloves", "sterile nitrile glove", ["-non-sterile", "-nonsterile"]),
        ("sterile pipette tips", "sterile pipette tip", ["-non-sterile", "-nonsterile"]),
    ]

    passed = 0
    for user_query, extracted_query, should_contain in test_cases:
        result = apply_negation_to_query(user_query, extracted_query)
        all_found = all(term in result for term in should_contain)
        if all_found:
            print(f"PASS: '{user_query}'")
            print(f"      Result: {result}")
            passed += 1
        else:
            print(f"FAIL: '{user_query}'")
            print(f"      Expected: {should_contain}")
            print(f"      Got: {result}")

    print(f"\nResults: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_no_exclusion_for_product_types():
    """Test that product type words don't get exclusions"""
    print()
    print("=" * 60)
    print("Testing: Product types should NOT get exclusions")
    print("=" * 60)

    test_cases = [
        # These should NOT have any exclusions added
        ("blue gloves", "blue glove"),
        ("microscope slides", "microscope slide"),
        ("pipette tips", "pipette tip"),
        ("test tubes", "test tube"),
    ]

    passed = 0
    for user_query, extracted_query in test_cases:
        result = apply_negation_to_query(user_query, extracted_query)
        # Result should be unchanged (no exclusions added)
        if result == extracted_query:
            print(f"PASS: '{user_query}' - no exclusions added")
            passed += 1
        else:
            print(f"FAIL: '{user_query}' - unexpected exclusions")
            print(f"      Got: {result}")

    print(f"\nResults: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_other_attribute_words():
    """Test other attribute words that should have exclusions"""
    print()
    print("=" * 60)
    print("Testing: Other attribute words with negations")
    print("=" * 60)

    test_cases = [
        # (user_query, extracted_query, should_contain)
        ("latex gloves", "latex glove", ["-non-latex", "-latex-free"]),
        ("coated slides", "coated slide", ["-non-coated", "-uncoated"]),
        ("filtered pipette tips", "filtered pipette tip", ["-non-filtered", "-unfiltered"]),
    ]

    passed = 0
    for user_query, extracted_query, should_contain in test_cases:
        result = apply_negation_to_query(user_query, extracted_query)
        all_found = all(term in result for term in should_contain)
        if all_found:
            print(f"PASS: '{user_query}'")
            print(f"      Result: {result}")
            passed += 1
        else:
            print(f"FAIL: '{user_query}'")
            print(f"      Expected: {should_contain}")
            print(f"      Got: {result}")

    print(f"\nResults: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_no_exclusion_when_searching_negated():
    """Test that searching for negated terms doesn't add contradictory exclusions"""
    print()
    print("=" * 60)
    print("Testing: No exclusion when user wants negated form")
    print("=" * 60)

    test_cases = [
        # User wants non-sterile, should NOT add -non-sterile exclusion
        ("non-sterile gloves", "non-sterile glove", ["-non-sterile", "-nonsterile"]),
        ("nonsterile gloves", "nonsterile glove", ["-non-sterile", "-nonsterile"]),
        ("latex-free gloves", "latex-free glove", ["-latex-free", "-latexfree"]),
        ("powder-free gloves", "powder-free glove", ["-powder-free", "-powderfree"]),
    ]

    passed = 0
    for user_query, extracted_query, should_not_contain in test_cases:
        result = apply_negation_to_query(user_query, extracted_query)
        # Should NOT contain these exclusions
        has_unwanted = any(term in result for term in should_not_contain)
        if not has_unwanted:
            print(f"PASS: '{user_query}' - no contradictory exclusions")
            passed += 1
        else:
            print(f"FAIL: '{user_query}' - has contradictory exclusions")
            print(f"      Result: {result}")

    print(f"\nResults: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_query_cleanliness():
    """Test that queries are clean and minimal"""
    print()
    print("=" * 60)
    print("Testing: Query cleanliness (no verbose exclusions)")
    print("=" * 60)

    # "powdered gloves" should only have powder-related exclusions, not gloves exclusions
    user_query = "powdered gloves"
    extracted_query = "powdered glove"
    result = apply_negation_to_query(user_query, extracted_query)

    # Should have powder exclusions
    has_powder_exclusions = "-powder-free" in result

    # Should NOT have gloves exclusions
    has_gloves_exclusions = "-nongloves" in result or "-anti-gloves" in result

    if has_powder_exclusions and not has_gloves_exclusions:
        print(f"PASS: '{user_query}'")
        print(f"      Clean result: {result}")
        return True
    else:
        print(f"FAIL: '{user_query}'")
        print(f"      Result: {result}")
        if not has_powder_exclusions:
            print("      Missing powder exclusions")
        if has_gloves_exclusions:
            print("      Has unwanted gloves exclusions")
        return False


if __name__ == "__main__":
    print("JAI-2210: Targeted Negation Handling Test Suite")
    print("(Only attribute words, NOT product types)")
    print()

    all_passed = True
    all_passed &= test_sterile_negation()
    all_passed &= test_no_exclusion_for_product_types()
    all_passed &= test_other_attribute_words()
    all_passed &= test_no_exclusion_when_searching_negated()
    all_passed &= test_query_cleanliness()

    print()
    print("=" * 60)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)
