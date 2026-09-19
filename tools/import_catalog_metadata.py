#!/usr/bin/env python3
import argparse
import copy

from catalog_metadata import (
    apply_metadata,
    load_config,
    load_metadata_csv,
    normalized_copy,
    validate_config,
    validate_csv_matches_config,
    write_config,
)


def main():
    parser = argparse.ArgumentParser(description="Import catalog row metadata from CSV.")
    parser.add_argument("--config", default="enhanced_kinklist.json", help="Catalog JSON path.")
    parser.add_argument("--input", default="catalog_metadata/main.csv", help="Input CSV path.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate CSV against the catalog without writing JSON.",
    )
    args = parser.parse_args()

    config = load_config(args.config, apply_defaults=False)
    effective_config = normalized_copy(config)
    validate_config(effective_config)
    metadata_rows = load_metadata_csv(args.input)

    if args.check:
        validate_csv_matches_config(effective_config, metadata_rows)
        print(f"{args.input} matches {args.config}")
        return

    original_config = copy.deepcopy(config)
    apply_metadata(config, metadata_rows)
    validate_config(normalized_copy(config))
    if config == original_config:
        print(f"No metadata changes needed for {args.config}")
        return

    write_config(args.config, config)
    print(f"Updated {args.config} from {args.input}")


if __name__ == "__main__":
    main()
