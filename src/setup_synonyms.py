"""
Typesense Synonym Setup for Mercedes Scientific Search

This script manages synonym groups for the product search.
Synonyms work at the text search level (complementing semantic embeddings).

Usage:
    python src/setup_synonyms.py              # Setup all synonyms
    python src/setup_synonyms.py --clear      # Clear all synonyms
    python src/setup_synonyms.py --list       # List current synonyms
    python src/setup_synonyms.py --test       # Test synonym matching
"""

import typesense
from config import Config
from typing import List, Dict
import sys


class SynonymManager:
    """Manages Typesense synonyms for the products collection."""

    def __init__(self):
        self.client = typesense.Client({
            'nodes': [{
                'host': Config.TYPESENSE_HOST,
                'port': Config.TYPESENSE_PORT,
                'protocol': Config.TYPESENSE_PROTOCOL
            }],
            'api_key': Config.TYPESENSE_API_KEY,
            'connection_timeout_seconds': 10
        })
        self.collection_name = 'mercedes_products'

    def get_synonym_groups(self) -> List[Dict]:
        """
        Define synonym groups for scientific/medical products.

        Each group is a set of terms that should match each other.
        Typesense will expand queries to include all synonyms.

        Categories:
        - Materials (PTFE/Teflon, PVC/vinyl, etc.)
        - Equipment (centrifuge/spinner, autoclave/sterilizer)
        - Measurements (ml/milliliter, mg/milligram)
        - Common terms (protective/safety, sterile/aseptic)
        """
        return [
            # Materials & Chemicals
            {
                "id": "ptfe-teflon",
                "synonyms": ["ptfe", "teflon", "polytetrafluoroethylene"]
            },
            {
                "id": "pvc-vinyl",
                "synonyms": ["pvc", "vinyl", "polyvinyl chloride"]
            },
            {
                "id": "pe-polyethylene",
                "synonyms": ["pe", "polyethylene", "polythene"]
            },
            {
                "id": "pp-polypropylene",
                "synonyms": ["pp", "polypropylene"]
            },
            {
                "id": "ps-polystyrene",
                "synonyms": ["ps", "polystyrene", "styrofoam"]
            },
            {
                "id": "glass-borosilicate",
                "synonyms": ["borosilicate", "pyrex", "borosilicate glass"]
            },
            {
                "id": "latex-rubber",
                "synonyms": ["latex", "natural rubber", "rubber"]
            },
            {
                "id": "nitrile-nbr",
                "synonyms": ["nitrile", "nbr", "nitrile rubber"]
            },
            {
                "id": "stainless-steel",
                "synonyms": ["stainless steel", "stainless", "steel", "ss"]
            },

            # Equipment & Instruments
            {
                "id": "centrifuge",
                "synonyms": ["centrifuge", "spinner", "microcentrifuge"]
            },
            {
                "id": "autoclave",
                "synonyms": ["autoclave", "sterilizer", "steam sterilizer"]
            },
            {
                "id": "microscope",
                "synonyms": ["microscope", "scope", "optical microscope"]
            },
            {
                "id": "pipette",
                "synonyms": ["pipette", "pipettor", "pipet", "micropipette"]
            },
            {
                "id": "beaker",
                "synonyms": ["beaker", "measuring cup", "lab beaker"]
            },
            {
                "id": "flask",
                "synonyms": ["flask", "erlenmeyer", "erlenmeyer flask"]
            },
            {
                "id": "petri-dish",
                "synonyms": ["petri dish", "petri", "culture dish", "dish"]
            },
            {
                "id": "test-tube",
                "synonyms": ["test tube", "tube", "vial", "sample tube"]
            },

            # Measurements & Units
            {
                "id": "milliliter",
                "synonyms": ["ml", "milliliter", "millilitre", "mL"]
            },
            {
                "id": "liter",
                "synonyms": ["l", "liter", "litre", "L"]
            },
            {
                "id": "milligram",
                "synonyms": ["mg", "milligram", "milligramme", "mG"]
            },
            {
                "id": "gram",
                "synonyms": ["g", "gram", "gramme", "gm"]
            },
            {
                "id": "microliter",
                "synonyms": ["ul", "microliter", "microlitre", "μl", "µl"]
            },
            {
                "id": "micrometer",
                "synonyms": ["um", "micrometer", "micron", "μm", "µm"]
            },

            # Common Product Terms
            {
                "id": "protective-safety",
                "synonyms": ["protective", "safety", "protection"]
            },
            {
                "id": "sterile-aseptic",
                "synonyms": ["sterile", "aseptic", "sterilized"]
            },
            {
                "id": "disposable-single-use",
                "synonyms": ["disposable", "single use", "single-use", "one-time"]
            },
            {
                "id": "glove-gloves",
                "synonyms": ["glove", "gloves", "hand protection"]
            },
            {
                "id": "cover-covering",
                "synonyms": ["cover", "covering", "protection", "shield"]
            },
            {
                "id": "powder-free",
                "synonyms": ["powder free", "powder-free", "powderfree", "non-powdered"]
            },
            {
                "id": "lab-laboratory",
                "synonyms": ["lab", "laboratory", "research lab"]
            },

            # Specific Product Categories
            {
                "id": "slide-microscope-slide",
                "synonyms": ["slide", "microscope slide", "glass slide", "specimen slide"]
            },
            {
                "id": "swab-applicator",
                "synonyms": ["swab", "applicator", "cotton swab", "specimen swab"]
            },
            {
                "id": "reagent-chemical",
                "synonyms": ["reagent", "chemical", "solution", "reagent solution"]
            },
            {
                "id": "filter-filtration",
                "synonyms": ["filter", "filtration", "membrane filter"]
            },
        ]

    def setup_synonyms(self) -> None:
        """Create or update all synonym groups."""
        synonym_groups = self.get_synonym_groups()

        print(f"{'='*60}")
        print(f"Setting up {len(synonym_groups)} synonym groups...")
        print(f"{'='*60}\n")

        success_count = 0
        error_count = 0

        for group in synonym_groups:
            try:
                # Try to create the synonym
                self.client.collections[self.collection_name].synonyms.upsert(
                    group['id'],
                    {
                        'synonyms': group['synonyms']
                    }
                )
                print(f"✓ {group['id']:30} → {', '.join(group['synonyms'])}")
                success_count += 1

            except Exception as e:
                print(f"✗ {group['id']:30} → Error: {e}")
                error_count += 1

        print(f"\n{'='*60}")
        print(f"✓ Success: {success_count}/{len(synonym_groups)}")
        if error_count > 0:
            print(f"✗ Errors: {error_count}")
        print(f"{'='*60}")

    def list_synonyms(self) -> None:
        """List all current synonyms."""
        try:
            synonyms = self.client.collections[self.collection_name].synonyms.retrieve()

            print(f"{'='*60}")
            print(f"Current Synonyms ({len(synonyms['synonyms'])} groups)")
            print(f"{'='*60}\n")

            for group in synonyms['synonyms']:
                print(f"ID: {group['id']}")
                print(f"   Synonyms: {', '.join(group['synonyms'])}")
                print()

        except Exception as e:
            print(f"✗ Error listing synonyms: {e}")

    def clear_synonyms(self) -> None:
        """Remove all synonym groups."""
        try:
            synonyms = self.client.collections[self.collection_name].synonyms.retrieve()

            print(f"{'='*60}")
            print(f"Clearing {len(synonyms['synonyms'])} synonym groups...")
            print(f"{'='*60}\n")

            for group in synonyms['synonyms']:
                self.client.collections[self.collection_name].synonyms[group['id']].delete()
                print(f"✓ Deleted: {group['id']}")

            print(f"\n{'='*60}")
            print(f"✓ All synonyms cleared")
            print(f"{'='*60}")

        except Exception as e:
            print(f"✗ Error clearing synonyms: {e}")

    def test_synonyms(self) -> None:
        """Test synonym matching with example queries."""
        test_queries = [
            ("ptfe gloves", "Should match Teflon products"),
            ("teflon tubing", "Should match PTFE products"),
            ("pipette tips", "Should match pipettor tips"),
            ("ml beaker", "Should match milliliter beakers"),
            ("sterile swabs", "Should match aseptic swabs"),
            ("powder-free gloves", "Should match powderfree gloves"),
        ]

        print(f"{'='*60}")
        print(f"Testing Synonym Matching")
        print(f"{'='*60}\n")

        for query, description in test_queries:
            try:
                # Simple text search to test synonym expansion
                results = self.client.collections[self.collection_name].documents.search({
                    'q': query,
                    'query_by': 'name,description,short_description',
                    'per_page': 3
                })

                print(f"Query: '{query}'")
                print(f"Note: {description}")
                print(f"Found: {results['found']} products")

                if results['found'] > 0:
                    for i, hit in enumerate(results['hits'][:3], 1):
                        doc = hit['document']
                        print(f"  {i}. {doc['name']} (SKU: {doc['sku']})")

                print()

            except Exception as e:
                print(f"✗ Error testing '{query}': {e}\n")


def main():
    """Main entry point."""
    manager = SynonymManager()

    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == '--clear':
            manager.clear_synonyms()
        elif command == '--list':
            manager.list_synonyms()
        elif command == '--test':
            manager.test_synonyms()
        else:
            print("Unknown command. Use --clear, --list, or --test")
            sys.exit(1)
    else:
        # Default: setup synonyms
        manager.setup_synonyms()


if __name__ == '__main__':
    main()
