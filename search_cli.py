"""
Command-line interface for semantic search.
"""
from vector_store import VectorStore
import config
import argparse


def format_result(result: dict, index: int) -> str:
    """Format a search result for display."""
    similarity_pct = result['similarity'] * 100
    url = result['url'] or f"https://news.ycombinator.com/item?id={result['id']}"

    output = f"\n{index}. {result['title']}\n"
    output += f"   Score: {result['score']} | "
    output += f"Comments: {result['comments']} | "
    output += f"By: {result['author']} | "
    output += f"Similarity: {similarity_pct:.1f}%\n"
    output += f"   {url}\n"
    output += f"   HN: https://news.ycombinator.com/item?id={result['id']}\n"

    return output


def main():
    parser = argparse.ArgumentParser(description='Search Hacker News posts semantically')
    parser.add_argument('query', nargs='+', help='Search query')
    parser.add_argument('-n', '--num-results', type=int, default=10,
                        help='Number of results to return (default: 10)')

    args = parser.parse_args()
    query = ' '.join(args.query)

    print(f"\n🔍 Searching for: '{query}'\n")

    vector_store = VectorStore(
        host=config.OPENSEARCH_HOST,
        port=config.OPENSEARCH_PORT,
        index_name=config.OPENSEARCH_INDEX,
        model_name=config.EMBEDDING_MODEL
    )

    if vector_store.count() == 0:
        print("❌ Index is empty. Please run build_index.py first.")
        return

    print(f"📚 Searching {vector_store.count()} indexed stories...\n")

    results = vector_store.search(query, n_results=args.num_results)

    if not results:
        print("No results found.")
        return

    print(f"✅ Found {len(results)} results:\n")
    print("=" * 80)

    for i, result in enumerate(results, 1):
        print(format_result(result, i))
        print("-" * 80)


if __name__ == "__main__":
    main()
