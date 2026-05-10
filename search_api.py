"""
FastAPI server for semantic search over Hacker News posts.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from vector_store import VectorStore
import config
import uvicorn


app = FastAPI(
    title="Hacker News Semantic Search",
    description="Search Hacker News posts using semantic similarity",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vector_store: Optional[VectorStore] = None


class SearchResult(BaseModel):
    id: str
    title: str
    url: str
    score: int
    author: str
    time: str
    comments: int
    similarity: float


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int


@app.on_event("startup")
async def startup_event():
    global vector_store
    print("Loading vector store...")
    vector_store = VectorStore(
        host=config.OPENSEARCH_HOST,
        port=config.OPENSEARCH_PORT,
        index_name=config.OPENSEARCH_INDEX,
        model_name=config.EMBEDDING_MODEL
    )
    print(f"Vector store loaded with {vector_store.count()} stories")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve a simple web interface."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hacker News Semantic Search</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 900px;
                margin: 40px auto;
                padding: 20px;
                background: #f6f6ef;
            }
            h1 {
                color: #ff6600;
                font-size: 28px;
                margin-bottom: 10px;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
            }
            .search-box {
                display: flex;
                gap: 10px;
                margin-bottom: 30px;
            }
            input[type="text"] {
                flex: 1;
                padding: 12px;
                font-size: 16px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            button {
                padding: 12px 24px;
                background: #ff6600;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                cursor: pointer;
            }
            button:hover {
                background: #ff7700;
            }
            .result {
                background: white;
                padding: 16px;
                margin-bottom: 12px;
                border-radius: 4px;
                border: 1px solid #ddd;
            }
            .title {
                font-size: 16px;
                font-weight: 500;
                margin-bottom: 8px;
            }
            .title a {
                color: #000;
                text-decoration: none;
            }
            .title a:hover {
                text-decoration: underline;
            }
            .meta {
                font-size: 13px;
                color: #666;
            }
            .similarity {
                display: inline-block;
                background: #ff6600;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 11px;
                margin-left: 8px;
            }
            .loading {
                text-align: center;
                color: #666;
                padding: 20px;
            }
            .error {
                background: #fee;
                border: 1px solid #fcc;
                padding: 12px;
                border-radius: 4px;
                color: #c00;
            }
            .stats {
                font-size: 14px;
                color: #666;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <h1>🔍 Hacker News Semantic Search</h1>
        <p class="subtitle">Search HN stories by meaning, not just keywords</p>

        <div class="search-box">
            <input type="text" id="query" placeholder="e.g., 'building scalable systems' or 'AI ethics'" />
            <button onclick="search()">Search</button>
        </div>

        <div id="results"></div>

        <script>
            const queryInput = document.getElementById('query');
            const resultsDiv = document.getElementById('results');

            queryInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') search();
            });

            async function search() {
                const query = queryInput.value.trim();
                if (!query) return;

                resultsDiv.innerHTML = '<div class="loading">Searching...</div>';

                try {
                    const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
                    if (!response.ok) throw new Error('Search failed');

                    const data = await response.json();
                    displayResults(data);
                } catch (error) {
                    resultsDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
                }
            }

            function displayResults(data) {
                if (data.results.length === 0) {
                    resultsDiv.innerHTML = '<div class="stats">No results found</div>';
                    return;
                }

                let html = `<div class="stats">Found ${data.total_results} results for "${data.query}"</div>`;

                data.results.forEach(result => {
                    const url = result.url || `https://news.ycombinator.com/item?id=${result.id}`;
                    const similarity = (result.similarity * 100).toFixed(1);

                    html += `
                        <div class="result">
                            <div class="title">
                                <a href="${url}" target="_blank">${result.title}</a>
                                <span class="similarity">${similarity}%</span>
                            </div>
                            <div class="meta">
                                ${result.score} points by ${result.author} |
                                ${result.comments} comments |
                                <a href="https://news.ycombinator.com/item?id=${result.id}" target="_blank">HN</a>
                            </div>
                        </div>
                    `;
                });

                resultsDiv.innerHTML = html;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query", min_length=1),
    n: int = Query(10, description="Number of results", ge=1, le=50)
):
    """
    Search for Hacker News stories semantically similar to the query.
    """
    if vector_store is None:
        raise HTTPException(status_code=503, detail="Vector store not initialized")

    if vector_store.count() == 0:
        raise HTTPException(
            status_code=503,
            detail="Index is empty. Please run build_index.py first."
        )

    results = vector_store.search(q, n_results=n)

    return SearchResponse(
        query=q,
        results=[SearchResult(**r) for r in results],
        total_results=len(results)
    )


@app.get("/stats")
async def stats():
    """Get index statistics."""
    if vector_store is None:
        raise HTTPException(status_code=503, detail="Vector store not initialized")

    return {
        "total_stories": vector_store.count(),
        "model": vector_store.model_name
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
