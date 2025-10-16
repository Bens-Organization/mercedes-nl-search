# Mercedes Scientific GraphQL API Documentation

## Overview

Mercedes Scientific's e-commerce platform is built on **Adobe Commerce** (formerly Magento 2) and exposes a comprehensive GraphQL API for product catalog access.

**GraphQL Endpoint:** `https://www.mercedesscientific.com/graphql`

## Store Configuration

```json
{
  "store_code": "mercedesscientific",
  "store_name": "Mercedes Scientific Store View",
  "locale": "en_US",
  "base_currency_code": "USD",
  "default_display_currency_code": "USD",
  "timezone": "America/Los_Angeles",
  "website_id": 1,
  "weight_unit": "lbs"
}
```

## Product Catalog Statistics

- **Total Products**: 26,953 products
- **Main Category Structure**: 5 top-level categories
  - Products (33 subcategories, 23,574 products)
  - Shop By Lab (16 subcategories, 9,673 products)
  - Clearance (19 products)
  - Promotions (30 subcategories, 12 products)
  - Limited Time Savings (40 products)

## Key Product Categories

### Products (Shop by Product)
1. **Absorbent Sheets, Pads & Mats** (32 products)
2. **Bags** (285 products)
3. **Blades & Handles** (202 products)
4. **Calibrators & Controls** (499 products)
5. **Chemicals & Stains** (3,166 products)
6. **Cleaners** (188 products)
7. **Deep Well Plates & Accessories** (267 products)
8. **Drug Tests** (215 products)
9. **Embedding, Cryotomy & Grossing** (978 products)
10. **Equipment & Accessories** (389 products)
11. **Filtration** (231 products)
12. **Glass & Plasticware** (2,206 products)
13. **Gloves & Apparel** (380 products)
14. **Labels & Labeling Tape** (318 products)
15. **Laboratory Essentials** (1,145 products)
16. **MedSurg & Exam Room Supplies** (1,136 products)
17. **Microscope Slides, Coverslips & Control Slides** (508 products)
18. **Needles & Syringes** (286 products)
19. **Pipettes, Pipettors, Tips & Accessories** (1,024 products)
20. **Rapid Diagnostic Testing** (297 products)
21. **Reagents** (5,084 products)
22. **Safety** (353 products)
23. **Specimen Collection** (339 products)
24. **Standards** (1,478 products)
25. **Storage** (238 products)
26. **Surgical Instruments** (896 products)
27. **Sutures & Suture Removal** (757 products)
28. **Thermometers, Meters & Accessories** (246 products)

### Shop By Lab
1. Cannabis Lab
2. Chemistry
3. Chromatography
4. Drug Testing/Screening
5. General Lab
6. Hematology
7. Histology And Cytology
8. Immunoassay
9. Medical/Surgical
10. Microbiology
11. Phlebotomy/Specimen Collection
12. Rapid Diagnostic Testing
13. Serology
14. Toxicology
15. Urinalysis
16. Veterinary Lab

## Product Data Structure

### Complete Product Fields

```json
{
  "id": 5734,
  "uid": "NTczNA==",
  "name": "Ansell GAMMEX® Cut-Resistant Glove Liners, Powder-Free, Small, White, Sterile (5 Pairs/Case)",
  "sku": "ANS 5789911",
  "url_key": "ansell-gammex-glove-liner-cut-resistant-small",
  "stock_status": "IN_STOCK",
  "type_id": "simple",
  "attribute_set_id": 379,
  "created_at": "2023-03-15 11:01:59",
  "updated_at": "2025-10-02 04:53:07",
  "description": {
    "html": "..."
  },
  "short_description": {
    "html": "..."
  },
  "meta_title": "...",
  "meta_keyword": null,
  "meta_description": null,
  "canonical_url": "...",
  "image": {
    "url": "https://www.mercedesscientific.com/media/catalog/product/...",
    "label": "..."
  },
  "small_image": {
    "url": "...",
    "label": "..."
  },
  "thumbnail": {
    "url": "...",
    "label": "..."
  },
  "media_gallery": [
    {
      "url": "...",
      "label": "...",
      "position": 1
    }
  ],
  "categories": [
    {
      "id": 18401,
      "uid": "MTg0MDE=",
      "name": "Gloves & Apparel",
      "url_path": "shop-by-product/gloves-apparel",
      "url_key": "gloves-apparel",
      "level": 3,
      "path": "1/2/5/18401"
    }
  ],
  "price_range": {
    "minimum_price": {
      "regular_price": {
        "value": 123.45,
        "currency": "USD"
      },
      "final_price": {
        "value": 123.45,
        "currency": "USD"
      },
      "discount": {
        "amount_off": 0,
        "percent_off": 0
      }
    },
    "maximum_price": {
      "regular_price": {
        "value": 123.45,
        "currency": "USD"
      },
      "final_price": {
        "value": 123.45,
        "currency": "USD"
      }
    }
  },
  "manufacturer": null
}
```

