#!/usr/bin/env python3
"""
Mycelium Knowledge Agent - autonomous daily knowledge discovery.

Discovers trending topics, curates digests, generates TIL posts,
tracks a knowledge graph, and flags premium guide opportunities.
"""

import json
import os
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Add parent dir so we can import siblings
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rss_harvester import RSSHarvester
from guide_builder import GuideBuilder

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
DIGEST_DIR = DATA_DIR / "digests"
GRAPH_FILE = DATA_DIR / "knowledge_graph.json"

CATEGORIES = ["tech", "finance", "legal-rights", "health", "survival", "community"]

CATEGORY_KEYWORDS = {
    "tech": [
        "software", "ai", "machine learning", "programming", "open source",
        "linux", "python", "javascript", "api", "cloud", "cybersecurity",
        "hardware", "robotics", "blockchain", "encryption", "algorithm",
    ],
    "finance": [
        "money", "invest", "stock", "crypto", "bank", "budget", "tax",
        "debt", "savings", "credit", "economy", "inflation", "income",
        "frugal", "passive income", "side hustle", "freelance",
    ],
    "legal-rights": [
        "rights", "law", "court", "amendment", "privacy", "surveillance",
        "protest", "civil", "police", "justice", "legal", "regulation",
        "freedom", "censorship", "eff", "aclu", "tenant", "worker",
    ],
    "health": [
        "health", "mental", "exercise", "nutrition", "sleep", "therapy",
        "meditation", "first aid", "vaccine", "disease", "wellness",
        "diet", "fitness", "stress", "anxiety", "depression",
    ],
    "survival": [
        "survival", "emergency", "preparedness", "off-grid", "water",
        "shelter", "fire", "food storage", "self-reliance", "homestead",
        "garden", "solar", "power outage", "disaster", "resilience",
    ],
    "community": [
        "community", "mutual aid", "cooperative", "volunteer", "organize",
        "solidarity", "neighborhood", "collective", "grassroots", "local",
        "commons", "sharing", "democratic", "autonomy", "decentralize",
    ],
}


def categorize(title: str, summary: str) -> str:
    """Assign a category based on keyword scoring."""
    text = f"{title} {summary}".lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw in text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "tech"


def topic_id(title: str) -> str:
    """Stable short hash for a topic."""
    return hashlib.sha256(title.encode()).hexdigest()[:12]


