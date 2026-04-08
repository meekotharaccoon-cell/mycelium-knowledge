#!/usr/bin/env python3
"""
RSS Harvester - content discovery engine for Mycelium Knowledge.

Pulls from free public APIs:
  - Wikipedia Current Events (REST API)
  - HackerNews top stories (Firebase API)
  - Reddit r/todayilearned (JSON endpoint)

Deduplicates, scores for SolarPunk relevance, and returns ranked items.
Only stdlib + requests.
"""

import hashlib
import re
from datetime import datetime, timezone

import requests

# Timeout for all HTTP requests (seconds)
HTTP_TIMEOUT = 15

# SolarPunk relevance keywords and their weights
SOLARPUNK_KEYWORDS = {
    # community & mutual aid
    "community": 3, "mutual aid": 4, "cooperative": 3, "solidarity": 3,
    "grassroots": 3, "collective": 2, "neighborhood": 2, "volunteer": 2,
    # autonomy & rights
    "autonomy": 3, "self-reliance": 3, "sovereignty": 3, "privacy": 2,
    "rights": 2, "freedom": 2, "censorship": 2, "surveillance": 2,
    "decentralize": 3, "open source": 3,
    # technology for good
    "solar": 2, "renewable": 2, "off-grid": 3, "mesh network": 3,
    "encryption": 2, "linux": 1, "raspberry pi": 2, "arduino": 2,
    "3d print": 2, "repair": 2, "right to repair": 4,
    # environment
    "permaculture": 3, "garden": 2, "compost": 2, "sustainability": 2,
    "biodiversity": 2, "regenerative": 3, "rewilding": 3,
    "climate": 1, "pollution": 1,
}


def _fingerprint(title: str) -> str:
    """Normalize title into a dedup fingerprint."""
    t = re.sub(r"[^a-z0-9 ]", "", title.lower())
    t = re.sub(r"\s+", " ", t).strip()
    return hashlib.md5(t.encode()).hexdigest()


def _solarpunk_score(text: str) -> int:
    """Score text for SolarPunk theme relevance."""
    text_lower = text.lower()
    return sum(
        weight for kw, weight in SOLARPUNK_KEYWORDS.items() if kw in text_lower
    )


class RSSHarvester:
    """Discovers trending content from free public sources."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MyceliumKnowledge/1.0 (autonomous learning agent)"
        })

    # ------------------------------------------------------------------
    # Source: Wikipedia Current Events
    # ------------------------------------------------------------------

    def _fetch_wikipedia(self) -> list:
        """Fetch today's current events from Wikipedia REST API."""
        items = []
        today = datetime.now(timezone.utc)
        url = (
            f"https://api.wikimedia.org/feed/v1/wikipedia/en/featured/"
            f"{today.year}/{today.month:02d}/{today.day:02d}"
        )
        try:
            resp = self.session.get(url, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            # Most-read articles
            for article in data.get("mostread", {}).get("articles", [])[:10]:
                items.append({
                    "title": article.get("normalizedtitle", article.get("title", "")),
                    "summary": article.get("extract", "")[:300],
                    "url": article.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    "source": "wikipedia",
                })

            # On-this-day
            for event in data.get("onthisday", [])[:5]:
                items.append({
                    "title": event.get("text", "")[:120],
                    "summary": event.get("text", "")[:300],
                    "url": "",
                    "source": "wikipedia",
                })

        except Exception as e:
            print(f"  [WARN] Wikipedia fetch failed: {e}")
        return items

    # ------------------------------------------------------------------
    # Source: HackerNews top stories
    # ------------------------------------------------------------------

    def _fetch_hackernews(self) -> list:
        """Fetch top stories from HackerNews Firebase API."""
        items = []
        try:
            resp = self.session.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                timeout=HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            story_ids = resp.json()[:15]  # top 15

            for sid in story_ids:
                try:
                    sr = self.session.get(
                        f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                        timeout=HTTP_TIMEOUT,
                    )
                    sr.raise_for_status()
                    story = sr.json()
                    if story and story.get("type") == "story":
                        items.append({
                            "title": story.get("title", ""),
                            "summary": story.get("title", ""),  # HN has no body
                            "url": story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                            "source": "hackernews",
                        })
                except Exception:
                    continue
        except Exception as e:
            print(f"  [WARN] HackerNews fetch failed: {e}")
        return items

    # ------------------------------------------------------------------
    # Source: Reddit r/todayilearned
    # ------------------------------------------------------------------

    def _fetch_reddit_til(self) -> list:
        """Fetch top posts from r/todayilearned via JSON API."""
        items = []
        try:
            resp = self.session.get(
                "https://www.reddit.com/r/todayilearned/hot.json?limit=15",
                timeout=HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            for post in data.get("data", {}).get("children", []):
                pd = post.get("data", {})
                title = pd.get("title", "")
                # Strip "TIL " prefix for cleaner processing
                clean_title = re.sub(r"^TIL\s+(?:that\s+)?", "", title, flags=re.IGNORECASE)
                items.append({
                    "title": clean_title[:150],
                    "summary": pd.get("selftext", title)[:300],
                    "url": pd.get("url", ""),
                    "source": "reddit",
                })
        except Exception as e:
            print(f"  [WARN] Reddit fetch failed: {e}")
        return items

    # ------------------------------------------------------------------
    # Deduplicate + Score + Harvest
    # ------------------------------------------------------------------

    def _deduplicate(self, items: list) -> list:
        """Remove near-duplicate items by title fingerprint."""
        seen = set()
        unique = []
        for item in items:
            fp = _fingerprint(item["title"])
            if fp not in seen:
                seen.add(fp)
                unique.append(item)
        return unique

    def _merge_sources(self, items: list) -> list:
        """Merge items with similar titles, tracking all sources."""
        by_fp = {}
        for item in items:
            fp = _fingerprint(item["title"])
            if fp in by_fp:
                existing = by_fp[fp]
                if item["source"] not in existing["sources"]:
                    existing["sources"].append(item["source"])
            else:
                item["sources"] = [item["source"]]
                by_fp[fp] = item
        return list(by_fp.values())

    def harvest(self) -> list:
        """Run full harvest: fetch all sources, dedupe, score, rank."""
        all_items = []

        all_items.extend(self._fetch_wikipedia())
        all_items.extend(self._fetch_hackernews())
        all_items.extend(self._fetch_reddit_til())

        print(f"  Raw items before dedup: {len(all_items)}")

        # Merge duplicates and track multi-source items
        merged = self._merge_sources(all_items)
        print(f"  After merge: {len(merged)}")

        # Score for SolarPunk relevance
        for item in merged:
            text = f"{item['title']} {item.get('summary', '')}"
            item["solarpunk_score"] = _solarpunk_score(text)

        # Sort: SolarPunk relevance first, then multi-source items
        merged.sort(
            key=lambda x: (x["solarpunk_score"], len(x.get("sources", []))),
            reverse=True,
        )

        return merged


if __name__ == "__main__":
    harvester = RSSHarvester()
    results = harvester.harvest()
    print(f"\n{'='*60}")
    print(f"Harvested {len(results)} unique items")
    print(f"{'='*60}\n")
    for i, item in enumerate(results[:10], 1):
        print(f"{i}. [{item.get('solarpunk_score', 0)}] {item['title']}")
        print(f"   Sources: {', '.join(item.get('sources', []))}")
        print()
