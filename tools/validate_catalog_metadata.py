#!/usr/bin/env python3
import argparse

from catalog_metadata import (
    load_config,
    load_metadata_csv,
    validate_config,
    validate_csv_matches_config,
)


def main():
    parser = argparse.ArgumentParser(description="Validate catalog metadata.")
    parser.add_argument("--config", default="enhanced_kinklist.json", help="Catalog JSON path.")
    parser.add_argument("--metadata", default=None, help="Optional metadata CSV path.")
    args = parser.parse_args()

    config = load_config(args.config)
    validate_config(config)

    if args.metadata:
        metadata_rows = load_metadata_csv(args.metadata)
        validate_csv_matches_config(config, metadata_rows)

    print("Catalog metadata OK")


if __name__ == "__main__":
    main()
