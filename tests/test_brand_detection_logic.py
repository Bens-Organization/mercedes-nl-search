#!/usr/bin/env python3
"""Unit tests for brand detection and priority logic.

Tests the helper methods without requiring a full re-index.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indexer_neon import NeonProductIndexer


def test_category_detection():
    """Test category type detection."""
    print("=" * 80)
    print("CATEGORY TYPE DETECTION TEST")
    print("=" * 80)
    print()

    indexer = NeonProductIndexer()

    test_cases = [
        {
            "categories": ["Products/Chemicals & Stains/Methanol", "Brand: VWR", "Grade: HPLC", "Size: 4 Liter"],
            "expected": "lcms_hplc",
            "name": "HPLC Grade Chemical"
        },
        {
            "categories": ["Products/Chemicals & Stains/Water", "Brand: Birch Biotech", "Grade: LCMS"],
            "expected": "lcms_hplc",
            "name": "LCMS Grade Chemical"
        },
        {
            "categories": ["Products/Chemicals & Stains/Acetonitrile", "Brand: Concord Technology", "Grade: Ultra HPLC"],
            "expected": "lcms_hplc",
            "name": "Ultra HPLC Grade Chemical"
        },
        {
            "categories": ["Products/Drug Tests/Saliva", "Brand: Wondfo"],
            "expected": "drug_testing",
            "name": "Drug Test Product"
        },
        {
            "categories": ["Products/Drug Tests/Urine", "Brand: AllTest"],
            "expected": "drug_testing",
            "name": "Drug Test Urine"
        },
        {
            "categories": ["Products/Gloves/Nitrile", "Brand: Mercedes Scientific"],
            "expected": "general",
            "name": "General Category - Gloves"
        },
        {
            "categories": ["Products/Lab Equipment/Microscope Slides", "Brand: Tanner Scientific"],
            "expected": "general",
            "name": "General Category - Lab Equipment"
        },
        {
            "categories": [],
            "expected": "general",
            "name": "No Categories"
        },
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        result = indexer._detect_category_type(test["categories"])
        status = "✅ PASS" if result == test["expected"] else "❌ FAIL"

        print(f"{status} | {test['name']}")
        print(f"     Categories: {test['categories']}")
        print(f"     Expected: {test['expected']}, Got: {result}")
        print()

        if result == test["expected"]:
            passed += 1
        else:
            failed += 1

    print(f"Results: {passed} passed, {failed} failed\n")
    return failed == 0


def test_brand_detection():
    """Test brand detection from SKU, brand field, and product name."""
    print("=" * 80)
    print("BRAND DETECTION TEST")
    print("=" * 80)
    print()

    indexer = NeonProductIndexer()

    test_cases = [
        # SKU prefix detection
        {
            "sku": "TBK 8003LC4000",
            "brand": "Concord Technology",
            "name": "Concord Water, HPLC Grade",
            "expected": "concord technologies",
            "description": "Concord (TBK prefix)"
        },
        {
            "sku": "BIR 19395",
            "brand": "Birch Biotech",
            "name": "Birch® Biotech PRISTINE® Water, LC-MS Grade",
            "expected": "birch biotech",
            "description": "Birch Biotech (BIR prefix)"
        },
        {
            "sku": "MER MMDOAY6125",
            "brand": "Mercedes Scientific",
            "name": "Mercedes Scientific® Platinum+ 12-Panel Drug Test Cup",
            "expected": "mercedes scientific",
            "description": "Mercedes (MER prefix)"
        },
        {
            "sku": "ALT DOAA1137C",
            "brand": None,
            "name": "AllTest® Multi-Drug Rapid Test Cup",
            "expected": "alltest",
            "description": "AllTest (ALT prefix, no brand field)"
        },
        {
            "sku": "TNR MMC12MOP",
            "brand": "Tanner Scientific",
            "name": "Tanner Scientific® BluRapids® Multi-Drug Test Cup",
            "expected": "tanner scientific",
            "description": "Tanner (TNR prefix)"
        },
        {
            "sku": "HGS HDCL114",
            "brand": "Healgen Scientific",
            "name": "Healgen® Single Drug Test Dip Card",
            "expected": "healgen",
            "description": "Healgen (HGS prefix)"
        },
        {
            "sku": "WON QODOA6126I",
            "brand": "Wondfo",
            "name": "Wondfo® T-Square Oral Fluid Drug Test",
            "expected": "wondfo",
            "description": "Wondfo (WON prefix)"
        },
        # Brand field detection
        {
            "sku": "VWR BDH85800400",
            "brand": "VWR",
            "name": "VWR® BDH® Chemicals Methanol",
            "expected": "VWR",
            "description": "Other brand (brand field)"
        },
        # Product name detection
        {
            "sku": "TEST-001",
            "brand": None,
            "name": "Mercedes Scientific® Microscope Slides",
            "expected": "mercedes scientific",
            "description": "Mercedes (from name, no brand field)"
        },
        {
            "sku": "TEST-002",
            "brand": None,
            "name": "Tanner Scientific® Pipette Tips",
            "expected": "tanner scientific",
            "description": "Tanner (from name, no brand field)"
        },
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        result = indexer._detect_brand(test["sku"], test["brand"], test["name"])
        status = "✅ PASS" if result == test["expected"] else "❌ FAIL"

        print(f"{status} | {test['description']}")
        print(f"     SKU: {test['sku']}, Brand: {test['brand']}")
        print(f"     Expected: {test['expected']}, Got: {result}")
        print()

        if result == test["expected"]:
            passed += 1
        else:
            failed += 1

    print(f"Results: {passed} passed, {failed} failed\n")
    return failed == 0


def test_brand_priority_calculation():
    """Test brand priority calculation for different categories."""
    print("=" * 80)
    print("BRAND PRIORITY CALCULATION TEST")
    print("=" * 80)
    print()

    indexer = NeonProductIndexer()

    test_cases = [
        # LCMS/HPLC Solvents
        {
            "sku": "TBK 8003LC4000",
            "brand": "Concord Technology",
            "name": "Concord Water, HPLC Grade",
            "categories": ["Brand: Concord Technology", "Grade: HPLC"],
            "expected": 100,
            "description": "LCMS/HPLC - Concord (should be 100)"
        },
        {
            "sku": "BIR 19395",
            "brand": "Birch Biotech",
            "name": "Birch® Biotech PRISTINE® Water, LC-MS Grade",
            "categories": ["Brand: Birch Biotech", "Grade: LCMS"],
            "expected": 90,
            "description": "LCMS/HPLC - Birch (should be 90)"
        },
        {
            "sku": "MER SOLV001",
            "brand": "Mercedes Scientific",
            "name": "Mercedes Scientific HPLC Solvent",
            "categories": ["Grade: HPLC"],
            "expected": 80,
            "description": "LCMS/HPLC - Mercedes (should be 80)"
        },
        {
            "sku": "TNR SOLV001",
            "brand": "Tanner Scientific",
            "name": "Tanner Scientific HPLC Solvent",
            "categories": ["Grade: Ultra HPLC"],
            "expected": 70,
            "description": "LCMS/HPLC - Tanner (should be 70)"
        },
        {
            "sku": "VWR BDH85800400",
            "brand": "VWR",
            "name": "VWR® BDH® Chemicals Methanol ≥99.9%, HiPerSolv CHROMANORM®",
            "categories": ["Brand: VWR", "Grade: Ultra HPLC"],
            "expected": 50,
            "description": "LCMS/HPLC - Other brand (should be 50)"
        },
        # Drug Testing
        {
            "sku": "MER MMDOAY6125",
            "brand": "Mercedes Scientific",
            "name": "Mercedes Scientific® Platinum+ 12-Panel Drug Test Cup",
            "categories": ["Products/Drug Tests/Urine", "Brand: Mercedes Scientific"],
            "expected": 100,
            "description": "Drug Testing - Mercedes (should be 100)"
        },
        {
            "sku": "ALT DOAA1137C",
            "brand": None,
            "name": "AllTest® Multi-Drug Rapid Test Cup",
            "categories": ["Products/Drug Tests/Urine"],
            "expected": 90,
            "description": "Drug Testing - AllTest (should be 90)"
        },
        {
            "sku": "TNR MMC12MOP",
            "brand": "Tanner Scientific",
            "name": "Tanner Scientific® BluRapids® Multi-Drug Test Cup",
            "categories": ["Products/Drug Tests/Urine"],
            "expected": 80,
            "description": "Drug Testing - Tanner (should be 80)"
        },
        {
            "sku": "HGS HDCL114",
            "brand": "Healgen Scientific",
            "name": "Healgen® Single Drug Test Dip Card",
            "categories": ["Products/Drug Tests/Urine"],
            "expected": 70,
            "description": "Drug Testing - Healgen (should be 70)"
        },
        {
            "sku": "WON QODOA6126I",
            "brand": "Wondfo",
            "name": "Wondfo® T-Square Oral Fluid Drug Test",
            "categories": ["Products/Drug Tests/Saliva"],
            "expected": 60,
            "description": "Drug Testing - Wondfo (should be 60)"
        },
        # General categories
        {
            "sku": "MER SLIDE001",
            "brand": "Mercedes Scientific",
            "name": "Mercedes Scientific® Microscope Slides",
            "categories": ["Products/Lab Equipment"],
            "expected": 100,
            "description": "General - Mercedes (should be 100)"
        },
        {
            "sku": "TNR GLOVE001",
            "brand": "Tanner Scientific",
            "name": "Tanner Scientific® Nitrile Gloves",
            "categories": ["Products/Gloves"],
            "expected": 90,
            "description": "General - Tanner (should be 90)"
        },
        {
            "sku": "VWR 12345",
            "brand": "VWR",
            "name": "VWR® Pipette Tips",
            "categories": ["Products/Lab Supplies"],
            "expected": 50,
            "description": "General - Other brand (should be 50)"
        },
        {
            "sku": "UNKNOWN-123",
            "brand": None,
            "name": "Generic Product",
            "categories": ["Products/Generic"],
            "expected": 0,
            "description": "General - No brand (should be 0)"
        },
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        result = indexer._calculate_brand_priority(
            test["sku"],
            test["brand"],
            test["name"],
            test["categories"]
        )
        status = "✅ PASS" if result == test["expected"] else "❌ FAIL"

        print(f"{status} | {test['description']}")
        print(f"     SKU: {test['sku']}")
        print(f"     Categories: {test['categories']}")
        print(f"     Expected: {test['expected']}, Got: {result}")
        print()

        if result == test["expected"]:
            passed += 1
        else:
            failed += 1

    print(f"Results: {passed} passed, {failed} failed\n")
    return failed == 0


def main():
    """Run all tests."""
    print("\n🧪 BRAND RANKING LOGIC TEST SUITE\n")

    all_passed = True

    # Test 1: Category Detection
    if not test_category_detection():
        all_passed = False

    # Test 2: Brand Detection
    if not test_brand_detection():
        all_passed = False

    # Test 3: Brand Priority Calculation
    if not test_brand_priority_calculation():
        all_passed = False

    # Summary
    print("=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("\n✅ Logic is correct. Ready to re-index for production use.")
        print("   Run: ./venv/bin/python3 src/indexer_neon.py")
    else:
        print("❌ SOME TESTS FAILED!")
        print("\n⚠️  Please fix the issues before re-indexing.")
    print("=" * 80)


if __name__ == "__main__":
    main()
