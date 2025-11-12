"""
Restricted Item Access Control Module

This module handles access control for 3 classes of restricted items that require
special account permissions to view, search, or purchase.

Three Restricted Classes:

1. FUO (Forensic Use Only) - "FORENSIC USE ONLY"
   - Visible to all users
   - Cannot add to cart without permissions
   - Requires form: https://marketing.mercedesscientific.com/en-us/fuo-form

2. CLIA Waived - "CLIA WV"
   - Visible to all users
   - Cannot add to cart without permissions
   - Requires CLIA license submitted to CLIA@Mercedesscientific.com

3. Alternative Sourced Items - "ALT SOURCE"
   - Hidden from users without permissions
   - Cannot add to cart without permissions
   - Typically Beckman Coulter and Olympus products

Business Rules:
- FUO and CLIA WV: Always visible, purchase requires authorization
- ALT SOURCE: Hidden unless user has restricted_access permission
- Authenticated users with permissions can see all items with disclaimers
"""

from typing import Dict, Any, Optional
from config import Config
from fastapi import Request


class RestrictedClass:
    """
    Constants for the 3 restricted classes of products.

    Database Field: restricted_class_id (from customer_x_restricted_class table)
    """
    # Forensic Use Only
    FORENSIC_USE_ONLY = "FORENSIC USE ONLY"

    # CLIA Waived (Clinical Laboratory Improvement Amendments)
    CLIA_WAIVED = "CLIA WV"

    # Alternative Sourced Items (third-party distributors)
    ALT_SOURCE = "ALT SOURCE"

    # All restricted classes
    ALL = [FORENSIC_USE_ONLY, CLIA_WAIVED, ALT_SOURCE]

    # Classes that are visible to all users (but not purchasable without permission)
    VISIBLE_CLASSES = [FORENSIC_USE_ONLY, CLIA_WAIVED]

    # Classes that are hidden from unauthorized users
    HIDDEN_CLASSES = [ALT_SOURCE]


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


def is_hidden_restriction(restricted_class: Optional[str]) -> bool:
    """
    Check if a restriction class means the product should be hidden from unauthorized users.

    Args:
        restricted_class: The restricted_class value ("FORENSIC USE ONLY", "CLIA WV", "ALT SOURCE", or None)

    Returns:
        True if product should be hidden (ALT SOURCE only), False otherwise

    Examples:
        >>> is_hidden_restriction("ALT SOURCE")
        True
        >>> is_hidden_restriction("FORENSIC USE ONLY")
        False
        >>> is_hidden_restriction("CLIA WV")
        False
        >>> is_hidden_restriction(None)
        False
    """
    return restricted_class in RestrictedClass.HIDDEN_CLASSES


def is_visible_restriction(restricted_class: Optional[str]) -> bool:
    """
    Check if a restriction class means the product is visible but not purchasable.

    Args:
        restricted_class: The restricted_class value

    Returns:
        True if product is visible but requires authorization to purchase (FUO, CLIA WV)

    Examples:
        >>> is_visible_restriction("FORENSIC USE ONLY")
        True
        >>> is_visible_restriction("CLIA WV")
        True
        >>> is_visible_restriction("ALT SOURCE")
        False
    """
    return restricted_class in RestrictedClass.VISIBLE_CLASSES


def requires_authorization(restricted_class: Optional[str]) -> bool:
    """
    Check if a product requires authorization to purchase (any restricted class).

    Args:
        restricted_class: The restricted_class value

    Returns:
        True if product requires authorization to purchase

    Examples:
        >>> requires_authorization("FORENSIC USE ONLY")
        True
        >>> requires_authorization("CLIA WV")
        True
        >>> requires_authorization("ALT SOURCE")
        True
        >>> requires_authorization(None)
        False
    """
    return restricted_class in RestrictedClass.ALL


def get_restriction_disclaimer(restricted_class: Optional[str]) -> Optional[str]:
    """
    Get the appropriate disclaimer text for a restricted item.

    Args:
        restricted_class: The restricted_class value

    Returns:
        Disclaimer text specific to the restriction class, or None if not restricted

    Examples:
        >>> get_restriction_disclaimer("FORENSIC USE ONLY")
        'This product is for forensic use only...'
        >>> get_restriction_disclaimer(None)
        None
    """
    if restricted_class == RestrictedClass.FORENSIC_USE_ONLY:
        return (
            "⚠️ FORENSIC USE ONLY: This product is restricted to forensic laboratory use. "
            "Authorization is required to purchase. Please complete the form at "
            "https://marketing.mercedesscientific.com/en-us/fuo-form"
        )
    elif restricted_class == RestrictedClass.CLIA_WAIVED:
        return (
            "⚠️ CLIA WAIVED: This product requires CLIA certification. "
            "Authorization is required to purchase. Please submit your CLIA license to "
            "CLIA@Mercedesscientific.com"
        )
    elif restricted_class == RestrictedClass.ALT_SOURCE:
        return (
            "⚠️ ALTERNATIVE SOURCED: This product is acquired through independent, "
            "third-party distribution channels. Mercedes Scientific is not an authorized "
            "distributor for this brand. Purchase may not satisfy requirements for "
            "authorized distribution channels. Authorization is required to view and purchase."
        )

    return None


def get_restriction_info(restricted_class: Optional[str]) -> Dict[str, Any]:
    """
    Get comprehensive information about a restriction class.

    Args:
        restricted_class: The restricted_class value

    Returns:
        Dictionary with restriction information:
        - is_restricted: bool - Product has any restriction
        - is_visible: bool - Product is visible to all users
        - is_hidden: bool - Product is hidden from unauthorized users
        - requires_auth: bool - Purchase requires authorization
        - disclaimer: str - Disclaimer text
        - restriction_type: str - Type of restriction

    Examples:
        >>> info = get_restriction_info("ALT SOURCE")
        >>> info["is_hidden"]
        True
        >>> info["is_visible"]
        False
    """
    return {
        "is_restricted": requires_authorization(restricted_class),
        "is_visible": not is_hidden_restriction(restricted_class),
        "is_hidden": is_hidden_restriction(restricted_class),
        "requires_auth": requires_authorization(restricted_class),
        "disclaimer": get_restriction_disclaimer(restricted_class),
        "restriction_type": restricted_class
    }
