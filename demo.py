"""
Quick demo of the semantic search functionality.
"""
from vector_store import VectorStore
import config


def run_demo():
    """Run example searches to demonstrate semantic search capabilities."""

    print("🔍 Hacker News Semantic Search Demo\n")

    vector_store = VectorStore(
        host=config.OPENSEARCH_HOST,
        port=config.OPENSEARCH_PORT,
        index_name=config.OPENSEARCH_INDEX,
        model_name=config.EMBEDDING_MODEL
    )

    if vector_store.count() == 0:
        print("❌ No data indexed yet. Please run: python build_index.py")
        return

    print(f"📚 Loaded index with {vector_store.count()} stories\n")

    example_queries = [
        "artificial intelligence ethics and safety",
        "building successful startups",
        "distributed systems at scale",
        "learning to code as a beginner",
        "remote work culture"
    ]

    for query in example_queries:
        print(f"\n{'='*80}")
        print(f"Query: '{query}'")
        print('='*80)

        results = vector_store.search(query, n_results=3)

        for i, result in enumerate(results, 1):
            similarity = result['similarity'] * 100
            print(f"\n{i}. {result['title']}")
            print(f"   Score: {result['score']} | Similarity: {similarity:.1f}%")
            print(f"   https://news.ycombinator.com/item?id={result['id']}")

    print("\n" + "="*80)
    print("\n✅ Demo complete!")
    print("\nTry your own searches:")
    print("  Web UI:  python search_api.py  (then open http://localhost:8000)")
    print("  CLI:     python search_cli.py 'your search query'")


if __name__ == "__main__":
    run_demo()
