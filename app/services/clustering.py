"""Pattern clustering service for analyzed screenshots."""
from collections import Counter, defaultdict
import re
from typing import Dict, List

from app.models.search import Screenshot


class ClusteringService:
    """Clusters screenshots using normalized tag overlap."""
    TERM_GROUPS = {
        "onboarding": ["onboarding", "signup", "welcome"],
        "search": ["search", "results", "discover", "browse"],
        "filter-sort": ["filter", "filters", "sort", "sorting", "refine", "facets"],
        "checkout": ["checkout", "payment", "billing", "cart"],
        "product-scan": ["scan", "scanning", "barcode"],
        "product-create": ["adding a product", "add product", "adding product", "create product"],
        "product-listing": ["listing", "sell", "catalog", "inventory"],
        "menu": ["menu", "restaurant", "delivery", "food"],
        "authentication": ["login", "sign in", "password", "auth"],
        "profile": ["profile", "account", "settings"],
    }

    def cluster_screenshots(
        self,
        screenshots: List[Screenshot],
        min_cluster_size: int = 2,
        max_clusters: int = 10,
    ) -> List[Dict]:
        groups: Dict[str, List[Screenshot]] = defaultdict(list)

        for shot in screenshots:
            key = self._cluster_key(shot)
            groups[key].append(shot)

        clusters: List[Dict] = []
        for _, group in groups.items():
            if len(group) < min_cluster_size:
                continue

            common_tags = self._common_tags(group)
            pattern_name = ", ".join(common_tags[:2]) if common_tags else f"{group[0].source_type} patterns"
            clusters.append(
                {
                    "pattern_name": pattern_name,
                    "count": len(group),
                    "examples": [s.id for s in group[:5]],
                    "common_tags": common_tags[:8],
                }
            )

        clusters.sort(key=lambda c: c["count"], reverse=True)
        return clusters[:max_clusters]

    def _cluster_key(self, shot: Screenshot) -> str:
        tags = sorted({(t.tag_name or "").strip().lower() for t in shot.tags if (t.tag_name or "").strip()})
        if tags:
            return "|".join(tags[:3])
        inferred = self._inferred_terms(shot)
        if inferred:
            return "|".join(inferred[:2])
        return f"source:{shot.source_type}"

    def _common_tags(self, group: List[Screenshot]) -> List[str]:
        counts = Counter()
        for shot in group:
            unique_tags = {(t.tag_name or "").strip().lower() for t in shot.tags if (t.tag_name or "").strip()}
            if not unique_tags:
                unique_tags = set(self._inferred_terms(shot))
            counts.update(unique_tags)
        return [tag for tag, _ in counts.most_common()]

    def _inferred_terms(self, shot: Screenshot) -> List[str]:
        text = " ".join(
            [
                shot.title or "",
                shot.raw_description or "",
                shot.source_url or "",
            ]
        ).lower()
        tokens = set(re.findall(r"[a-z0-9-]+", text))

        inferred: List[str] = []
        for canonical, variants in self.TERM_GROUPS.items():
            if any(variant in text or variant in tokens for variant in variants):
                inferred.append(canonical)

        if inferred:
            return inferred

        title_tokens = [
            token for token in re.findall(r"[a-z0-9-]+", shot.title.lower())
            if len(token) > 3 and token not in {"page", "flows", "flow", "ios", "android"}
        ] if shot.title else []
        return title_tokens[:2]
