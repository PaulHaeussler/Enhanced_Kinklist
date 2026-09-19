# Adult Platform and Kinklist v2 Plan

Date: 2026-07-26

## Decision

Build ERP and Kinklist v2 in a new `adult-platform` codebase as sibling product surfaces. Keep this `Enhanced_Kinklist` repo as the legacy source/reference and preserve old public result URLs through a read-only compatibility path.

## Boundaries

- Do not build ERP inside this repo.
- Do not share a production database between ERP, Kinklist v2, and legacy Kinklist.
- Share explicit foundations only: request IDs, safe logging, retention classes, token/share conventions, export/delete interfaces, synthetic fixtures, and Security Center event contracts.
- Keep `/results?token=...` and `/<token>` working for legacy result links.
- Disable or gate legacy writes before Kinklist v2 accepts new submissions.

## Legacy Findings

- Submitted answers persist in MySQL `answers.choices_json`.
- Demographic fields and IP persist in `users`.
- Result access is bearer-token based.
- Legacy tokens were five random alphanumeric characters.
- Request logging stored raw URL/query data, which could include result tokens.
- Client error logging could include `window.location.href`.
- Local log files exist in the working tree and must stay untracked.

## First Steps

1. Patch legacy log/repo hygiene in this repo.
2. Write the repo-boundary ADR in the new adult-platform repo once created.
3. Define Kinklist v2 data model and migration posture.
4. Scaffold adult-platform with separate shared, kinklist, and ERP modules.
5. Implement a tested legacy result adapter before cutting over routes.

## Security Center Link

Tether Security Center remains the shared observability and privacy-operations surface. It should ingest structural metadata only and must not receive result bodies, message bodies, tokens, cookies, private query strings, submitted preferences, or signed URLs.
