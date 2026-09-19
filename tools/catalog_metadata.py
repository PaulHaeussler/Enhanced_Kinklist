import csv
import copy
import json
import re
from pathlib import Path


FIELDNAMES = [
    "id",
    "group",
    "description",
    "columns",
    "domain",
    "spice_level",
    "visibility",
    "flags",
    "aliases",
]

ALLOWED_DOMAINS = {"irl", "rp", "media", "legacy"}
ALLOWED_VISIBILITIES = {"default", "opt_in", "hidden", "blocked"}
MIN_SPICE_LEVEL = 0
MAX_SPICE_LEVEL = 5
LIST_SEPARATOR = "|"
FLAG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_:-]*$")

DEFAULT_CATALOG_ID = "main"
DEFAULT_CATALOG_VERSION = "legacy"
DEFAULT_DOMAIN = "irl"
DEFAULT_SPICE_LEVEL = 2
DEFAULT_VISIBILITY = "default"


class CatalogMetadataError(Exception):
    pass


def load_config(path, apply_defaults=True):
    with Path(path).open(newline="") as handle:
        config = json.load(handle)
    if apply_defaults:
        normalize_config(config)
    return config


def write_config(path, config):
    Path(path).write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")


def normalize_config(config):
    config.setdefault("catalog_id", DEFAULT_CATALOG_ID)
    config.setdefault("catalog_version", DEFAULT_CATALOG_VERSION)
    config.setdefault("default_domain", DEFAULT_DOMAIN)
    config.setdefault("default_spice_level", DEFAULT_SPICE_LEVEL)
    config.setdefault("default_visibility", DEFAULT_VISIBILITY)

    for group in config.get("kink_groups", []):
        group.setdefault("domain", config["default_domain"])
        group.setdefault("spice_level", config["default_spice_level"])
        group.setdefault("visibility", config["default_visibility"])
        group.setdefault("flags", [])
        group.setdefault("rows", [])
        group.setdefault("columns", [])

        for row in group["rows"]:
            row.setdefault("domain", group["domain"])
            row.setdefault("spice_level", group["spice_level"])
            row.setdefault("visibility", group["visibility"])
            row.setdefault("flags", list(group["flags"]))
            row.setdefault("aliases", [])


def iter_items(config):
    for group_index, group in enumerate(config.get("kink_groups", [])):
        for row_index, row in enumerate(group.get("rows", [])):
            yield group_index, row_index, group, row


def serialize_list(values):
    if values is None:
        return ""
    return LIST_SEPARATOR.join(str(value).strip() for value in values if str(value).strip())


def parse_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(LIST_SEPARATOR) if item.strip()]


def parse_spice_level(value, source):
    try:
        spice_level = int(value)
    except (TypeError, ValueError):
        raise CatalogMetadataError(f"{source}: spice_level must be an integer")
    if spice_level < MIN_SPICE_LEVEL or spice_level > MAX_SPICE_LEVEL:
        raise CatalogMetadataError(
            f"{source}: spice_level must be between {MIN_SPICE_LEVEL} and {MAX_SPICE_LEVEL}"
        )
    return spice_level


def validate_metadata(domain, spice_level, visibility, flags, aliases, source):
    if domain not in ALLOWED_DOMAINS:
        raise CatalogMetadataError(
            f"{source}: domain must be one of {sorted(ALLOWED_DOMAINS)}, got {domain!r}"
        )

    parse_spice_level(spice_level, source)

    if visibility not in ALLOWED_VISIBILITIES:
        raise CatalogMetadataError(
            f"{source}: visibility must be one of {sorted(ALLOWED_VISIBILITIES)}, got {visibility!r}"
        )

    for flag in flags:
        if not FLAG_PATTERN.match(flag):
            raise CatalogMetadataError(
                f"{source}: flag {flag!r} must use lowercase letters, numbers, underscores, colons, or hyphens"
            )
        if len(flag) > 64:
            raise CatalogMetadataError(f"{source}: flag {flag!r} is longer than 64 characters")

    for alias in aliases:
        if "\n" in alias or "\r" in alias:
            raise CatalogMetadataError(f"{source}: aliases must not contain newlines")
        if len(alias) > 120:
            raise CatalogMetadataError(f"{source}: alias {alias!r} is longer than 120 characters")


def validate_config(config):
    errors = []
    ids = set()

    try:
        validate_metadata(
            config.get("default_domain", DEFAULT_DOMAIN),
            config.get("default_spice_level", DEFAULT_SPICE_LEVEL),
            config.get("default_visibility", DEFAULT_VISIBILITY),
            [],
            [],
            "catalog defaults",
        )
    except CatalogMetadataError as error:
        errors.append(str(error))

    for group_index, row_index, group, row in iter_items(config):
        source = f"row id {row.get('id', '<missing>')} ({group.get('description', 'group ' + str(group_index))})"
        row_id = str(row.get("id", "")).strip()
        if not row_id:
            errors.append(f"{source}: missing id")
        elif row_id in ids:
            errors.append(f"{source}: duplicate id {row_id}")
        else:
            ids.add(row_id)

        try:
            validate_metadata(
                row.get("domain"),
                row.get("spice_level"),
                row.get("visibility"),
                parse_list(row.get("flags")),
                parse_list(row.get("aliases")),
                source,
            )
        except CatalogMetadataError as error:
            errors.append(str(error))

    if errors:
        raise CatalogMetadataError("\n".join(errors))


