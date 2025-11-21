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
from src.config import Config
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
        self.collection_name = Config.TYPESENSE_COLLECTION_NAME

    def get_synonym_groups(self) -> List[Dict]:
        """
        Define synonym groups based on Magento Live Search production configuration.

        Source: Production Magento Live Search synonyms (63 groups)
        Enhanced with:
        - JAI-2191: kimwipes ⟷ sciswipe (private label alternative)
        - JAI-2164: parafin ⟷ paraffin (trademark spelling)
        - Restored: slide ⟷ microscope slide ⟷ glass slide ⟷ specimen slide

        Total: 63 synonym groups

        Categories:
        - Medical/Drug Testing (THC, COC, AMP, etc.)
        - Lab Equipment & Supplies (vaccutainer, commode hat, etc.)
        - Medical Supplies (charged slides, cassettes, etc.)
        - Chemicals (isopropyl alcohol, gluteraldehyde, etc.)
        - Mounting & Staining (OCT, mounting media, etc.)
        - Medical Tape Types (durapore, micropore, transpore)
        - Specimen Collection (POC, multistix, etc.)
        """
        return [
            # Medical/Drug Testing Acronyms
            {
                "id": "6-mam-heroin",
                "synonyms": ["6-MAM", "6MAM", "Heroin"]
            },
            {
                "id": "amp-amphetamine",
                "synonyms": ["AMP", "Amphetamine"]
            },
            {
                "id": "bar-barbiturates",
                "synonyms": ["BAR", "Barbiturates"]
            },
            {
                "id": "bup-buprenorphine",
                "synonyms": ["BUP", "Suboxone", "Buprenorphine"]
            },
            {
                "id": "coc-cocaine",
                "synonyms": ["COC", "Cocaine"]
            },
            {
                "id": "cr-creatinine",
                "synonyms": ["CR", "Creatinine"]
            },
            {
                "id": "etg-alcohol",
                "synonyms": ["ETG", "Alcohol"]
            },
            {
                "id": "fty-fentanyl",
                "synonyms": ["FTY", "FEN", "Fentanyl"]
            },
            {
                "id": "k2-synthetic-marijuana",
                "synonyms": ["K2", "K2 Spice", "Synthetic Marijuana"]
            },
            {
                "id": "mamp-methamphetamine",
                "synonyms": ["MAMP", "Methamphetamine", "MET"]
            },
            {
                "id": "mdma-ecstasy",
                "synonyms": ["MDMA", "Ecstasy"]
            },
            {
                "id": "mtd-methadone",
                "synonyms": ["MTD", "Methadone", "EDDP"]
            },
            {
                "id": "ni-nitrate",
                "synonyms": ["NI", "Nitrate"]
            },
            {
                "id": "nicotine-cotinine",
                "synonyms": ["Nicotine", "Cotinine", "Tobacco", "COT"]
            },
            {
                "id": "opi2000-opiates",
                "synonyms": ["OPI2000", "OPI", "Opiates"]
            },
            {
                "id": "opi300-morphine",
                "synonyms": ["OPI300", "MOP", "Morphine", "MOR"]
            },
            {
                "id": "ox-oxidants",
                "synonyms": ["OX", "Oxidants"]
            },
            {
                "id": "oxy-oxycodone",
                "synonyms": ["OXY", "Oxycodone"]
            },
            {
                "id": "pcp-phencyclidine",
                "synonyms": ["PCP", "Phencyclidine"]
            },
            {
                "id": "ppx-propoxyphene",
                "synonyms": ["PPX", "Propoxyphene"]
            },
            {
                "id": "sg-specific-gravity",
                "synonyms": ["SG", "Specific Gravity"]
            },
            {
                "id": "tca-tricyclic-antidepressants",
                "synonyms": ["TCA", "Tricyclic Antidepressants"]
            },
            {
                "id": "thc-marijuana",
                "synonyms": ["THC", "Marijuana"]
            },
            {
                "id": "tra-tramadol",
                "synonyms": ["TRA", "Tramadol"]
            },
            {
                "id": "poc-drug-test",
                "synonyms": ["POC", "UDS", "Drug Test", "DOA"]
            },

            # Lab Equipment & Supplies
            {
                "id": "block-trimmer",
                "synonyms": ["block trimmer", "wax trimmer", "paraffin trimmer"]
            },
            {
                "id": "chuck-pad",
                "synonyms": ["Chuck Pad", "Under Pad"]
            },
            {
                "id": "chuck-specimen-disc",
                "synonyms": ["chuck", "specimen disc", "disc"]
            },
            {
                "id": "coban-cohesive-bandage",
                "synonyms": ["coban", "cohesive bandage"]
            },
            {
                "id": "commode-hat",
                "synonyms": ["commode hat", "urine hat", "nun hat", "pee hat", "commode collection", "specimen hat"]
            },
            {
                "id": "heating-block",
                "synonyms": ["heating block", "dry bath", "heater block"]
            },
            {
                "id": "pipette",
                "synonyms": ["pipette", "pipet", "pipettor", "pipetter"]
            },
            {
                "id": "sphygmomanometer",
                "synonyms": ["Sphygmomanometer", "BP cuff", "Cuff", "pressure cuff"]
            },
            {
                "id": "vaccutainer-holder",
                "synonyms": ["vaccutainer holder", "hub", "needle holder", "needle protector"]
            },
            {
                "id": "vaccutainer-needle",
                "synonyms": ["vaccutainer needle", "Eclipse needle"]
            },
            {
                "id": "vaccutainer-tube",
                "synonyms": ["vaccutainer tube", "vacuette tube", "draw tube", "blood draw"]
            },
            {
                "id": "vortex-mixer",
                "synonyms": ["vortex", "mixer"]
            },

            # Medical Supplies
            {
                "id": "aerosol-barrier",
                "synonyms": ["aerosol barrier", "filter tip"]
            },
            {
                "id": "card-dip",
                "synonyms": ["Card", "Dip"]
            },
            {
                "id": "cassette-block",
                "synonyms": ["Cassette", "block"]
            },
            {
                "id": "charged-slide",
                "synonyms": ["Charged Slide", "Adhesive Slide", "Plus Slide", "positively charged"]
            },
            {
                "id": "coverglass",
                "synonyms": ["Coverglass", "Cover slip", "Cover Glass", "Coverslip"]
            },
            {
                "id": "coverslipping-film",
                "synonyms": ["coverslipping film", "coverslipping tape"]
            },
            {
                "id": "embedding-mold",
                "synonyms": ["embedding mold", "base mold"]
            },
            {
                "id": "finger-stick",
                "synonyms": ["finger stick", "lancet"]
            },
            {
                "id": "multistix",
                "synonyms": ["multistix", "urine strip"]
            },
            {
                "id": "red-gray-tiger-top",
                "synonyms": ["red/gray", "tiger top"]
            },
            {
                "id": "slide-microscope-slide",
                "synonyms": ["slide", "microscope slide", "glass slide", "specimen slide"]
            },
            {
                "id": "slide-marker",
                "synonyms": ["slide marker", "marking pen"]
            },

            # Chemicals
            {
                "id": "gluteraldehyde",
                "synonyms": ["Gluteraldehyde", "GL"]
            },
            {
                "id": "isopropyl-alcohol",
                "synonyms": ["isopropyl alcohol", "isopropanol", "2-propanol", "2propanol"]
            },
            {
                "id": "methylene-chloride",
                "synonyms": ["Methylene Chloride", "Dichloromethane", "CH₂Cl₂"]
            },
            {
                "id": "trichloromethane",
                "synonyms": ["Trichloromethane", "chloroform", "CHCl₃"]
            },

            # Mounting & Staining
            {
                "id": "dye-ink",
                "synonyms": ["dye", "ink"]
            },
            {
                "id": "margin-marker",
                "synonyms": ["margin marker", "tissue marking dye"]
            },
            {
                "id": "mounting-media",
                "synonyms": ["mounting media", "coverslip media"]
            },
            {
                "id": "oct-freezing-medium",
                "synonyms": ["OCT", "Freezing Medium", "Tissue freezing"]
            },
            {
                "id": "tissue-bath",
                "synonyms": ["tissue bath", "water bath", "waterbath"]
            },

            # Medical Tape Types
            {
                "id": "durapore-silk-tape",
                "synonyms": ["durapore", "Silk Tape", "Cloth Tape"]
            },
            {
                "id": "micropore-paper-tape",
                "synonyms": ["micropore", "Paper Tape"]
            },
            {
                "id": "transpore-transparent-tape",
                "synonyms": ["transpore", "transparent tape"]
            },

            # Wipes (Enhanced with JAI-2191 fix)
            {
                "id": "kimwipes-sciswipe",
                "synonyms": ["kimwipe", "kim wipe", "wipe", "sciswipe", "delicate task wipes"]
            },

            # Trademark Spelling Variations (JAI-2164 fix)
            {
                "id": "parafin-paraffin",
                "synonyms": ["parafin", "paraffin"]
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
