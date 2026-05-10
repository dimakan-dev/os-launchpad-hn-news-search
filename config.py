"""
Configuration settings for the Hacker News Semantic Search application.
"""
import os

# Vector Store Settings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Options: all-MiniLM-L6-v2, all-mpnet-base-v2, paraphrase-MiniLM-L6-v2

# Get OpenSearch connection from environment variable (Aiven-injected) or fall back to localhost
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "https://localhost:9200")
# Parse the URL to extract host and port
from urllib.parse import urlparse
_parsed = urlparse(OPENSEARCH_URL)
OPENSEARCH_HOST = _parsed.hostname or "localhost"
OPENSEARCH_PORT = _parsed.port or 9200
OPENSEARCH_INDEX = "hackernews"
SIMILARITY_METRIC = "cosine"  # Options: cosine, l2, ip

# Data Loading Settings
DEFAULT_YEARS = [2023, 2024, 2025, 2026]
DEFAULT_LIMIT = 10000
DEFAULT_MIN_SCORE = 10

# API Settings
API_HOST = "0.0.0.0"
API_PORT = 8000
CORS_ORIGINS = ["*"]

# Search Settings
DEFAULT_SEARCH_RESULTS = 10
MAX_SEARCH_RESULTS = 50

# UI Settings
APP_TITLE = "Hacker News Semantic Search"
APP_DESCRIPTION = "Search HN stories by meaning, not just keywords"
PRIMARY_COLOR = "#ff6600"  # HN orange