def csv_rows_from_config(config):
    rows = []
    for _, _, group, row in iter_items(config):
        rows.append({
            "id": str(row["id"]),
            "group": group.get("description", ""),
            "description": row.get("description", ""),
            "columns": "; ".join(group.get("columns", [])),
            "domain": row.get("domain", DEFAULT_DOMAIN),
            "spice_level": str(row.get("spice_level", DEFAULT_SPICE_LEVEL)),
            "visibility": row.get("visibility", DEFAULT_VISIBILITY),
            "flags": serialize_list(row.get("flags", [])),
            "aliases": serialize_list(row.get("aliases", [])),
        })
    return rows


def write_metadata_csv(path, rows):
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def load_metadata_csv(path):
    csv_path = Path(path)
    with csv_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDNAMES:
            raise CatalogMetadataError(
                f"{csv_path}: expected CSV header {FIELDNAMES}, got {reader.fieldnames}"
            )

        rows = {}
        for line_number, row in enumerate(reader, start=2):
            source = f"{csv_path}:{line_number} id {row.get('id', '<missing>')}"
            row_id = str(row.get("id", "")).strip()
            if not row_id:
                raise CatalogMetadataError(f"{source}: missing id")
            if row_id in rows:
                raise CatalogMetadataError(f"{source}: duplicate id {row_id}")

            flags = parse_list(row.get("flags"))
            aliases = parse_list(row.get("aliases"))
            spice_level = parse_spice_level(row.get("spice_level"), source)
            domain = str(row.get("domain", "")).strip()
            visibility = str(row.get("visibility", "")).strip()
            validate_metadata(domain, spice_level, visibility, flags, aliases, source)

            rows[row_id] = {
                "id": row_id,
                "group": row.get("group", ""),
                "description": row.get("description", ""),
                "columns": row.get("columns", ""),
                "domain": domain,
                "spice_level": spice_level,
                "visibility": visibility,
                "flags": flags,
                "aliases": aliases,
            }

    return rows


def config_rows_by_id(config):
    return {row["id"]: row for row in csv_rows_from_config(config)}


def validate_csv_matches_config(config, metadata_rows):
    config_rows = config_rows_by_id(config)
    config_ids = set(config_rows)
    metadata_ids = set(metadata_rows)
    errors = []

    missing = sorted(config_ids - metadata_ids, key=sort_id)
    extra = sorted(metadata_ids - config_ids, key=sort_id)
    if missing:
        errors.append(f"metadata CSV is missing ids: {', '.join(missing[:20])}")
    if extra:
        errors.append(f"metadata CSV has unknown ids: {', '.join(extra[:20])}")

    for row_id in sorted(config_ids & metadata_ids, key=sort_id):
        config_row = config_rows[row_id]
        metadata_row = metadata_rows[row_id]
        for field in ["group", "description", "columns", "domain", "visibility"]:
            if str(config_row[field]) != str(metadata_row[field]):
                errors.append(
                    f"id {row_id}: CSV {field} {metadata_row[field]!r} does not match catalog {config_row[field]!r}"
                )
        if int(config_row["spice_level"]) != int(metadata_row["spice_level"]):
            errors.append(
                f"id {row_id}: CSV spice_level {metadata_row['spice_level']!r} does not match catalog {config_row['spice_level']!r}"
            )
        if parse_list(config_row["flags"]) != metadata_row["flags"]:
            errors.append(f"id {row_id}: CSV flags do not match catalog flags")
        if parse_list(config_row["aliases"]) != metadata_row["aliases"]:
            errors.append(f"id {row_id}: CSV aliases do not match catalog aliases")

    if errors:
        raise CatalogMetadataError("\n".join(errors))


def apply_metadata(config, metadata_rows):
    rows_by_id = {}
    for group_index, row_index, group, row in iter_items(config):
        rows_by_id[str(row["id"])] = (group, row)

    config_ids = set(rows_by_id)
    metadata_ids = set(metadata_rows)
    missing = sorted(config_ids - metadata_ids, key=sort_id)
    extra = sorted(metadata_ids - config_ids, key=sort_id)
    if missing or extra:
        errors = []
        if missing:
            errors.append(f"metadata CSV is missing ids: {', '.join(missing[:20])}")
        if extra:
            errors.append(f"metadata CSV has unknown ids: {', '.join(extra[:20])}")
        raise CatalogMetadataError("\n".join(errors))

    for row_id, metadata in metadata_rows.items():
        group, row = rows_by_id[row_id]

        expected_group = group.get("description", "")
        expected_description = row.get("description", "")
        expected_columns = "; ".join(group.get("columns", []))
        if metadata["group"] != expected_group:
            raise CatalogMetadataError(f"id {row_id}: stale group in metadata CSV")
        if metadata["description"] != expected_description:
            raise CatalogMetadataError(f"id {row_id}: stale description in metadata CSV")
        if metadata["columns"] != expected_columns:
            raise CatalogMetadataError(f"id {row_id}: stale columns in metadata CSV")

        set_metadata_value(
            row,
            "domain",
            metadata["domain"],
            group.get("domain", config.get("default_domain", DEFAULT_DOMAIN)),
        )
        set_metadata_value(
            row,
            "spice_level",
            metadata["spice_level"],
            group.get("spice_level", config.get("default_spice_level", DEFAULT_SPICE_LEVEL)),
        )
        set_metadata_value(
            row,
            "visibility",
            metadata["visibility"],
            group.get("visibility", config.get("default_visibility", DEFAULT_VISIBILITY)),
        )
        set_metadata_value(row, "flags", metadata["flags"], group.get("flags", []))
        set_metadata_value(row, "aliases", metadata["aliases"], [])


def normalized_copy(config):
    result = copy.deepcopy(config)
    normalize_config(result)
    return result


def set_metadata_value(row, field, value, inherited):
    if value == inherited:
        row.pop(field, None)
    else:
        row[field] = value


def sort_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return str(value)
