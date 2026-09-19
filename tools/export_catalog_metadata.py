#!/usr/bin/env python3
import argparse

from catalog_metadata import csv_rows_from_config, load_config, validate_config, write_metadata_csv


def main():
    parser = argparse.ArgumentParser(description="Export catalog row metadata to CSV.")
    parser.add_argument("--config", default="enhanced_kinklist.json", help="Catalog JSON path.")
    parser.add_argument("--output", default="catalog_metadata/main.csv", help="Output CSV path.")
    args = parser.parse_args()

    config = load_config(args.config)
    validate_config(config)
    write_metadata_csv(args.output, csv_rows_from_config(config))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
