"""
Load and process Hacker News data from the open-index dataset.
"""
import duckdb
from typing import List, Dict, Optional
from datetime import datetime


class HackerNewsDataLoader:
    """Loads Hacker News stories from the Hugging Face dataset."""

    def __init__(self, years: Optional[List[int]] = None):
        """
        Initialize the data loader.

        Args:
            years: List of years to load. If None, loads recent data (2023-2024).
        """
        self.years = years or [2023, 2024, 2025, 2026]
        self.conn = duckdb.connect()

    def load_stories(self, limit: int = 10000, min_score: int = 10) -> List[Dict]:
        """
        Load top stories from Hacker News.

        Args:
            limit: Maximum number of stories to load
            min_score: Minimum score threshold for stories

        Returns:
            List of story dictionaries with id, title, url, score, time, and author
        """
        year_patterns = ' OR '.join([f"time >= '{year}-01-01'" for year in self.years])

        query = f"""
        SELECT
            id,
            title,
            url,
            text,
            score,
            time,
            "by" as author,
            descendants as comments
        FROM read_parquet('hf://datasets/open-index/hacker-news/data/*/*.parquet')
        WHERE type = 1
            AND title != ''
            AND score >= {min_score}
            AND ({year_patterns})
        ORDER BY score DESC, time DESC
        LIMIT {limit}
        """

        print(f"Loading up to {limit} stories with score >= {min_score}...")
        result = self.conn.execute(query).fetchdf()

        stories = result.to_dict('records')
        print(f"Loaded {len(stories)} stories")

        return stories

    def create_search_content(self, story: Dict) -> str:
        """
        Create searchable content from a story by combining title, url, and text.

        Args:
            story: Story dictionary

        Returns:
            Combined content string for embedding
        """
        parts = []

        if story.get('title'):
            parts.append(story['title'])

        if story.get('url'):
            parts.append(f"URL: {story['url']}")

        if story.get('text'):
            text = story['text'][:500]
            parts.append(text)

        return ' | '.join(parts)

    def close(self):
        """Close the database connection."""
        self.conn.close()
