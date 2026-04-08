#!/usr/bin/env python3
"""
Guide Builder - creates free and premium learning guides.

Free guides include overview + key concepts.
Premium guides add practical steps, resources, and exercises.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GUIDES_DIR = REPO_ROOT / "guides"
FREE_DIR = GUIDES_DIR / "free"
PREMIUM_DIR = GUIDES_DIR / "premium"
PUBLISHED_FILE = REPO_ROOT / "data" / "published.json"


def slugify(text: str) -> str:
    """Turn a title into a filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:80].strip("-")


class GuideBuilder:
    """Generates structured learning guides in free and premium tiers."""

    def __init__(self):
        FREE_DIR.mkdir(parents=True, exist_ok=True)
        PREMIUM_DIR.mkdir(parents=True, exist_ok=True)
        PUBLISHED_FILE.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Content generation (template-based; swap for LLM calls later)
    # ------------------------------------------------------------------

    @staticmethod
    def _section_overview(topic: str, summary: str) -> str:
        return (
            f"## Overview\n\n"
            f"**{topic}** is a topic of growing relevance in today's landscape.\n\n"
            f"{summary}\n\n"
            f"This guide will walk you through the essentials and give you a "
            f"practical foundation to act on this knowledge.\n"
        )

    @staticmethod
    def _section_key_concepts(topic: str, category: str) -> str:
        # Category-aware concept scaffolding
        concept_map = {
            "tech": [
                "Core technology and how it works",
                "Current state of adoption",
                "Open-source alternatives and tools",
                "Security and privacy considerations",
            ],
            "finance": [
                "Fundamental financial principle",
                "Risk vs. reward analysis",
                "Practical money moves you can make today",
                "Common pitfalls to avoid",
            ],
            "legal-rights": [
                "Your rights in this area",
                "Key laws and precedents",
                "How to document and protect yourself",
                "Organizations that can help",
            ],
            "health": [
                "What the science says",
                "Daily habits that make a difference",
                "Warning signs to watch for",
                "When to seek professional help",
            ],
            "survival": [
                "Core survival principle",
                "Essential supplies and preparation",
                "Step-by-step emergency protocol",
                "Long-term resilience strategies",
            ],
            "community": [
                "Why collective action matters here",
                "Models that are working right now",
                "How to start in your neighborhood",
                "Scaling from local to regional",
            ],
        }
        concepts = concept_map.get(category, concept_map["tech"])
        lines = ["## Key Concepts\n"]
        for i, concept in enumerate(concepts, 1):
            lines.append(f"### {i}. {concept}\n")
            lines.append(
                f"Understanding this aspect of **{topic}** is critical. "
                f"Dig deeper by exploring the resources section below.\n"
            )
        return "\n".join(lines)

    @staticmethod
    def _section_practical_steps(topic: str) -> str:
        return (
            "## Practical Steps\n\n"
            "1. **Research** - Spend 30 minutes reading primary sources on "
            f"*{topic}*. Use the resources listed below.\n"
            "2. **Take Notes** - Write down 3 things that surprised you and "
            "3 things you can act on this week.\n"
            "3. **Discuss** - Share what you learned with one person. Teaching "
            "cements understanding.\n"
            "4. **Apply** - Pick one actionable insight and implement it within "
            "48 hours.\n"
            "5. **Review** - After one week, revisit your notes and assess what "
            "changed.\n"
        )

    @staticmethod
    def _section_resources(topic: str) -> str:
        return (
            "## Resources\n\n"
            f"- Wikipedia: search \"{topic}\"\n"
            f"- HackerNews: search for recent discussions\n"
            f"- Reddit: r/todayilearned, r/explainlikeimfive\n"
            f"- YouTube: look for explainer videos under 15 minutes\n"
            f"- Local library: free access to journals and databases\n"
        )

    @staticmethod
    def _section_exercises(topic: str) -> str:
        return (
            "## Exercises\n\n"
            f"1. **Explain it simply** - Write a 3-sentence explanation of "
            f"*{topic}* that a 12-year-old would understand.\n"
            f"2. **Find the debate** - Identify two opposing viewpoints on this "
            f"topic. Summarize each in one paragraph.\n"
            f"3. **Build something** - Create a small project, document, or "
            f"action plan related to *{topic}*.\n"
            f"4. **Teach it** - Give a 5-minute informal talk to a friend or "
            f"record a voice note explaining the topic.\n"
            f"5. **Connect it** - How does *{topic}* relate to something you "
            f"already know? Draw the connection in writing.\n"
        )

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, topic: str, category: str, summary: str = "") -> dict:
        """Generate both free and premium versions of a guide.

        Returns metadata dict with paths and publish info.
        """
        slug = slugify(topic)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # -- Free guide (overview + key concepts) --
        free_content = "\n".join([
            f"# {topic}",
            f"*Category: {category} | Generated: {today}*",
            "",
            self._section_overview(topic, summary),
            self._section_key_concepts(topic, category),
            "---",
            "*Want practical steps, curated resources, and hands-on exercises? "
            "Check out the **premium guide**.*",
            "",
        ])
        free_path = FREE_DIR / f"{slug}.md"
        free_path.write_text(free_content, encoding="utf-8")

        # -- Premium guide (full content) --
        premium_content = "\n".join([
            f"# {topic} - Complete Guide",
            f"*Category: {category} | Generated: {today}*",
            "",
            self._section_overview(topic, summary),
            self._section_key_concepts(topic, category),
            self._section_practical_steps(topic),
            self._section_resources(topic),
            self._section_exercises(topic),
            "---",
            "*Part of the Mycelium Knowledge collection. "
            "Learn something new every day.*",
            "",
        ])
        premium_path = PREMIUM_DIR / f"{slug}.md"
        premium_path.write_text(premium_content, encoding="utf-8")

        # -- Track published --
        meta = {
            "topic": topic,
            "slug": slug,
            "category": category,
            "date": today,
            "free_path": str(free_path.relative_to(REPO_ROOT)),
            "premium_path": str(premium_path.relative_to(REPO_ROOT)),
        }
        published = []
        if PUBLISHED_FILE.exists():
            published = json.loads(PUBLISHED_FILE.read_text(encoding="utf-8"))
        published.append(meta)
        PUBLISHED_FILE.write_text(json.dumps(published, indent=2), encoding="utf-8")

        print(f"  Guide built: {slug} (free + premium)")
        return meta


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "Off-Grid Solar Power Basics"
    category = sys.argv[2] if len(sys.argv) > 2 else "survival"
    builder = GuideBuilder()
    result = builder.build(topic=topic, category=category, summary="A practical introduction.")
    print(json.dumps(result, indent=2))
