"""
Build the vector index from Hacker News data.
"""
from data_loader import HackerNewsDataLoader
from vector_store import VectorStore
import config
import argparse


def main():
    parser = argparse.ArgumentParser(description='Build semantic search index for Hacker News')
    parser.add_argument('--limit', type=int, default=10000, help='Maximum number of stories to index')
    parser.add_argument('--min-score', type=int, default=10, help='Minimum score threshold')
    parser.add_argument('--years', type=int, nargs='+', default=[2023, 2024, 2025, 2026],
                        help='Years to load data from')
    parser.add_argument('--clear', action='store_true', help='Clear existing index before building')

    args = parser.parse_args()

    print("Initializing vector store...")
    vector_store = VectorStore(
        host=config.OPENSEARCH_HOST,
        port=config.OPENSEARCH_PORT,
        index_name=config.OPENSEARCH_INDEX,
        model_name=config.EMBEDDING_MODEL
    )

    if args.clear:
        print("Clearing existing index...")
        vector_store.clear()

    existing_count = vector_store.count()
    if existing_count > 0:
        print(f"Found existing index with {existing_count} stories")
        response = input("Continue and add more stories? (y/n): ")
        if response.lower() != 'y':
            print("Exiting")
            return

    print(f"\nLoading Hacker News data from years: {args.years}")
    loader = HackerNewsDataLoader(years=args.years)

    stories = loader.load_stories(limit=args.limit, min_score=args.min_score)

    if not stories:
        print("No stories loaded. Exiting.")
        return

    print("\nPreparing search content...")
    for story in stories:
        story['search_content'] = loader.create_search_content(story)

    print(f"\nIndexing {len(stories)} stories...")
    vector_store.add_stories(stories)

    print("\n✅ Index building complete!")
    print(f"Total stories in index: {vector_store.count()}")

    loader.close()


if __name__ == "__main__":
    main()
