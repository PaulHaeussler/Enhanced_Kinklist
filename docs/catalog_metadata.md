# Catalog Metadata Workflow

Catalog metadata is edited through `catalog_metadata/main.csv` and imported into `enhanced_kinklist.json`.

Fields:

- `id`: stable kink row id; do not change this unless intentionally migrating content.
- `group`, `description`, `columns`: read-only context fields used to catch stale CSV edits.
- `domain`: one of `irl`, `rp`, `media`, `legacy`.
- `spice_level`: integer from `0` to `5`.
- `visibility`: one of `default`, `opt_in`, `hidden`, `blocked`.
- `flags`: optional `|`-separated machine tags, using lowercase letters, numbers, underscores, colons, or hyphens.
- `aliases`: optional `|`-separated duplicate/typo/search aliases.

Commands:

```sh
python tools/export_catalog_metadata.py --config enhanced_kinklist.json --output catalog_metadata/main.csv
python tools/import_catalog_metadata.py --config enhanced_kinklist.json --input catalog_metadata/main.csv --check
python tools/import_catalog_metadata.py --config enhanced_kinklist.json --input catalog_metadata/main.csv
python tools/validate_catalog_metadata.py --config enhanced_kinklist.json --metadata catalog_metadata/main.csv
```

Compatibility rule:

- Do not change row ids for existing items.
- If metadata changes will affect what users see, such as spice filtering, RP splits, hidden rows, or blocked rows, bump `catalog_version` and create a matching immutable catalog snapshot before deployment.
- The current metadata pass does not enable filtering yet, so `catalog_version` and `catalog_snapshots/main-2026.1.json` stay unchanged.

First-pass classification rules:

- `default`: acceptable in the normal catalog once filtering exists.
- `opt_in`: valid catalog content, but niche, intense, sensitive, privacy-affecting, or demographic enough that it should not be frontloaded.
- `hidden`: very high-risk, extreme, non-consent fantasy, public/privacy-risk, or safety-heavy content that should require explicit "everything" style access.
- `blocked`: not eligible for the public catalog, public suggestions, public stats, or autocomplete.
- `rp`: fictional, fantasy, roleplay, or scenario-first content.
- `media`: erotic media or visual trope content.
- `irl`: real-world partner traits, activities, tools, clothing, or dynamics.
