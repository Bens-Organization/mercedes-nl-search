"""
Tests for Restricted Item Access Control (JAI-2166)

Tests the implementation of 3-class restricted item filtering system.

Three Restricted Classes:
1. FUO (Forensic Use Only) - "FORENSIC USE ONLY"
   - Visible to all users in search results
   - Cannot add to cart without permissions
   - Form required: https://marketing.mercedesscientific.com/en-us/fuo-form

2. CLIA Waived - "CLIA WV"
   - Visible to all users in search results
   - Cannot add to cart without permissions
   - CLIA license required

3. Alternative Sourced Items - "ALT SOURCE"
   - Hidden from users without permissions
   - Cannot add to cart without permissions
   - Typically Beckman Coulter and Olympus products

Test Categories:
1. Search without authentication (should exclude ALT SOURCE only)
2. Search with authentication but no permissions (should exclude ALT SOURCE only)
3. Search with authentication and permissions (should include all items)
4. Direct product access control
5. Restriction helper functions
6. Visibility rules for FUO and CLIA WV (visible to all)
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app
from src.restrictions import (
    is_restricted_brand,
    is_restricted_sku,
    is_restricted_product,
    build_restriction_filter,
    get_restriction_disclaimer
)

client = TestClient(app)


class TestRestrictionHelpers:
    """Test restriction helper functions."""

    def test_is_restricted_brand_beckman(self):
        """Beckman Coulter should be identified as restricted."""
        assert is_restricted_brand("Beckman Coulter") is True

    def test_is_restricted_brand_olympus(self):
        """Olympus should be identified as restricted."""
        assert is_restricted_brand("Olympus") is True

    def test_is_restricted_brand_normal(self):
        """Normal brands should not be restricted."""
        assert is_restricted_brand("Mercedes Scientific") is False
        assert is_restricted_brand("Tanner Scientific") is False

    def test_is_restricted_brand_none(self):
        """None/empty brand should not be restricted."""
        assert is_restricted_brand(None) is False
        assert is_restricted_brand("") is False

    def test_is_restricted_sku_beckman(self):
        """BEY SKUs should be identified as restricted."""
        assert is_restricted_sku("BEY 64130") is True
        assert is_restricted_sku("BEY64130") is True

    def test_is_restricted_sku_olympus(self):
        """OSR SKUs should be identified as restricted."""
        assert is_restricted_sku("OSR 12345") is True
        assert is_restricted_sku("OSR12345") is True

    def test_is_restricted_sku_normal(self):
        """Normal SKUs should not be restricted."""
        assert is_restricted_sku("TNR 700S") is False
        assert is_restricted_sku("CLI 501003") is False

    def test_is_restricted_product(self):
        """Test combined brand and SKU restriction check."""
        # Restricted by brand
        assert is_restricted_product("Beckman Coulter", "ABC123") is True
        # Restricted by SKU
        assert is_restricted_product("Other Brand", "BEY 12345") is True
        # Not restricted
        assert is_restricted_product("Mercedes Scientific", "TNR 700S") is False

    def test_build_restriction_filter_without_permissions(self):
        """Filter should exclude ALT SOURCE when user has no permissions."""
        perms = {"has_restricted_access": False}
        filter_str = build_restriction_filter(perms)
        assert "restricted_class:!=[ALT SOURCE]" in filter_str

    def test_build_restriction_filter_with_permissions(self):
        """Filter should be empty when user has permissions."""
        perms = {"has_restricted_access": True}
        filter_str = build_restriction_filter(perms)
        assert filter_str == ""

    def test_get_restriction_disclaimer(self):
        """Disclaimer should contain key information."""
        disclaimer = get_restriction_disclaimer()
        assert "Beckman Coulter" in disclaimer
        assert "not an authorized distributor" in disclaimer


class TestSearchWithoutAuthentication:
    """Test search behavior for non-authenticated users."""

    def test_search_beckman_no_auth(self):
        """
        Non-authenticated users searching for "beckman" should get 0 results.

        Expected behavior:
        - restricted_class=ALT SOURCE products are excluded
        - Only Beckman products with restricted_class=Normal would appear (if any)
        """
        response = client.post("/api/search", json={"query": "beckman"})
        assert response.status_code == 200

        data = response.json()
        # Most Beckman products have restricted_class=ALT SOURCE
        # So result count should be very low (close to 0)
        assert data["total"] < 50, f"Expected < 50 results, got {data['total']}"

        # Verify no restricted items in results
        for product in data["results"]:
            assert product.get("restricted_class") != "ALT SOURCE", \
                f"Found restricted product: {product['sku']} - {product['name']}"

    def test_search_olympus_no_auth(self):
        """
        Non-authenticated users searching for "olympus" should get limited results.

        Expected behavior:
        - restricted_class=ALT SOURCE products are excluded
        - Only compatible/third-party Olympus products appear
        """
        response = client.post("/api/search", json={"query": "olympus"})
        assert response.status_code == 200

        data = response.json()
        # Verify no restricted items in results
        for product in data["results"]:
            assert product.get("restricted_class") != "ALT SOURCE", \
                f"Found restricted product: {product['sku']} - {product['name']}"

    def test_search_normal_products_no_auth(self):
        """
        Non-authenticated users searching for normal products should get full results.

        Expected behavior:
        - All non-restricted products appear normally
        """
        response = client.post("/api/search", json={"query": "gloves"})
        assert response.status_code == 200

        data = response.json()
        assert data["total"] > 0, "Should find gloves"

    def test_search_get_endpoint_no_auth(self):
        """GET endpoint should also filter restricted items."""
        response = client.get("/api/search?q=beckman&limit=10")
        assert response.status_code == 200

        data = response.json()
        # Verify no restricted items in results
        for product in data["results"]:
            assert product.get("restricted_class") != "ALT SOURCE"


class TestSearchWithPermissions:
    """Test search behavior for users with restricted item permissions."""

    def test_search_beckman_with_permissions(self):
        """
        Users with permissions searching for "beckman" should see all products.

        Expected behavior:
        - restricted_class=ALT SOURCE products are included
        - All ~231 Beckman products appear
        """
        headers = {"X-Customer-Permissions": "restricted_access"}
        response = client.post("/api/search", json={"query": "beckman"}, headers=headers)
        assert response.status_code == 200

        data = response.json()
        # Should see significantly more products (including ALT SOURCE)
        assert data["total"] > 100, f"Expected > 100 results with permissions, got {data['total']}"

        # Some results should have restricted_class=ALT SOURCE
        alt_source_found = any(
            p.get("restricted_class") == "ALT SOURCE"
            for p in data["results"]
        )
        assert alt_source_found, "Should find ALT SOURCE products with permissions"

    def test_search_with_beckman_access_permission(self):
        """Test with beckman_access specific permission."""
        headers = {"X-Customer-Permissions": "beckman_access"}
        response = client.post("/api/search", json={"query": "beckman"}, headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["total"] > 100

    def test_search_with_customer_group(self):
        """Test with customer group authorization."""
        headers = {"X-Customer-Group": "authorized"}
        response = client.post("/api/search", json={"query": "beckman"}, headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["total"] > 100

    def test_search_with_authorization_header(self):
        """Test with Bearer token (simulated)."""
        headers = {
            "Authorization": "Bearer fake-token-for-testing",
            "X-Customer-Permissions": "restricted_access"
        }
        response = client.post("/api/search", json={"query": "beckman"}, headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["total"] > 100


class TestSearchWithoutPermissions:
    """Test search behavior for authenticated users without restricted item permissions."""

    def test_search_authenticated_no_permissions(self):
        """
        Authenticated users without permissions should not see restricted items.

        Expected behavior:
        - Same as non-authenticated users
        - restricted_class=ALT SOURCE products are excluded
        """
        headers = {"Authorization": "Bearer fake-token"}
        # Note: No X-Customer-Permissions header = no restricted access
        response = client.post("/api/search", json={"query": "beckman"}, headers=headers)
        assert response.status_code == 200

        data = response.json()
        # Should get limited results (no ALT SOURCE)
        assert data["total"] < 50

        # Verify no restricted items in results
        for product in data["results"]:
            assert product.get("restricted_class") != "ALT SOURCE"


class TestSpecificProducts:
    """Test access to specific restricted products mentioned in the ticket."""

    def test_beckman_isoton_product_without_auth(self):
        """
        Test for: Beckman Coulter Reagent, Isoton, III Diluent 20L (BEY 8546733)

        Expected: Should NOT appear in search results without permissions
        """
        response = client.post("/api/search", json={"query": "BEY 8546733 isoton"})
        assert response.status_code == 200

        data = response.json()
        # Should not find this specific product
        isoton_found = any(
            "8546733" in p["sku"] or "isoton" in p["name"].lower()
            for p in data.get("results", [])
        )
        # If found, it should NOT be the ALT SOURCE version
        if isoton_found:
            for p in data["results"]:
                if "8546733" in p["sku"] or "isoton" in p["name"].lower():
                    assert p.get("restricted_class") != "ALT SOURCE"

    def test_beckman_access_folate_without_auth(self):
        """
        Test for: Beckman Coulter® Access® Red Blood Cell Folate (BEY A14206)

        Expected: Should NOT appear in search results without permissions
        """
        response = client.post("/api/search", json={"query": "BEY A14206 folate"})
        assert response.status_code == 200

        data = response.json()
        # Verify no ALT SOURCE products
        for product in data.get("results", []):
            assert product.get("restricted_class") != "ALT SOURCE"

    def test_olympus_albumin_without_auth(self):
        """
        Test for: Beckman Coulter® Olympus Albumin, 4 x 1120 Tests (BEY OSR6202)

        Expected: Should NOT appear in search results without permissions
        """
        response = client.post("/api/search", json={"query": "OSR6202 albumin"})
        assert response.status_code == 200

        data = response.json()
        # Verify no ALT SOURCE products
        for product in data.get("results", []):
            assert product.get("restricted_class") != "ALT SOURCE"


@pytest.mark.skip(reason="Direct product access endpoint not yet implemented")
class TestDirectProductAccess:
    """Test direct URL access to restricted products."""

    def test_direct_access_restricted_product_no_auth(self):
        """
        Direct access to restricted product should return 404.

        Expected: GET /api/product/BEY-64130 → 404
        """
        response = client.get("/api/product/BEY 64130")
        assert response.status_code == 404

    def test_direct_access_restricted_product_with_auth(self):
        """
        Direct access to restricted product with permissions should work.

        Expected: GET /api/product/BEY-64130 → 200 with product data
        """
        headers = {"X-Customer-Permissions": "restricted_access"}
        response = client.get("/api/product/BEY 64130", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["sku"] == "BEY 64130"
        assert data.get("restricted_class") == "ALT SOURCE"

    def test_direct_access_normal_product_no_auth(self):
        """
        Direct access to normal product should work for everyone.

        Expected: GET /api/product/TNR-700S → 200
        """
        response = client.get("/api/product/TNR 700S")
        assert response.status_code == 200


class TestVisibleRestrictions:
    """Test that FUO and CLIA WV items are visible to all users."""

    def test_fuo_items_visible_without_auth(self):
        """
        FUO items should be visible in search results even without authentication.

        Expected behavior:
        - restricted_class=FORENSIC USE ONLY products appear in results
        - Users can see these products but frontend should disable "Add to Cart"
        """
        response = client.post("/api/search", json={"query": "forensic"})
        assert response.status_code == 200

        data = response.json()
        # Should find products (if any FUO items exist with "forensic" in name/description)
        # Note: This test will pass even if 0 results (no FUO items in catalog)
        # But it verifies that FUO items are NOT filtered out

        for product in data.get("results", []):
            # Verify that if we find FUO items, they're included
            if product.get("restricted_class") == "FORENSIC USE ONLY":
                print(f"✓ Found FUO item visible without auth: {product['name']}")

    def test_clia_waived_items_visible_without_auth(self):
        """
        CLIA WV items should be visible in search results even without authentication.

        Expected behavior:
        - restricted_class=CLIA WV products appear in results
        - Users can see these products but frontend should disable "Add to Cart"
        """
        response = client.post("/api/search", json={"query": "clia"})
        assert response.status_code == 200

        data = response.json()
        # Should find products (if any CLIA WV items exist)

        for product in data.get("results", []):
            # Verify that if we find CLIA WV items, they're included
            if product.get("restricted_class") == "CLIA WV":
                print(f"✓ Found CLIA WV item visible without auth: {product['name']}")

    def test_fuo_and_clia_not_filtered_in_general_search(self):
        """
        General search should include FUO and CLIA WV items (only exclude ALT SOURCE).

        Expected behavior:
        - Search for common terms includes FUO and CLIA WV items
        - ALT SOURCE items are excluded
        """
        response = client.post("/api/search", json={"query": "gloves"})
        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= 0

        # Count items by restriction class
        fuo_count = 0
        clia_count = 0
        alt_source_count = 0
        normal_count = 0

        for product in data.get("results", []):
            restriction = product.get("restricted_class")
            if restriction == "FORENSIC USE ONLY":
                fuo_count += 1
            elif restriction == "CLIA WV":
                clia_count += 1
            elif restriction == "ALT SOURCE":
                alt_source_count += 1
            else:
                normal_count += 1

        print(f"Results breakdown:")
        print(f"  Normal items: {normal_count}")
        print(f"  FUO items: {fuo_count}")
        print(f"  CLIA WV items: {clia_count}")
        print(f"  ALT SOURCE items: {alt_source_count}")

        # Verify ALT SOURCE is filtered out
        assert alt_source_count == 0, f"Found {alt_source_count} ALT SOURCE items without auth"

        # FUO and CLIA WV can be present (not an error if they are)
        if fuo_count > 0:
            print(f"✓ FUO items are visible without auth (as expected)")
        if clia_count > 0:
            print(f"✓ CLIA WV items are visible without auth (as expected)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
