# PatternScout — PRD v0.1

## 1. Problem Statement
Product managers researching UX patterns waste time:
- Manually browsing Dribbble, Mobbin, Google Images
- Screenshots scattered across folders without context
- No systematic way to compare patterns or generate alternatives

## 2. Target User
**Primary:** Product Managers (Walmart internal)
- Needs: Validate assumptions, competitive analysis, ideation
- Context: Evaluating variant selection, checkout flows, onboarding

**Secondary:** UX Designers

## 3. Functional Requirements

### 3.1 Input
- Text search: "e-commerce variant selection"
- Optional: Upload reference image for "similar to this"

### 3.2 Scraping

**Primary Sources:**
- **Google Images API** — broad coverage, free tier 100 queries/day, no rate limiting concerns
- **Page Flows** — UX-focused screenshot library (check accessibility)
- **Screenlane** — filterable by pattern/industry

**Deferred Sources:**
- **Mobbin** — no official API; Cloudflare-protected; high block risk (post-MVP)
- **App Store / Play Store** — official screenshots (future sprint)
- **GoodUI / UI Garage** — curated patterns (evaluate for v2)

**Strategy:** Cache aggressively (SQLite); min 1 hour between re-scraping same query.

### 3.3 Analysis (Qwen2.5-VL)
For each image:
- Describe UI pattern in structured format
- Extract visible text (OCR)
- Tag: component type, layout, interaction pattern
- Confidence score

### 3.4 Clustering
- Group similar patterns automatically
- Surface: "12 examples use dropdowns"
- Surface: "8 examples use visual swatches"

### 3.5 Hybrid Generation (Qwen 3.5)
- Blend 2-3 real patterns into novel approach
- Constrained to feasible UI (no fantasy)
- Output: description + wireframe prompt

### 3.6 Output
- Grid view with filters (by tag, source, date)
- Side-by-side comparison mode
- Export: JSON, markdown, or image zip

## 4. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Search-to-result time | < 30 seconds for 20 images |
| Local inference | No cloud API required |
| Storage | SQLite, < 1GB for 1000 images |
| Privacy | All data stays local |
| Deploy | Single Docker container |

## 5. Technical Architecture

```
┌─────────────────────────────────────────────────────────┐
│  FastAPI Backend                                        │
│  ├── /search → trigger scraping                         │
│  ├── /analyze → Qwen2.5-VL inference                   │
│  ├── /cluster → pattern grouping                        │
│  └── /hybrid → blend patterns                           │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌─────────┐      ┌──────────┐      ┌──────────┐
   │Scrapling│      │Ollama    │      │SQLite    │
   │(Google, │      │• Qwen2.5-VL│     │• images  │
   │ Mobbin) │      │• Qwen 3.5 │      │• tags    │
   └─────────┘      └──────────┘      │• embeddings
                                      └──────────┘
```

### Stack
- **Backend:** Python 3.11 + FastAPI
- **Scraping:** Scrapling + Playwright
- **Vision:** Ollama + Qwen2.5-VL (7B)
- **LLM:** Ollama + Qwen 3.5 (4B or 7B)
- **DB:** SQLite + sqlite-vec for embeddings
- **Frontend:** React (minimal) or Streamlit (faster MVP)

## 6. Success Metrics

### Phase 1: Utility (Week 1-2)
| Metric | Target | Measurement |
|--------|--------|-------------|
| Search success rate | > 80% | User finds relevant examples |
| Analysis accuracy | > 70% | Tags match human judgment |
| End-to-end time | < 30s | Query → clustered results |

### Phase 2: Value (Week 3-4)
| Metric | Target | Measurement |
|--------|--------|-------------|
| Pattern coverage | 5+ distinct patterns | Per query |
| Hybrid usefulness | > 50% | User saves/exports hybrid ideas |
| Re-query rate | < 20% | Users find answers first time |

### Phase 3: Adoption (Month 2)
| Metric | Target | Measurement |
|--------|--------|-------------|
| Weekly active users | 3+ PMs | At Walmart demo |
| Demo conversion | > 30% | Ask for access/internal deployment |
| Feature requests | 5+ captured | For iteration planning |

## 7. Iteration Plan

### Sprint 1: Core Loop
- [ ] Scrapling + Google Images integration
- [ ] Qwen2.5-VL image analysis
- [ ] SQLite storage
- [ ] Basic grid UI

**Success:** Can search "checkout flow" and see 10+ analyzed screenshots

### Sprint 2: Intelligence
- [ ] Pattern clustering
- [ ] Hybrid generation
- [ ] Filter/sort UI

**Success:** Can identify 3 distinct patterns and generate 1 hybrid

### Sprint 3: Polish
- [ ] Comparison view
- [ ] Export functionality
- [ ] Mobbin integration
- [ ] Internal demo prep

**Success:** PM can walk through a research question end-to-end in < 5 minutes

## 8. Open Questions

| Question | Decision | Notes |
|----------|----------|-------|
| 1. Image upload as reference? | **Deferred** | Post-1st iteration. Adds complexity, validate core loop first |
| 2. Mobbin rate limits? | **Research required** | Tech discovery on limits + product research on alternative sources |
| 3. Embeddings: sqlite-vec vs Ollama API? | TBD | Default to sqlite-vec for simplicity |
| 4. Fallback for tag hallucinations? | **Deferred** | Use 1st iteration results as baseline to measure accuracy |

## 9. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Scraping blocked | Medium | Rotate user agents, respect robots.txt, cache aggressively |
| Qwen2.5-VL too slow | Low | Use smaller 3B variant, or batch process |
| Results not diverse | Medium | Multiple source APIs, deduplication logic |
| Demo flops | Low | Test with 2-3 PMs before formal demo |

---

**Next Step:** Approve PRD → Scaffold Sprint 1
