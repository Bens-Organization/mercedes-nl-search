"""
Restricted Item Access Control Module

This module handles access control for restricted items (Beckman/Olympus products)
that require special account permissions to view and search.

Business Rules:
- Beckman Coulter and Olympus branded products are restricted
- Non-authenticated users OR users without permissions cannot see restricted items
- Authenticated users with permissions can see restricted items with disclaimers
"""

from typing import Dict, Any, Optional
from config import Config
from fastapi import Request


def is_restricted_brand(brand: Optional[str]) -> bool:
    """
    Check if a brand is restricted.

    Args:
        brand: Product brand name

    Returns:
        True if brand is restricted, False otherwise

    Examples:
        >>> is_restricted_brand("Beckman Coulter")
        True
        >>> is_restricted_brand("Mercedes Scientific")
        False
    """
    if not brand:
        return False

    # Normalize brand name for comparison
    brand_normalized = brand.strip().lower()

    for restricted_brand in Config.RESTRICTED_BRANDS:
        if restricted_brand.strip().lower() in brand_normalized:
            return True

    return False


def is_restricted_sku(sku: Optional[str]) -> bool:
    """
    Check if a SKU indicates a restricted product.

    Args:
        sku: Product SKU

    Returns:
        True if SKU indicates restricted product, False otherwise

    Examples:
        >>> is_restricted_sku("BEY 64130")
        True
        >>> is_restricted_sku("TNR 700S")
        False
    """
    if not sku:
        return False

    sku_normalized = sku.strip().upper()

    for prefix in Config.RESTRICTED_SKU_PREFIXES:
        # Check if SKU starts with prefix (allowing for spaces)
        prefix_normalized = prefix.strip().upper()
        if sku_normalized.startswith(prefix_normalized):
            return True
        # Also check without spaces (e.g., "BEY64130")
        if sku_normalized.replace(" ", "").startswith(prefix_normalized):
            return True

    return False


def is_restricted_product(brand: Optional[str], sku: Optional[str]) -> bool:
    """
    Check if a product is restricted based on brand or SKU.

    Args:
        brand: Product brand name
        sku: Product SKU

    Returns:
        True if product is restricted, False otherwise
    """
    return is_restricted_brand(brand) or is_restricted_sku(sku)


async def get_user_permissions(request: Request) -> Dict[str, Any]:
    """
    Extract and validate user permissions from request.

    Checks multiple sources for user permissions:
    1. Authorization header (Bearer token)
    2. X-Customer-Permissions header (comma-separated permissions)
    3. X-Customer-Group header (customer group)

    Args:
        request: FastAPI request object

    Returns:
        Dictionary with user permission flags:
        - authenticated: bool - User is authenticated
        - has_restricted_access: bool - User can view restricted items
        - permissions: list - List of permission strings
        - customer_group: str - Customer group (if available)

    Examples:
        With permissions header:
        >>> headers = {"X-Customer-Permissions": "restricted_access,beckman_access"}
        >>> perms = await get_user_permissions(request)
        >>> perms["has_restricted_access"]
        True

        Without permissions:
        >>> headers = {}
        >>> perms = await get_user_permissions(request)
        >>> perms["has_restricted_access"]
        False
    """
    # Check if authentication is enabled
    if not Config.AUTH_ENABLED:
        # If auth is disabled, allow all access (for development)
        # In production, this should be enabled
        return {
            "authenticated": False,
            "has_restricted_access": False,
            "permissions": [],
            "customer_group": None
        }

    # Check Authorization header
    auth_header = request.headers.get("authorization", "")
    has_auth_token = auth_header.startswith("Bearer ")

    # Check X-Customer-Permissions header
    permissions_header = request.headers.get("x-customer-permissions", "")
    permissions = [p.strip() for p in permissions_header.split(",") if p.strip()]

    # Check X-Customer-Group header
    customer_group = request.headers.get("x-customer-group", "")

    # Check if user has restricted item access
    has_restricted_access = any([
        "restricted_access" in permissions,
        "beckman_access" in permissions,
        "olympus_access" in permissions,
        customer_group.lower() in ["authorized", "premium", "dealer"]
    ])

    return {
        "authenticated": has_auth_token or bool(permissions_header) or bool(customer_group),
        "has_restricted_access": has_restricted_access,
        "permissions": permissions,
        "customer_group": customer_group or None
    }


def build_restriction_filter(user_permissions: Dict[str, Any]) -> str:
    """
    Build Typesense filter to exclude restricted items.

    If user has restricted access, returns empty string (no filter needed).
    Otherwise, returns filter to exclude items with restricted_class=ALT SOURCE.

    Args:
        user_permissions: Dictionary from get_user_permissions()

    Returns:
        Filter string for Typesense search (e.g., "restricted_class:!=[ALT SOURCE]")

    Examples:
        With permissions:
        >>> perms = {"has_restricted_access": True}
        >>> build_restriction_filter(perms)
        ''

        Without permissions:
        >>> perms = {"has_restricted_access": False}
        >>> build_restriction_filter(perms)
        'restricted_class:!=[ALT SOURCE]'
    """
    # If user has restricted access, no filter needed
    if user_permissions.get("has_restricted_access"):
        return ""

    # Exclude products with restricted_class=ALT SOURCE
    # Use exact match with square brackets to handle spaces in value
    return "restricted_class:!=[ALT SOURCE]"


def get_restriction_disclaimer() -> str:
    """
    Get the disclaimer text for restricted items.

    Returns:
        Disclaimer text to display for authorized users
    """
    return (
        "This product is a genuine Beckman Coulter® item acquired through "
        "independent, third-party distribution channels. Mercedes Scientific is "
        "not an authorized distributor of Beckman Coulter products. As such, "
        "purchase of this product may not satisfy any requirements for authorized "
        "distribution channels."
    )
