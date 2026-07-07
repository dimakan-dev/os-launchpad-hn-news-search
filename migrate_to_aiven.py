#!/usr/bin/env python3
"""
Migrate OpenSearch index from local to Aiven remote cluster.

This script:
1. Connects to local OpenSearch (source)
2. Connects to remote Aiven OpenSearch (destination)
3. Creates the index on remote if it doesn't exist
4. Scrolls through all documents in the local index
5. Bulk-indexes them into the remote cluster

Usage:
    # Set the remote OpenSearch URL with credentials
    export REMOTE_OPENSEARCH_URL="https://user:pass@your-aiven-opensearch.com:port"

    # Run the migration
    python migrate_to_aiven.py

    # Optional: specify different index names
    python migrate_to_aiven.py --source-index hackernews --dest-index hackernews
"""
import os
import sys
from opensearchpy import OpenSearch
from opensearchpy.helpers import scan, streaming_bulk
from urllib.parse import urlparse
import argparse
from typing import Generator, Dict, Any


def create_opensearch_client(url: str, use_ssl: bool = False) -> OpenSearch:
    """
    Create an OpenSearch client from a URL.

    Args:
        url: OpenSearch URL (http://localhost:9200 or https://user:pass@host:port)
        use_ssl: Whether to use SSL (auto-detected from URL scheme)

    Returns:
        OpenSearch client
    """
    parsed = urlparse(url)

    # Auto-detect SSL from URL scheme
    if parsed.scheme == "https":
        use_ssl = True

    http_auth = None
    if parsed.username and parsed.password:
        http_auth = (parsed.username, parsed.password)

    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if use_ssl else 9200)

    client = OpenSearch(
        hosts=[{'host': host, 'port': port}],
        http_compress=True,
        http_auth=http_auth,
        use_ssl=use_ssl,
        verify_certs=use_ssl,
        ssl_assert_hostname=False,
        ssl_show_warn=False
    )

    return client


def get_index_settings_and_mappings(client: OpenSearch, index_name: str) -> Dict[str, Any]:
    """
    Get index settings and mappings from source index.

    Args:
        client: OpenSearch client
        index_name: Index name

    Returns:
        Dictionary with settings and mappings
    """
    index_info = client.indices.get(index=index_name)
    index_data = index_info[index_name]

    # Remove auto-generated settings that shouldn't be copied
    settings = index_data.get('settings', {}).get('index', {})

    # Remove settings that are auto-generated or cluster-specific
    remove_keys = [
        'creation_date', 'uuid', 'version', 'provided_name',
        'routing', 'number_of_replicas', 'blocks', 'max_result_window'
    ]
    for key in remove_keys:
        settings.pop(key, None)

    return {
        'settings': {'index': settings},
        'mappings': index_data.get('mappings', {})
    }


def scroll_documents(client: OpenSearch, index_name: str, batch_size: int = 1000) -> Generator[Dict, None, None]:
    """
    Scroll through all documents in an index.

    Args:
        client: OpenSearch client
        index_name: Index name
        batch_size: Number of documents per scroll batch

    Yields:
        Document dictionaries
    """
    query = {"query": {"match_all": {}}}

    for doc in scan(
        client,
        query=query,
        index=index_name,
        size=batch_size,
        scroll='5m'
    ):
        yield doc