### Product Types
- `simple` - Standard products
- `configurable` - Products with variants (sizes, colors, etc.)

For configurable products, additional fields are available:
```json
{
  "configurable_options": [
    {
      "id": 123,
      "attribute_id": 456,
      "label": "Size",
      "position": 1,
      "values": [
        {
          "uid": "...",
          "label": "Small",
          "swatch_data": {
            "value": "#ffffff"
          }
        }
      ]
    }
  ]
}
```

## GraphQL Query Examples

### 1. Search for Products

**IMPORTANT**: The products query REQUIRES either a `search` or `filter` parameter.

```graphql
{
  products(
    search: "gloves"
    pageSize: 10
    currentPage: 1
  ) {
    total_count
    items {
      id
      uid
      name
      sku
      url_key
      stock_status
      price_range {
        minimum_price {
          regular_price {
            value
            currency
          }
        }
      }
      image {
        url
        label
      }
    }
    page_info {
      current_page
      page_size
      total_pages
    }
  }
}
```

### 2. Filter Products by Category

```graphql
{
  products(
    filter: {
      category_id: { eq: "18401" }
    }
    pageSize: 20
  ) {
    total_count
    items {
      name
      sku
      price_range {
        minimum_price {
          regular_price {
            value
            currency
          }
        }
      }
      categories {
        name
        url_path
      }
    }
  }
}
```

### 3. Filter Products by Price Range

```graphql
{
  products(
    filter: {
      price: { from: "100", to: "500" }
    }
    pageSize: 10
    sort: { price: ASC }
  ) {
    total_count
    items {
      name
      sku
      stock_status
      price_range {
        minimum_price {
          regular_price {
            value
            currency
          }
        }
      }
    }
  }
}
```

### 4. Get Category Tree

```graphql
{
  categoryList {
    id
    uid
    name
    url_path
    url_key
    children_count
    product_count
    children {
      id
      uid
      name
      url_path
      url_key
      children_count
      product_count
    }
  }
}
```

### 5. Get Product with Full Details

```graphql
{
  products(
    filter: { sku: { eq: "ANS 5789911" } }
    pageSize: 1
  ) {
    items {
      id
      uid
      name
      sku
      description {
        html
      }
      short_description {
        html
      }
      stock_status
      price_range {
        minimum_price {
          regular_price {
            value
            currency
          }
          final_price {
            value
            currency
          }
          discount {
            amount_off
            percent_off
          }
        }
      }
      image {
        url
        label
      }
      media_gallery {
        url
        label
        position
      }
      categories {
        id
        name
        url_path
      }
    }
  }
}
```

### 6. Get Product Aggregations (Filters)

When searching/filtering products, you can also get available filter options:

```graphql
{
  products(
    search: "gloves"
    pageSize: 10
  ) {
    total_count
    items {
      name
      sku
    }
    aggregations {
      attribute_code
      label
      count
      options {
        label
        value
        count
      }
    }
  }
}
```

## Integration Recommendations

### 1. Product Search Integration

For Journey AI chatbot integration, use search-based queries:

```python
def search_mercedes_products(search_term: str, page_size: int = 10) -> dict:
    """Search Mercedes Scientific products"""
    query = """
    {
      products(
        search: "%s"
        pageSize: %d
      ) {
        total_count
        items {
          id
          name
          sku
          url_key
          stock_status
          price_range {
            minimum_price {
              regular_price {
                value
                currency
              }
            }
          }
          image {
            url
            label
          }
          short_description {
            html
          }
        }
      }
    }
    """ % (search_term, page_size)

    response = requests.post(
        'https://www.mercedesscientific.com/graphql',
        json={'query': query},
        headers={'Content-Type': 'application/json'}
    )

    return response.json()
```

