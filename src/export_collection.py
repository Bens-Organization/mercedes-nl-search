"""Export Typesense collection to CSV."""
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import typesense

from config import Config


class CollectionExporter:
    """Export Typesense collection to CSV."""

    def __init__(self):
        """Initialize exporter."""
        Config.validate()
        self.client = typesense.Client(Config.get_typesense_config())
        self.collection_name = Config.TYPESENSE_COLLECTION_NAME

    def export_to_csv(self, output_path: str = None, max_products: int = None) -> str:
        """
        Export collection to CSV file.

        Args:
            output_path: Optional custom output path
            max_products: Optional limit on number of products to export

        Returns:
            Path to created CSV file
        """
        print(f"Exporting collection '{self.collection_name}'...")

        # Get all documents
        documents = self._fetch_all_documents(max_products)

        if not documents:
            print("No documents found in collection")
            return None

        print(f"✓ Fetched {len(documents)} documents")

        # Generate output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(__file__).parent.parent / "database"
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"mercedes_products_{timestamp}.csv"

        # Write to CSV
        self._write_csv(documents, output_path)
        print(f"✓ Exported to: {output_path}")

        return str(output_path)

    def _fetch_all_documents(self, max_products: int = None) -> List[Dict[str, Any]]:
        """
        Fetch all documents from collection.

        Args:
            max_products: Optional limit on number of products

        Returns:
            List of document dictionaries
        """
        documents = []
        page = 1
        per_page = 250  # Typesense max

        while True:
            try:
                # Export documents using the export endpoint
                # This is more efficient than searching
                search_params = {
                    "q": "*",
                    "per_page": per_page,
                    "page": page,
                }

                result = self.client.collections[self.collection_name].documents.search(
                    search_params
                )

                hits = result.get("hits", [])
                if not hits:
                    break

                for hit in hits:
                    doc = hit["document"]
                    # Remove embedding field as it's too large for CSV
                    doc.pop("embedding", None)
                    documents.append(doc)

                print(f"  Page {page}: {len(hits)} documents (Total: {len(documents)})")

                # Check if we've reached the limit
                if max_products and len(documents) >= max_products:
                    documents = documents[:max_products]
                    print(f"✓ Reached max_products limit: {max_products}")
                    break

                # Check if there are more pages
                if len(hits) < per_page:
                    break

                page += 1

            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                break

        return documents

    def _write_csv(self, documents: List[Dict[str, Any]], output_path: str):
        """
        Write documents to CSV file.

        Args:
            documents: List of document dictionaries
            output_path: Path to output CSV file
        """
        if not documents:
            return

        # Get all unique field names across all documents
        fieldnames = set()
        for doc in documents:
            fieldnames.update(doc.keys())

        # Sort for consistent ordering
        fieldnames = sorted(fieldnames)

        # Move important fields to front
        priority_fields = [
            "product_id", "uid", "sku", "name", "price", "special_price",
            "stock_status", "brand", "size", "color", "physical_form"
        ]
        ordered_fields = []
        for field in priority_fields:
            if field in fieldnames:
                ordered_fields.append(field)
                fieldnames.remove(field)
        ordered_fields.extend(sorted(fieldnames))

        # Write CSV
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=ordered_fields)
            writer.writeheader()

            for doc in documents:
                # Convert lists to comma-separated strings
                row = {}
                for key, value in doc.items():
                    if isinstance(value, list):
                        row[key] = ", ".join(str(v) for v in value)
                    else:
                        row[key] = value
                writer.writerow(row)


def main():
    """Main entry point."""
    max_products = None

    # Check for command line argument
    if len(sys.argv) > 1:
        try:
            max_products = int(sys.argv[1])
            print(f"Limiting export to {max_products} products")
        except ValueError:
            print(f"Invalid max_products argument: {sys.argv[1]}")
            sys.exit(1)

    exporter = CollectionExporter()
    output_path = exporter.export_to_csv(max_products=max_products)

    if output_path:
        print(f"\n✓ Export complete!")
        print(f"  File: {output_path}")
    else:
        print("\n✗ Export failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
