# Enhanced Kinklist Catalog Roadmap

This roadmap tracks the move from one rigid list toward versioned catalogs, safer moderation, custom private entries, and separate real-life and RP/fantasy experiences.

## Progress

- [x] Draft roadmap and save it in-repo.
- [x] Phase 1 foundation: catalog id/version/default metadata and runtime item defaults.
- [x] Phase 1 tooling: CSV export/import/validation for catalog metadata.
- [x] Phase 1 first-pass content classification: assign domain/spice/visibility/flags/aliases to catalog rows.
- [ ] Phase 1 review pass: refine classifications after manual/product review.
- [x] Phase 2 foundation: schema and code support for catalog context on submitted results.
- [x] Phase 2 compatibility: immutable catalog snapshots for result rendering.
- [ ] Phase 2 deployment: run the catalog-context DB migration on the live database.
- [ ] Phase 2 deployment: run the catalog-snapshots DB migration on the live database.
- [ ] Phase 3: Add spice filtering.
- [ ] Phase 4: Split RP/fantasy catalog.
- [ ] Phase 5: Slim down the main list.
- [x] Phase 6 foundation: default partner definition, advanced context selector, and persona storage.
- [ ] Phase 6 follow-up: persona-aware answering for selected categories/items.
- [ ] Phase 7: Add private custom user entries.
- [ ] Phase 8: Build custom-entry aggregation pipeline.
- [ ] Phase 9: Add moderation/review workflow.
- [ ] Phase 10: Rework stats around filtered/versioned catalogs.
- [ ] Phase 11: Improve usability around search, progress, compare, and export.

## Moderation Line

The public catalog should not include or aggregate sexualized-minor content, even in fictional framing. Private user-defined text can be stored as private result data later, but anything in this category should be blocked from public catalog promotion, public suggestions, public stats, and public autocomplete.

## Phase 1: Stabilize The Catalog Model

Goal: make the current list describable before changing behavior.

Add metadata fields to each catalog item:

```json
{
  "id": 1234,
  "description": "...",
  "tip": "...",
  "domain": "irl",
  "spice_level": 2,
  "visibility": "default",
  "flags": ["pain", "power_exchange"],
  "aliases": ["alternate wording", "common typo"]
}
```

Suggested values:

- `domain`: `irl`, `rp`, `media`, `legacy`
- `spice_level`: `0-5`
- `visibility`: `default`, `opt_in`, `hidden`, `blocked`
- `flags`: searchable/moderation tags
- `aliases`: duplicate matching and future custom-entry clustering

Implementation notes:

- Add defaults at config-load time so existing JSON remains valid.
- Add top-level catalog metadata: `catalog_id`, `catalog_version`, `default_domain`, `default_spice_level`, `default_visibility`.
- Do not require every row to be manually annotated before the app still runs.
- Use `catalog_metadata/main.csv` plus the tools in `tools/` for content classification.
- Treat `group`, `description`, and `columns` in the CSV as read-only context fields; the importer uses them to catch stale CSV edits.

## Phase 2: Catalog Versions

Goal: stop result links from depending on today's JSON forever.

Store with each submitted result:

- `catalog_id`
- `catalog_version`
- selected `max_spice_level`
- `shown_item_ids`

This matters because filtering changes what "completion" means.

Implementation notes:

- Add schema columns without changing old `choices_json`.
- Stop using `SELECT *` for result reads so future answer columns do not break index offsets.
- For now, `shown_item_ids` can include all current item ids until filtering exists.
- Keep immutable catalog snapshots keyed by `catalog_id` and `catalog_version`.
- Result and compare pages must render from the stored/versioned catalog snapshot, not whatever the current quiz JSON says today.
- Do not overwrite an existing catalog snapshot for the same id/version; bump `catalog_version` for content edits that change result meaning.

## Phase 3: Spice Filtering

Goal: slim the experience down without deleting content.

Add a first-screen preference:

- Standard
- Spicy
- Everything visible
- Customize

Behavior:

- show rows with `spice_level <= selected level`
- hide `opt_in` rows behind "show more"
- never show `blocked`
- skipped-by-filter rows do not count as unanswered

Also add category-level helpers:

- skip remaining items in this category
- hide harder items like this
- show all in this category

## Phase 4: RP / Fantasy Split

Goal: stop mixing real-world preferences with fictional/RP/media preferences.

Create multiple catalogs:

- `main` or `irl`
- `rp`
- possibly `media`

Same codebase, different catalog env/config:

```env
CATALOG=main
```

For `rp.kinkli.st`, run the same app with:

```env
CATALOG=rp
```

Stats and result links should be catalog-specific.

