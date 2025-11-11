#!/usr/bin/env python3
"""Quick test of brand ranking logic."""

from indexer_neon import NeonProductIndexer

# Test category detection
indexer = NeonProductIndexer()

print('=' * 80)
print('BRAND RANKING LOGIC TEST')
print('=' * 80)
print()

print('=== Category Detection Test ===')
print()

# Test HPLC
cats_hplc = ['Products/Chemicals & Stains/Methanol', 'Brand: VWR', 'Grade: HPLC', 'Size: 4 Liter']
result = indexer._detect_category_type(cats_hplc)
status = '✅' if result == 'lcms_hplc' else '❌'
print(f'{status} HPLC categories: {result} (expected: lcms_hplc)')

# Test LCMS
cats_lcms = ['Products/Chemicals & Stains/Water', 'Brand: Birch Biotech', 'Grade: LCMS']
result = indexer._detect_category_type(cats_lcms)
status = '✅' if result == 'lcms_hplc' else '❌'
print(f'{status} LCMS categories: {result} (expected: lcms_hplc)')

# Test Drug Testing
cats_drug = ['Products/Drug Tests/Saliva', 'Brand: Wondfo']
result = indexer._detect_category_type(cats_drug)
status = '✅' if result == 'drug_testing' else '❌'
print(f'{status} Drug Test categories: {result} (expected: drug_testing)')

# Test General
cats_general = ['Products/Gloves/Nitrile', 'Brand: Mercedes Scientific']
result = indexer._detect_category_type(cats_general)
status = '✅' if result == 'general' else '❌'
print(f'{status} General categories: {result} (expected: general)')
print()

print('=== Brand Detection Test ===')
print()

# Test SKU prefix detection
tests = [
    ('TBK 8003LC4000', 'Concord Technology', 'Concord Water, HPLC Grade', 'concord technologies'),
    ('BIR 19395', 'Birch Biotech', 'Birch® Biotech PRISTINE® Water', 'birch biotech'),
    ('MER MMDOAY6125', 'Mercedes Scientific', 'Mercedes Scientific® Platinum+ 12-Panel Drug Test Cup', 'mercedes scientific'),
    ('ALT DOAA1137C', None, 'AllTest® Multi-Drug Rapid Test Cup', 'alltest'),
    ('TNR MMC12MOP', 'Tanner Scientific', 'Tanner Scientific® BluRapids® Multi-Drug Test Cup', 'tanner scientific'),
    ('HGS HDCL114', 'Healgen Scientific', 'Healgen® Single Drug Test Dip Card', 'healgen'),
    ('WON QODOA6126I', 'Wondfo', 'Wondfo® T-Square Oral Fluid Drug Test', 'wondfo'),
]

for sku, brand, name, expected in tests:
    result = indexer._detect_brand(sku, brand, name)
    status = '✅' if result == expected else '❌'
    print(f'{status} {sku}: {result} (expected: {expected})')

print()

print('=== Brand Priority Calculation Test ===')
print()

priority_tests = [
    # LCMS/HPLC Solvents
    ('TBK 8003LC4000', 'Concord Technology', 'Concord Water', ['Grade: HPLC'], 100, 'HPLC - Concord'),
    ('BIR 19395', 'Birch Biotech', 'Birch Water', ['Grade: LCMS'], 90, 'LCMS - Birch'),
    ('MER SOLV001', 'Mercedes Scientific', 'Mercedes HPLC Solvent', ['Grade: HPLC'], 80, 'HPLC - Mercedes'),
    ('TNR SOLV001', 'Tanner Scientific', 'Tanner HPLC Solvent', ['Grade: Ultra HPLC'], 70, 'HPLC - Tanner'),
    ('VWR 123', 'VWR', 'VWR Methanol', ['Grade: HPLC'], 50, 'HPLC - VWR'),
    # Drug Testing
    ('MER DRUG001', 'Mercedes Scientific', 'Mercedes Drug Test', ['Products/Drug Tests/Urine'], 100, 'Drug - Mercedes'),
    ('ALT DRUG001', None, 'AllTest Drug Test', ['Products/Drug Tests/Urine'], 90, 'Drug - AllTest'),
    ('TNR DRUG001', 'Tanner Scientific', 'Tanner Drug Test', ['Products/Drug Tests/Urine'], 80, 'Drug - Tanner'),
    ('HGS DRUG001', 'Healgen Scientific', 'Healgen Drug Test', ['Products/Drug Tests/Urine'], 70, 'Drug - Healgen'),
    ('WON DRUG001', 'Wondfo', 'Wondfo Drug Test', ['Products/Drug Tests/Saliva'], 60, 'Drug - Wondfo'),
    # General
    ('MER GEN001', 'Mercedes Scientific', 'Mercedes Gloves', ['Products/Gloves'], 100, 'General - Mercedes'),
    ('TNR GEN001', 'Tanner Scientific', 'Tanner Slides', ['Products/Lab Equipment'], 90, 'General - Tanner'),
    ('VWR GEN001', 'VWR', 'VWR Pipettes', ['Products/Lab Supplies'], 50, 'General - VWR'),
]

for sku, brand, name, categories, expected, desc in priority_tests:
    result = indexer._calculate_brand_priority(sku, brand, name, categories)
    status = '✅' if result == expected else '❌'
    print(f'{status} {desc}: Priority {result} (expected: {expected})')

print()
print('=' * 80)
print('✅ All logic tests completed!')
print('=' * 80)
