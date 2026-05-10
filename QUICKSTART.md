# Quick Start Guide

Get your Hacker News semantic search running in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- 2-3 GB free RAM
- OpenSearch running locally on port 9200
- Internet connection (for downloading data)

### Start OpenSearch

```bash
# Using Docker (recommended)
docker run -d -p 9200:9200 -p 9600:9600 \
  -e "discovery.type=single-node" \
  -e "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m" \
  opensearchproject/opensearch:latest
```

Verify it's running:
```bash
curl http://localhost:9200
```

## Installation

### Option 1: Automated Setup (Recommended)

```bash
cd hn-semantic-search
./setup.sh
```

### Option 2: Manual Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Test installation
python test_setup.py
```

## Build the Index

This is a **one-time operation** that downloads and indexes HN stories:

```bash
python build_index.py
```

**What happens:**
1. Downloads embedding model (~90 MB) - one-time download
2. Loads 10,000 top HN stories from 2023-2026 via DuckDB (no local download)
3. Generates embeddings for each story
4. Builds k-NN vector index in OpenSearch

**Time:** ~5-10 minutes on first run

**Customize:**
```bash
# Quick index (5,000 stories, higher score threshold)
python build_index.py --limit 5000 --min-score 20

# Larger index (50,000 stories)
python build_index.py --limit 50000

# Specific years only
python build_index.py --years 2024 2025
```

## Start Searching

### Web Interface (Recommended)

```bash
python search_api.py
```

Then open http://localhost:8000 in your browser.

### Command Line

```bash
# Single search
python search_cli.py "machine learning best practices"

# More results
python search_cli.py -n 20 "startup advice"
```

### Run Demo

```bash
python demo.py
```

Shows example searches with different query types.

## Example Queries

Try these in the web interface or CLI:

**Technology:**
- "building scalable distributed systems"
- "learning rust programming language"
- "comparison of different databases"

**Startups:**
- "how to validate a startup idea"
- "fundraising advice for founders"
- "growing from 0 to 1000 users"

**AI/ML:**
- "ethical concerns about artificial intelligence"
- "practical applications of machine learning"
- "GPT and large language models"

**Career:**
- "switching from academia to industry"
- "negotiating job offers and salary"
- "working remotely effectively"

**General:**
- "book recommendations for developers"
- "productivity tips and time management"
- "open source project sustainability"

## Tips

**Why semantic search is powerful:**
- Query: "preventing burnout" finds stories about work-life balance, stress management, etc.
- Query: "side projects" finds stories about indie hacking, bootstrapping, weekend projects
- No need for exact keyword matches!

**Get better results:**
- Use descriptive phrases rather than single words
- Be specific: "debugging memory leaks in python" vs just "debugging"
- Try different phrasings if first results aren't perfect

## Troubleshooting

**"Index is empty" error**
→ Run `python build_index.py` first

**Import errors**
→ Run `python test_setup.py` to check dependencies
→ Install missing packages: `pip install -r requirements.txt`

**Out of memory**
→ Reduce index size: `python build_index.py --limit 5000`

**Slow searches**
→ First search after startup loads models into memory (takes a few seconds)
→ Subsequent searches are fast (<100ms)

**Port 8000 already in use**
→ Stop other services or change port in search_api.py

## Architecture

```
┌─────────────┐
│   Query     │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Sentence Transformer│  Converts text to 384-dim vector
│  (all-MiniLM-L6-v2) │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│    OpenSearch       │  Vector similarity search
│   (k-NN HNSW Index) │  using cosine distance
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Top-K Results     │  Ranked by similarity score
└─────────────────────┘
```

**Data Flow:**
1. DuckDB queries Parquet files on HuggingFace (no local download)
2. Stories are processed and embedded
3. Embeddings stored in OpenSearch with metadata and k-NN index
4. Search queries are embedded and matched against stored vectors
5. Results ranked by cosine similarity

## Next Steps

**Expand your index:**
```bash
# Add more stories (cumulative)
python build_index.py --limit 20000
```

**Integrate the API:**
```python
import requests

response = requests.get(
    "http://localhost:8000/search",
    params={"q": "your query", "n": 10}
)
results = response.json()
```

**Modify the UI:**
- Edit the HTML in `search_api.py` (root endpoint)
- Add filters, themes, or additional features

**Try different models:**
- Edit `config.py` EMBEDDING_MODEL to use other sentence-transformers models
- Trade-off between speed and accuracy

## Files Overview

- `build_index.py` - Index builder (one-time setup)
- `search_api.py` - FastAPI server with web UI
- `search_cli.py` - Command-line search
- `data_loader.py` - HN data loading via DuckDB
- `vector_store.py` - Vector search with OpenSearch
- `config.py` - Configuration settings
- `demo.py` - Example searches
- `test_setup.py` - Dependency checker

## Resources

- [Dataset](https://huggingface.co/datasets/open-index/hacker-news)
- [Sentence Transformers](https://www.sbert.net/)
- [OpenSearch](https://opensearch.org/docs/latest/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)

Happy searching! 🔍