### 2. Category-Based Navigation

```python
def get_products_by_category(category_id: str, page_size: int = 20) -> dict:
    """Get products in a specific category"""
    query = """
    {
      products(
        filter: { category_id: { eq: "%s" } }
        pageSize: %d
        sort: { name: ASC }
      ) {
        total_count
        items {
          name
          sku
          url_key
          price_range {
            minimum_price {
              regular_price {
                value
              }
            }
          }
          image {
            url
          }
        }
        page_info {
          total_pages
        }
      }
    }
    """ % (category_id, page_size)

    response = requests.post(
        'https://www.mercedesscientific.com/graphql',
        json={'query': query},
        headers={'Content-Type': 'application/json'}
    )

    return response.json()
```

### 3. Price-Based Filtering

```python
def get_products_by_price_range(min_price: float, max_price: float) -> dict:
    """Filter products by price range"""
    query = """
    {
      products(
        filter: {
          price: { from: "%.2f", to: "%.2f" }
        }
        pageSize: 20
        sort: { price: ASC }
      ) {
        total_count
        items {
          name
          sku
          price_range {
            minimum_price {
              regular_price {
                value
                currency
              }
            }
          }
        }
      }
    }
    """ % (min_price, max_price)

    response = requests.post(
        'https://www.mercedesscientific.com/graphql',
        json={'query': query},
        headers={'Content-Type': 'application/json'}
    )

    return response.json()
```

## Important Notes

### API Requirements
1. **Filter/Search Required**: The `products` query MUST include either a `search` parameter or a `filter` parameter
2. **Content-Type**: Always use `Content-Type: application/json`
3. **POST Method**: GraphQL queries must be sent via POST
4. **Pagination**: Use `pageSize` and `currentPage` for pagination
5. **Rate Limiting**: Be mindful of API rate limits (not documented)

### Data Characteristics
- **Large Catalog**: 26,953 products total
- **Deep Category Hierarchy**: Up to 3 levels deep
- **Rich Product Data**: Includes descriptions, images, pricing, categories
- **Stock Status**: Available in product data (`IN_STOCK`, `OUT_OF_STOCK`)
- **Product Types**: Both simple and configurable products
- **Pricing**: Supports regular price, final price, and discount information

### Frontend Integration
- **Apollo Client**: The website uses Apollo Client for GraphQL
- **Client-Side Rendering**: Product data is loaded dynamically
- **Default Sorting**: `core_item_rank` is the default sort order
- **Grid Display**: 12 products per page by default

## Sample Products

Here are some example product searches with result counts:

| Search Term | Results |
|------------|---------|
| "test" | 500 |
| "gloves" | 477 |
| "pipette" | ~1,024 |
| "microscope" | varies |
| "beaker" | varies |

## Category IDs Reference

Key category IDs for filtering:

| Category | ID | Products |
|----------|------|----------|
| Products | 5 | 23,574 |
| Gloves & Apparel | 18401 | 380 |
| Pipettes, Pipettors, Tips & Accessories | 18518 | 1,024 |
| Reagents | 17807 | 5,084 |
| Chemicals & Stains | 17546 | 3,166 |
| Glass & Plasticware | 18509 | 2,206 |
| Standards | 18722 | 1,478 |

## Product URL Structure

Products have a `url_key` field that can be used to construct product URLs:

```
https://www.mercedesscientific.com/{url_key}
```

Example:
```
https://www.mercedesscientific.com/ansell-gammex-glove-liner-cut-resistant-small
```

## Next Steps for Integration

1. **Create Product Search Tool**: Implement a tool for Journey AI agents to search Mercedes products
2. **Category Navigation Tool**: Allow agents to browse by category
3. **Price Filter Tool**: Enable price-based product recommendations
4. **Product Detail Retrieval**: Get full product information for specific SKUs
5. **Stock Availability Check**: Verify product availability before recommendations
6. **Cart Integration**: Potentially integrate with cart/checkout (requires authentication)

## Testing Script

See `tmp/explore_mercedes_graphql.py` and `tmp/explore_mercedes_detailed.py` for working examples of querying the API.