class KnowledgeAgent:
    """Discovers, curates, and packages daily knowledge."""

    def __init__(self):
        self.harvester = RSSHarvester()
        self.guide_builder = GuideBuilder()
        self.today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._ensure_dirs()

    def _ensure_dirs(self):
        DIGEST_DIR.mkdir(parents=True, exist_ok=True)
        (REPO_ROOT / "guides" / "free").mkdir(parents=True, exist_ok=True)
        (REPO_ROOT / "guides" / "premium").mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Knowledge graph
    # ------------------------------------------------------------------

    def _load_graph(self) -> dict:
        if GRAPH_FILE.exists():
            return json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
        return {"nodes": {}, "edges": []}

    def _save_graph(self, graph: dict):
        GRAPH_FILE.write_text(json.dumps(graph, indent=2), encoding="utf-8")

    def _update_graph(self, items: list) -> None:
        """Add topics as nodes and connect items that share a category."""
        graph = self._load_graph()
        nodes = graph["nodes"]
        edges = graph["edges"]
        today_ids = []
        for item in items:
            tid = topic_id(item["title"])
            nodes[tid] = {
                "title": item["title"],
                "category": item["category"],
                "last_seen": self.today,
                "sources": item.get("sources", []),
            }
            today_ids.append(tid)
        # Connect items in the same category from today
        for i, a in enumerate(today_ids):
            for b in today_ids[i + 1:]:
                if nodes[a]["category"] == nodes[b]["category"]:
                    edge = sorted([a, b])
                    if edge not in edges:
                        edges.append(edge)
        graph["nodes"] = nodes
        graph["edges"] = edges
        self._save_graph(graph)

    # ------------------------------------------------------------------
    # Digest + TIL
    # ------------------------------------------------------------------

    def _build_digest(self, items: list) -> str:
        """Render a markdown daily digest."""
        lines = [
            f"# Daily Knowledge Digest - {self.today}",
            "",
            f"*{len(items)} topics discovered across {len(set(i['category'] for i in items))} categories*",
            "",
        ]
        by_cat = {}
        for item in items:
            by_cat.setdefault(item["category"], []).append(item)
        for cat in CATEGORIES:
            group = by_cat.get(cat, [])
            if not group:
                continue
            lines.append(f"## {cat.replace('-', ' ').title()}")
            lines.append("")
            for item in group:
                lines.append(f"### {item['title']}")
                lines.append("")
                lines.append(item.get("summary", "No summary available."))
                lines.append("")
                src = ", ".join(item.get("sources", []))
                lines.append(f"*Sources: {src}*")
                lines.append("")
        return "\n".join(lines)

    def _generate_til_posts(self, items: list) -> list:
        """Create short TIL posts suitable for social media."""
        posts = []
        for item in items[:5]:  # top 5
            post = {
                "text": (
                    f"TIL: {item['title']}\n\n"
                    f"{item.get('summary', '')[:200]}\n\n"
                    f"#{item['category'].replace('-', '')} #TIL #MyceliumKnowledge"
                ),
                "category": item["category"],
                "date": self.today,
            }
            posts.append(post)
        return posts

    # ------------------------------------------------------------------
    # Premium guide opportunities
    # ------------------------------------------------------------------

    def _find_guide_opportunities(self, items: list) -> list:
        """Score items for premium-guide potential.

        Heuristic: topics that appear in multiple sources and belong to
        high-demand categories get higher scores.
        """
        high_demand = {"finance", "legal-rights", "health", "survival"}
        opportunities = []
        for item in items:
            score = len(item.get("sources", []))  # multi-source = broader interest
            if item["category"] in high_demand:
                score += 2
            if score >= 2:
                opportunities.append({**item, "guide_score": score})
        opportunities.sort(key=lambda x: x["guide_score"], reverse=True)
        return opportunities[:3]

    # ------------------------------------------------------------------
    # Main run
    # ------------------------------------------------------------------

    def run(self):
        """Execute a full knowledge-discovery cycle."""
        print(f"[{self.today}] Mycelium Knowledge Agent starting...")

        # 1. Harvest
        print("  Harvesting RSS feeds and APIs...")
        raw_items = self.harvester.harvest()
        print(f"  Found {len(raw_items)} raw items")

        if not raw_items:
            print("  No items discovered. Exiting.")
            return

        # 2. Categorize
        print("  Categorizing...")
        for item in raw_items:
            item["category"] = categorize(item["title"], item.get("summary", ""))

        # 3. Write digest
        digest_md = self._build_digest(raw_items)
        digest_path = DIGEST_DIR / f"{self.today}.md"
        digest_path.write_text(digest_md, encoding="utf-8")
        print(f"  Digest written: {digest_path.name}")

        # 4. TIL posts
        til_posts = self._generate_til_posts(raw_items)
        til_path = DATA_DIR / "til_posts.json"
        existing = []
        if til_path.exists():
            existing = json.loads(til_path.read_text(encoding="utf-8"))
        existing.extend(til_posts)
        til_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        print(f"  {len(til_posts)} TIL posts generated")

        # 5. Knowledge graph
        self._update_graph(raw_items)
        print("  Knowledge graph updated")

        # 6. Premium guide opportunities
        opportunities = self._find_guide_opportunities(raw_items)
        if opportunities:
            print(f"  {len(opportunities)} premium guide opportunities found:")
            for opp in opportunities:
                print(f"    - {opp['title']} (score {opp['guide_score']})")
            # Auto-generate the top opportunity
            top = opportunities[0]
            self.guide_builder.build(
                topic=top["title"],
                category=top["category"],
                summary=top.get("summary", ""),
            )
            print(f"  Guide generated for: {top['title']}")

        print(f"[{self.today}] Cycle complete.")


if __name__ == "__main__":
    agent = KnowledgeAgent()
    agent.run()
