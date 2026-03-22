# WORKLOG

## 2026-03-22 07:30: Phase 3 Complete — Quality & Polish

### What was done
- Fixed test_doc E2E failure (missing `mammoth` dependency in pyproject.toml)
- ANY2-9: Improved error messages for missing deps, added `any2md deps` subcommand
- Updated CLAUDE.md with new CLI flags, test counts, common.py docs
- Bumped to v0.2.0, created GitHub release, updated brew formula
- `brew upgrade roboalchemist/tap/any2md` verified at v0.2.0
- All work pushed to GitHub

### Results
- 683 unit tests passing (test_sub/test_yt skip due to missing pysubs2/mlx-audio — not errors)
- Brew formula at v0.2.0 verified working
- GOAL.md Phase 3 complete

### Current state
- Phase 3 ✅ done, Phase 4 (test coverage) next
- 9 trckr tickets total, all done

---

## 2026-03-22 06:45: CLI Standards Upgrade Complete + Cant-Stop-Wont-Stop Initiated

### What was done
- Completed 8 CLI standards tickets (ANY2-1 through ANY2-8) via parallel plow agents
- `--version` / `-V` flag added
- `--json` / `-j` output mode for all 16 converters with `--fields` filtering
- Structured JSON error output to stderr in `--json` mode
- stdout/stderr separation standardized across all converters
- Help text footer with bug report URL
- `NO_COLOR` environment variable support
- `--quiet` / `-q` flag to suppress logs
- Shell completions enabled
- llms.txt and Makefile created
- Brew formula published at `roboalchemist/tap/any2md`
- trckr project created (key: ANY2)
- Claude skill created at `~/.claude/skills/any2md/`

### Key decisions
- Used `uv` in brew formula instead of pip (resolved missing `annotated-doc` transitive dep)
- Base brew install only includes typer core; AI deps are optional add-ons
- JSON output goes to stdout, all logs/status to stderr — clean agent piping

### Current state
- 244 tests passing, 1 pre-existing failure (test_doc.py markitdown issue)
- 9,454 lines of source across 18 modules
- GOAL.md outdated — needs refresh for post-CLI-standards era
- ANY2-9 open: brew formula missing optional deps guidance
- GitHub push may need retry (SSH was flaky earlier)