## Phase 5: Slim Down Main List

Goal: make the default list less exhausting.

Use metadata to move content:

- obvious RP/media items to RP catalog
- niche/high-friction items to `opt_in`
- unsafe/problematic public entries to `blocked`
- duplicate/near-duplicate items merged via `aliases`

Keep old IDs where possible for compatibility. Deprecated items can remain readable in old results but not appear in new quizzes.

## Phase 6: Answer Context And Partner Personas

Goal: keep the default flow simple while letting users define what "partner" means for their result.

Default definition:

> Answer for a consenting adult partner you would realistically choose for this activity, not necessarily your current partner.

For "have tried" answers:

> If you have tried it with any consenting adult partner, answer from your overall experience.

Advanced start options:

- choose a different answer context, e.g. current partner, past/best overall, fantasy/RP partner, custom personas
- define optional partner personas before starting
- keep this optional and collapsed by default

Initial implementation:

- [x] Store `answer_context` with each result.
- [x] Store optional `partner_personas` with each result.
- [x] Add collapsed advanced options at the start/meta screen.
- [x] Keep the first pass result-level only, without per-persona quiz duplication.
- [x] Do not include persona-specific data in public stats.

Future implementation:

- Allow selected categories/items to be answered per persona.
- Limit persona count in normal UI, e.g. 1-3 personas.
- Keep persona-specific aggregation private until a moderation/statistics model exists.

## Phase 7: Custom User Entries

Goal: let people represent themselves without forcing every niche into the public list.

Add private custom entries:

- user enters label plus optional note
- chooses category/domain
- answers it like a normal row
- stored inside that result only

Possible DB shape:

- `custom_items`
- `custom_answers`
- or embedded in `answers.choices_json` with `custom: true`

Do not show custom entries globally yet.

## Phase 8: Custom Aggregation Pipeline

Goal: learn from repeated custom entries without letting unsafe or low-quality text leak public.

Pipeline:

1. Normalize text.
2. Remove punctuation/casing noise.
3. Alias/fuzzy match known catalog entries.
4. Cluster similar customs.
5. Apply blocklist/moderation flags.
6. Require threshold, e.g. 5-10 distinct users.
7. Admin review before public promotion.

Output:

- suggested catalog additions
- duplicate candidates
- typo/alias candidates

## Phase 9: Moderation / Admin Review

Goal: make controversial content manageable instead of hardcoded chaos.

Add a small admin-only review workflow:

- pending custom clusters
- suggestion inbox
- mark as `approved`, `alias`, `blocked`, `needs rewrite`
- assign domain/spice/flags

Even a CSV-export/import workflow is acceptable at first.

## Phase 10: Stats Rework

Goal: stats stay correct after filtering/custom catalogs.

Stats should aggregate by:

- catalog id
- catalog version
- domain
- spice level
- only fields actually shown to that user

Homepage stats should stay broad and safe:

- total submitted results
- average completion
- top public/default items
- top opt-in items only if safe
- no blocked/custom-private data

## Phase 11: UX Improvements

Once the data model is sane:

- search/filter inside quiz
- compact mode
- progress by category
- resume by unfinished category
- export image options: compact/full, filtered/all
- compare UI that supports 2-4 tokens without manual URL editing

## Current Work Notes

- Phase 1 foundation is implemented with top-level catalog metadata in `enhanced_kinklist.json` and runtime defaults for rows/groups that do not yet have metadata.
- Phase 2 foundation is implemented with new `answers` columns for `catalog_id`, `catalog_version`, `max_spice_level`, and `shown_item_ids`.
- Result/compare reads now use explicit columns instead of `SELECT *`, so future answer columns should not shift template indexes.
- Result/compare rendering now resolves rows and choices through immutable catalog snapshots when available, with `catalog_snapshots/main-2026.1.json` as the repo fallback for existing legacy-style results.
- Migrations exist at `deploy/migrations/001_answers_catalog_context.sql`, `deploy/migrations/002_answers_partner_context.sql`, and `deploy/migrations/003_catalog_snapshots.sql`.
- Partner context/persona foundation is implemented at result level; per-persona answering is still future work.
- Catalog metadata tooling exists in `tools/`, with `catalog_metadata/main.csv` as the editable working CSV and CI validation for metadata drift.
- Catalog rows have first-pass metadata: 168 `default`, 113 `opt_in`, 32 `hidden`, and 2 `blocked`; filtering is still not enabled.
- `answers.shown_item_ids` records all configured rows until filtering exists, so metadata prep does not claim hidden/blocked rows were absent from the current UI.
- The current pass intentionally does not visibly change quiz behavior yet.
