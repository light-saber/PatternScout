# PatternScout Issue Log

Updated: 2026-03-06

## Open Issues

1. Google Custom Search API returns `403 PERMISSION_DENIED`
- Symptom: `/search` logs `This project does not have the access to Custom Search JSON API.`
- Impact: Google image source path returns zero results.
- Current mitigation: direct Pageflows fallback scraping is enabled.
- Next action: fix GCP project/API/key restrictions for `Custom Search JSON API`.

2. Retrieval quality remains biased toward fallback sources
- Symptom: search results can over-index on Pageflows mobile app flows when Google search is unavailable.
- Impact: relevance is inconsistent for broader web/UI pattern queries.
- Current mitigation: query variant expansion, relevance scoring, and app-store filtering are enabled.
- Next action: restore Google search, add an additional source, and improve ranking.

3. Ollama connectivity can still be intermittent during local runs
- Symptom: local model calls may fail temporarily even when models are installed.
- Impact: heuristic analysis/tags may replace richer LLM output.
- Current mitigation: deterministic metadata and hybrid fallbacks keep jobs usable.
- Next action: stabilize Ollama runtime and add health visibility in the UI.

## Sprint 3 Tracker

1. Comparison view for selected screenshots
- Goal: let PMs compare 2-4 patterns side by side with title, source, tags, and description.
- Status: not started.

2. Export results and hybrid ideas
- Goal: export selected patterns and summaries as JSON or markdown.
- Status: not started.

3. Retrieval quality hardening
- Goal: reduce fallback-source bias and improve query relevance.
- Status: in progress via heuristics; blocked on Google `403`.

## Recently Resolved

1. Vision model latency timeout blocked analysis
- Resolution: switched to text-only mode with `OLLAMA_USE_VISION=false` and `qwen3.5:4b`.

2. Google-only search dependency blocked all results when API failed
- Resolution: added direct Pageflows scraping fallback via Scrapling.

3. Text-only tag extraction and metadata descriptions could leave completed jobs unusable
- Resolution: added deterministic metadata descriptions, fallback tags, and hybrid fallback output.

4. Results view could not reliably load a newly selected job
- Resolution: frontend state now scopes loaded results and generated hybrid output to the active job.
