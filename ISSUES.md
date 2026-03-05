# PatternScout Issue Log

Updated: 2026-03-05

## Open Issues

1. Google Custom Search API returns `403 PERMISSION_DENIED`
- Symptom: `/search` logs `This project does not have the access to Custom Search JSON API.`
- Impact: Google image source path returns zero results.
- Current mitigation: direct Pageflows fallback scraping is enabled.
- Next action: fix GCP project/API/key restrictions for `Custom Search JSON API`.

2. Text-only tag extraction can fail JSON parsing
- Symptom: backend logs `Tag extraction failed: Expecting value...`.
- Impact: tags may be missing even when screenshots are collected.
- Current mitigation: search pipeline still completes.
- Next action: harden parsing with fallback format and retry prompt.

3. Text-only metadata descriptions can be empty
- Symptom: `analysis_status=completed` but `description` may be empty.
- Impact: weaker result quality in UI.
- Next action: enforce non-empty description fallback from title/source URL.

## Recently Resolved

1. Vision model latency timeout blocked analysis
- Resolution: switched to text-only mode with `OLLAMA_USE_VISION=false` and `qwen3.5:4b`.

2. Google-only search dependency blocked all results when API failed
- Resolution: added direct Pageflows scraping fallback via Scrapling.
