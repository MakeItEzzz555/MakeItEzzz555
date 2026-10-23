# Profile contribution telemetry

The GitHub profile README displays SVG snapshots generated from GitHub's API and refreshed automatically by GitHub Actions. No scripts or tokens run in the visitor's browser.

## Schedule and sources

- The `update-profile-stats.yml` workflow runs at 01:19, 07:19, 13:19 and 19:19 UTC, plus manual dispatch and collector/workflow updates on `main`.
- GitHub Actions cron is best-effort and can run late; the profile shows the last successful snapshot, not live, per-viewer statistics.
- GitHub REST user metadata provides followers and public repository count. Paginated public owned repositories provide stars, fork counts, license and last push. The displayed total stars received excludes forks, as before.
- GitHub GraphQL contributionsCollection provides the calendar, last-year counts, today/month/year contributions, current streak and longest streak inside the returned window.
- The telemetry generator consumes `assets/telemetry/data.json` to recreate contributions.svg and the existing flagship headers. It retains the profile styling, fonts and layout.

## Reliability

- Fetches all repository pages, not just the first 100.
- Rejects duplicate repo records, missing counters, incomplete contribution data and inconsistent repository counts instead of publishing misleading zeros.
- Regenerates and validates SVG assets, runs the unit tests, validates README image references and commits only when the snapshot differs.
- Serializes overlapping GitHub Actions runs and rebases safely if the branch advances; never force-pushes.
- API failures keep the previous committed snapshot. Inspect failures in the GitHub Actions workflow.
- GitHub privacy settings and GraphQL permissions can affect which private contributions are visible. Last-year data is not lifetime contributions.
- No third-party telemetry service or personal access token is needed for the scheduled workflow; its standard GITHUB_TOKEN is scoped for contents:write.

## Verification

Run these from the repository root:

    python3 scripts/build_telemetry_panels.py --check
    python3 -m unittest discover -s tests -v
    python3 scripts/validate_readme_images.py

Workflow URL: https://github.com/MakeItEzzz555/MakeItEzzz555/actions/workflows/update-profile-stats.yml
