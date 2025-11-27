#!/usr/bin/env python3
"""
Test script for JAI-2210: Dynamic Negation Handling

Tests that searching for positive terms excludes their negated variants.
Uses dynamic prefix detection instead of static mappings.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.openai_middleware import apply_negation_filters, SAFE_NEGATION_PREFIXES, SHORT_PREFIX_MIN_TERM_LENGTH


def test_negation_filter_function():
    """Test the dynamic apply_negation_filters function"""
    print("=" * 60)
    print("Testing Dynamic Negation Filter")
    print("=" * 60)

    test_cases = [
        # (query, existing_filter, should_contain, should_not_contain)
        # Sterile - the main JAI-2210 case
        ("sterile gloves", "", ["non-sterile", "nonsterile"], None),
        ("sterile nitrile gloves", "price:<50", ["non-sterile"], None),
        ("non-sterile gloves", "", None, ["non-sterile"]),  # User wants non-sterile

        # Dynamic cases - NOT in any static list
        ("labeled tubes", "", ["unlabeled"], None),  # un- prefix
        ("coated slides", "", ["non-coated"], None),  # coated is 6 chars
        ("filtered water", "", ["non-filtered", "unfiltered"], None),

        # Anti- prefix
        ("microbial solution", "", ["anti-microbial", "antimicrobial"], None),

        # Short words should NOT have negation applied (5+ char minimum)
        ("red tubes", "", None, ["nonred"]),  # "red" is 3 chars - too short
        ("box of items", "", None, ["nonbox"]),  # "box" is 3 chars - too short
        ("slip mat", "", None, ["nonslip"]),  # "slip" is 4 chars - too short

        # Complex queries
        ("sterile labeled pipettes", "", ["non-sterile", "unlabeled"], None),
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        query, existing_filter, should_contain, should_not_contain = test
        result = apply_negation_filters(query, existing_filter)

        test_passed = True
        errors = []

        # Check should_contain
        if should_contain:
            for term in should_contain:
                if f"name:!*{term}*" not in result:
                    test_passed = False
                    errors.append(f"Missing exclusion for '{term}'")

        # Check should_not_contain
        if should_not_contain:
            for term in should_not_contain:
                if f"name:!*{term}*" in result:
                    test_passed = False
                    errors.append(f"Should NOT exclude '{term}'")

        if test_passed:
            print(f"✅ PASS: '{query}'")
            passed += 1
        else:
            print(f"❌ FAIL: '{query}'")
            for err in errors:
                print(f"   {err}")
            print(f"   Result: {result[:100]}...")
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

    query = "sterile nitrile gloves"
    existing_filter = "categories:=`Products / Gloves & Apparel / Gloves`"

    result = apply_negation_filters(query, existing_filter)

    print(f"Query: {query}")
    print(f"Existing filter: {existing_filter}")
    print()
    print(f"Result filter:")
    # Pretty print the filter
    parts = result.split(" && ")
    for part in parts[:5]:  # Show first 5 parts
        print(f"  {part}")
    if len(parts) > 5:
        print(f"  ... and {len(parts) - 5} more")
    print()

    # Check that non-sterile variants are excluded
    required = ["non-sterile", "nonsterile"]
    all_found = all(f"name:!*{r}*" in result for r in required)

    if all_found:
        print("✅ PASS: Non-sterile products will be excluded")
        return True
    else:
        print("❌ FAIL: Missing required negation filters")
        return False


def test_dynamic_unlisted_terms():
    """Test that terms NOT in any static list are still handled"""
    print()
    print("=" * 60)
    print("Testing Dynamic Detection (unlisted terms)")
    print("=" * 60)

    # These terms would NOT be in a static list
    # All attribute words are 5+ chars and not in skip_words
    unlisted_terms = [
        ("absorbent material", "non-absorbent"),   # absorbent = 9 chars
        ("conductive wire", "non-conductive"),      # conductive = 10 chars
        ("reactive compound", "non-reactive"),      # reactive = 8 chars
        ("magnetic material", "non-magnetic"),      # magnetic = 8 chars
        ("adhesive material", "non-adhesive"),      # adhesive = 8 chars
        ("porous filter", "non-porous"),            # porous = 6 chars
    ]

    passed = 0
    for query, expected_exclusion in unlisted_terms:
        result = apply_negation_filters(query, "")
        if f"name:!*{expected_exclusion}*" in result:
            print(f"✅ '{query}' → excludes '{expected_exclusion}'")
            passed += 1
        else:
            print(f"❌ '{query}' → missing '{expected_exclusion}'")
            print(f"   Result: {result[:80]}...")

    print()
    print(f"Dynamic detection: {passed}/{len(unlisted_terms)} terms handled")
    return passed == len(unlisted_terms)


def test_reverse_negation():
    """Test that searching for negated terms excludes positive variants"""
    print()
    print("=" * 60)
    print("Testing Reverse Negation (negated → excludes positive)")
    print("=" * 60)

    test_cases = [
        # (query, should_exclude_positive_pattern)
        ("non-sterile gloves", ", Sterile "),      # Should exclude standalone "Sterile"
        ("nonsterile gloves", ", Sterile "),       # Should exclude standalone "Sterile"
        ("non sterile gloves", ", Sterile "),      # Should exclude standalone "Sterile"
        ("anti-microbial wipes", ", Microbial "),  # Should exclude standalone "Microbial"
    ]

    passed = 0
    for query, expected_pattern in test_cases:
        result = apply_negation_filters(query, "")
        if f"name:!*{expected_pattern}*" in result:
            print(f"✅ '{query}' → excludes positive form")
            passed += 1
        else:
            print(f"❌ '{query}' → missing positive exclusion")
            print(f"   Expected pattern: {expected_pattern}")
            # Show what we got
            sterile_filters = [f for f in result.split(" && ") if "Sterile" in f or "Microbial" in f]
            print(f"   Got: {sterile_filters}")

    print()
    print(f"Reverse negation: {passed}/{len(test_cases)} cases handled")
    return passed == len(test_cases)


if __name__ == "__main__":
    print("JAI-2210: Dynamic Negation Handling Test Suite")
    print()

    all_passed = True
    all_passed &= test_prefix_configuration()
    all_passed &= test_negation_filter_function()
    all_passed &= test_sterile_example()
    all_passed &= test_dynamic_unlisted_terms()
    all_passed &= test_reverse_negation()

    print()
    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)