def migrate_index(
    source_client: OpenSearch,
    dest_client: OpenSearch,
    source_index: str,
    dest_index: str,
    batch_size: int = 500,
    recreate: bool = False
):
    """
    Migrate an index from source to destination cluster.

    Args:
        source_client: Source OpenSearch client
        dest_client: Destination OpenSearch client
        source_index: Source index name
        dest_index: Destination index name
        batch_size: Batch size for bulk indexing
        recreate: Whether to recreate the destination index if it exists
    """
    # Check source index exists
    if not source_client.indices.exists(index=source_index):
        print(f"❌ Source index '{source_index}' does not exist")
        sys.exit(1)

    source_count = source_client.count(index=source_index)['count']
    print(f"📊 Source index '{source_index}' contains {source_count:,} documents")

    # Check if destination index exists
    dest_exists = dest_client.indices.exists(index=dest_index)

    if dest_exists:
        dest_count = dest_client.count(index=dest_index)['count']
        print(f"📊 Destination index '{dest_index}' already exists with {dest_count:,} documents")

        if recreate:
            print(f"🗑️  Deleting existing destination index...")
            dest_client.indices.delete(index=dest_index)
            dest_exists = False
        else:
            response = input(f"⚠️  Destination index exists. Continue and append? (y/n): ")
            if response.lower() != 'y':
                print("❌ Migration cancelled")
                sys.exit(0)

    # Create destination index if needed
    if not dest_exists:
        print(f"🔨 Creating destination index '{dest_index}'...")
        index_config = get_index_settings_and_mappings(source_client, source_index)
        dest_client.indices.create(index=dest_index, body=index_config)
        print("✅ Index created")

    # Scroll and bulk insert
    print(f"🔄 Starting migration with batch size {batch_size}...")

    def generate_actions():
        """Generate bulk actions for opensearch-py helpers."""
        for doc in scroll_documents(source_client, source_index, batch_size):
            action = {
                '_op_type': 'index',
                '_index': dest_index,
                '_id': doc['_id'],
                '_source': doc['_source']
            }
            yield action

    # Use streaming_bulk helper for efficient indexing with progress tracking
    success_count = 0
    error_count = 0

    for ok, result in streaming_bulk(
        dest_client,
        generate_actions(),
        chunk_size=batch_size,
        raise_on_error=False,
        raise_on_exception=False
    ):
        if ok:
            success_count += 1
            if success_count % batch_size == 0:
                print(f"  ✓ Migrated {success_count:,} / {source_count:,} documents")
        else:
            error_count += 1
            print(f"  ❌ Error: {result}")

    # Refresh index to make documents searchable
    dest_client.indices.refresh(index=dest_index)

    # Final count
    final_count = dest_client.count(index=dest_index)['count']

    print(f"\n{'='*60}")
    print(f"✅ Migration complete!")
    print(f"   Source documents: {source_count:,}")
    print(f"   Successfully migrated: {success_count:,}")
    print(f"   Errors: {error_count:,}")
    print(f"   Final destination count: {final_count:,}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate OpenSearch index from local to remote Aiven cluster"
    )
    parser.add_argument(
        '--source-url',
        default=os.getenv('SOURCE_OPENSEARCH_URL', 'http://localhost:9200'),
        help='Source OpenSearch URL (default: http://localhost:9200 or SOURCE_OPENSEARCH_URL env var)'
    )
    parser.add_argument(
        '--dest-url',
        default=os.getenv('REMOTE_OPENSEARCH_URL') or os.getenv('OPENSEARCH_URL'),
        help='Destination OpenSearch URL (required, from REMOTE_OPENSEARCH_URL or OPENSEARCH_URL env var)'
    )
    parser.add_argument(
        '--source-index',
        default='hackernews',
        help='Source index name (default: hackernews)'
    )
    parser.add_argument(
        '--dest-index',
        default='hackernews',
        help='Destination index name (default: hackernews)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=500,
        help='Batch size for bulk indexing (default: 500)'
    )
    parser.add_argument(
        '--recreate',
        action='store_true',
        help='Recreate destination index if it exists (deletes existing data)'
    )

    args = parser.parse_args()

    if not args.dest_url:
        print("❌ Error: Destination URL is required")
        print("   Set REMOTE_OPENSEARCH_URL or OPENSEARCH_URL environment variable")
        print("   Or use --dest-url argument")
        sys.exit(1)

    print("🚀 OpenSearch Migration Tool")
    print(f"   Source: {args.source_url} (index: {args.source_index})")
    print(f"   Destination: {args.dest_url} (index: {args.dest_index})")
    print()

    # Create clients
    print("🔌 Connecting to source...")
    source_client = create_opensearch_client(args.source_url)
    print("✅ Connected to source")

    print("🔌 Connecting to destination...")
    dest_client = create_opensearch_client(args.dest_url)
    print("✅ Connected to destination")
    print()

    # Run migration
    migrate_index(
        source_client=source_client,
        dest_client=dest_client,
        source_index=args.source_index,
        dest_index=args.dest_index,
        batch_size=args.batch_size,
        recreate=args.recreate
    )


if __name__ == '__main__':
    main()
