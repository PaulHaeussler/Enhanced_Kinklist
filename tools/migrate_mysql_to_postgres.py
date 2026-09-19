"""Migrate the legacy Enhanced Kinklist MySQL database into Postgres.

Deliberate omissions (see create_db_postgres.sql):
  * `hits` and `stats` are not migrated; the stats compiler is retired.
  * No IP address is carried over, from any table.
  * `users` is folded into `answers.submitter` as a per-submission snapshot.

The script is re-runnable. Rows are keyed on `answers.token` with
ON CONFLICT DO NOTHING, so a second pass only adds what is new. Use
--since with the watermark printed by the previous run to migrate just
the tail during cutover.

Usage:
  python tools/migrate_mysql_to_postgres.py \
      --mysql-host 127.0.0.1 --mysql-user kinklist --mysql-password ... \
      --mysql-database kl \
      --postgres-dsn "postgresql://kinklist_legacy:...@localhost/kinklist_legacy" \
      [--since 1750000000000] [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys

import mysql.connector
import psycopg

BATCH_SIZE = 1000

SUBMITTER_FIELDS = ("username", "sex", "age", "fap_freq", "sex_freq", "body_count", "created")


def as_json_text(value):
    """Normalize a MySQL JSON column into a string Postgres can cast to JSONB."""
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        # Validate early; a malformed row should fail loudly here, not mid-load.
        json.loads(value)
        return value
    return json.dumps(value)


def suggestion_digest(timestamp, suggestion):
    """Stable dedup key for a table that has no primary key upstream."""
    raw = f"{timestamp}\x00{suggestion}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()


def load_users(mysql_cur):
    """Return {user_id: (user_uuid, submitter_json)}. The ip column is dropped."""
    mysql_cur.execute(
        "SELECT id, `user`, username, sex, age, fap_freq, sex_freq, body_count, created FROM users;"
    )
    users = {}
    for row in mysql_cur.fetchall():
        user_id, user_uuid = row[0], row[1]
        submitter = {field: row[i + 2] for i, field in enumerate(SUBMITTER_FIELDS)}
        submitter = {k: v for k, v in submitter.items() if v is not None}
        users[user_id] = (user_uuid, json.dumps(submitter))
    return users


# Columns added by deploy/migrations/001-002, which were never applied to
# production. Missing ones fall back to the default the Postgres schema uses.
OPTIONAL_ANSWER_COLUMNS = {
    "catalog_id": "main",
    "catalog_version": "legacy",
    "max_spice_level": None,
    "shown_item_ids": None,
    "answer_context": "realistic_adult_partner",
    "partner_personas": None,
}


def table_columns(mysql_cur, table):
    mysql_cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = %s;",
        (table,),
    )
    return {r[0].lower() for r in mysql_cur.fetchall()}


def migrate_answers(mysql_cur, pg_cur, users, since, dry_run):
    present = table_columns(mysql_cur, "answers")
    optional = [c for c in OPTIONAL_ANSWER_COLUMNS if c in present]
    missing = [c for c in OPTIONAL_ANSWER_COLUMNS if c not in present]
    if missing:
        print(f"  note: answers is missing {', '.join(missing)}; using schema defaults")

    select = ["user_id", "timestamp", "token", "choices_json", "hit_count"] + optional
    where = "WHERE timestamp > %s" if since is not None else ""
    args = (since,) if since is not None else None
    mysql_cur.execute(
        f"SELECT {', '.join(select)} FROM answers {where} ORDER BY timestamp;",
        args,
    )

    insert = (
        "INSERT INTO answers (token, \"timestamp\", choices_json, hit_count, catalog_id, "
        "catalog_version, max_spice_level, shown_item_ids, answer_context, partner_personas, "
        "user_uuid, submitter, legacy_user_id) "
        "VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s) "
        "ON CONFLICT (token) DO NOTHING;"
    )

    batch, seen, watermark = [], 0, since or 0
    orphans = 0
    for row in mysql_cur:
        user_id, timestamp, token, choices_json, hit_count = row[:5]
        extra = dict(zip(optional, row[5:]))
        values = {c: extra.get(c, default) if extra.get(c) is not None else default
                  for c, default in OPTIONAL_ANSWER_COLUMNS.items()}
        catalog_id = values["catalog_id"]
        catalog_version = values["catalog_version"]
        max_spice = values["max_spice_level"]
        shown_item_ids = values["shown_item_ids"]
        answer_context = values["answer_context"]
        partner_personas = values["partner_personas"]

        user_uuid, submitter = users.get(user_id, (None, "{}"))
        if user_id not in users:
            orphans += 1

        batch.append((
            token, timestamp, as_json_text(choices_json), hit_count or 0,
            catalog_id or "main", catalog_version or "legacy", max_spice,
            as_json_text(shown_item_ids), answer_context or "realistic_adult_partner",
            as_json_text(partner_personas), user_uuid, submitter, user_id,
        ))
        seen += 1
        watermark = max(watermark, timestamp or 0)

        if len(batch) >= BATCH_SIZE:
            if not dry_run:
                pg_cur.executemany(insert, batch)
            batch.clear()

    if batch and not dry_run:
        pg_cur.executemany(insert, batch)

    return seen, watermark, orphans


def migrate_simple(mysql_cur, pg_cur, select_sql, insert_sql, transform, dry_run):
    mysql_cur.execute(select_sql)
    rows = [transform(r) for r in mysql_cur.fetchall()]
    if rows and not dry_run:
        pg_cur.executemany(insert_sql, rows)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mysql-host", required=True)
    parser.add_argument("--mysql-port", type=int, default=3306)
    parser.add_argument("--mysql-user", required=True)
    parser.add_argument("--mysql-password", required=True)
    parser.add_argument("--mysql-database", default="kl")
    parser.add_argument("--postgres-dsn", required=True)
    parser.add_argument("--since", type=int, default=None,
                        help="Only migrate answers with timestamp greater than this (ms epoch).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Read and validate everything, write nothing.")
    args = parser.parse_args()

    source = mysql.connector.connect(
        host=args.mysql_host, port=args.mysql_port, user=args.mysql_user,
        password=args.mysql_password, database=args.mysql_database,
    )
    target = psycopg.connect(args.postgres_dsn)

    try:
        mysql_cur = source.cursor()
        with target.cursor() as pg_cur:
            users = load_users(mysql_cur)
            print(f"users read:            {len(users)}")

            answers, watermark, orphans = migrate_answers(
                mysql_cur, pg_cur, users, args.since, args.dry_run
            )
            print(f"answers migrated:      {answers}")
            if orphans:
                print(f"  warning: {orphans} answer(s) had no matching users row; "
                      f"submitter left empty")

            if table_columns(mysql_cur, "catalog_snapshots"):
                snapshots = migrate_simple(
                    mysql_cur, pg_cur, "SELECT catalog_id, catalog_version, data, created FROM catalog_snapshots;",
                    "INSERT INTO catalog_snapshots (catalog_id, catalog_version, data, created) "
                    "VALUES (%s, %s, %s::jsonb, %s) "
                    "ON CONFLICT (catalog_id, catalog_version) DO NOTHING;",
                    lambda r: (r[0], r[1], as_json_text(r[2]), r[3]),
                    args.dry_run,
                )
                print(f"catalog_snapshots:     {snapshots}")
            else:
                print("catalog_snapshots:     table absent upstream, skipped")

            # ip is deliberately not selected. Production calls the text column
            # `msg`; create_db_mysql.sql calls it `suggestion`.
            sug_col = "suggestion" if "suggestion" in table_columns(mysql_cur, "suggestions") else "msg"
            suggestions = migrate_simple(
                mysql_cur, pg_cur, f"SELECT timestamp, {sug_col} FROM suggestions;",
                'INSERT INTO suggestions ("timestamp", suggestion, legacy_digest) '
                "VALUES (%s, %s, %s) "
                "ON CONFLICT (legacy_digest) DO NOTHING;",
                lambda r: (r[0], r[1], suggestion_digest(r[0], r[1])),
                args.dry_run,
            )
            print(f"suggestions:           {suggestions}")

            errors = migrate_simple(
                mysql_cur, pg_cur,
                "SELECT id, timestamp, error_type, message, user_agent, data FROM error_logs;",
                'INSERT INTO error_logs (id, "timestamp", error_type, message, user_agent, data) '
                "VALUES (%s, %s, %s, %s, %s, %s::jsonb) "
                "ON CONFLICT (id) DO NOTHING;",
                lambda r: (r[0], r[1], r[2], r[3], r[4], as_json_text(r[5])),
                args.dry_run,
            )
            print(f"error_logs:            {errors}")

        if args.dry_run:
            target.rollback()
            print("\ndry run: nothing written")
        else:
            with target.cursor() as pg_cur:
                # error_logs ids were supplied explicitly, so the identity
                # sequence still points at 1 and would collide on first write.
                pg_cur.execute(
                    "SELECT setval(pg_get_serial_sequence('error_logs', 'id'), "
                    "COALESCE((SELECT MAX(id) FROM error_logs), 1));"
                )
            target.commit()

        print(f"\nwatermark (pass --since with this for the delta run): {watermark}")
        mysql_cur.close()
    finally:
        source.close()
        target.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
