"""
Vector store for semantic search using OpenSearch and sentence transformers.
"""
from opensearchpy import OpenSearch
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import urlparse
import os


class VectorStore:
    """Manages embeddings and semantic search using OpenSearch."""

    def __init__(self, host: str = "localhost", port: int = 9200, index_name: str = "hackernews", model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the vector store.

        Args:
            host: OpenSearch host
            port: OpenSearch port
            index_name: Name of the OpenSearch index
            model_name: Sentence transformer model to use for embeddings
        """
        self.host = host
        self.port = port
        self.index_name = index_name
        self.model_name = model_name

        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_embedding_dimension()

        # Check if we have an Aiven OpenSearch URL with credentials
        opensearch_url = os.getenv("OPENSEARCH_URL")
        if opensearch_url and opensearch_url.startswith("https://"):
            # Parse credentials from URL
            parsed = urlparse(opensearch_url)
            use_ssl = True
            http_auth = None
            if parsed.username and parsed.password:
                http_auth = (parsed.username, parsed.password)

            self.client = OpenSearch(
                hosts=[{'host': parsed.hostname, 'port': parsed.port or 443}],
                http_compress=True,
                http_auth=http_auth,
                use_ssl=use_ssl,
                verify_certs=True,
                ssl_assert_hostname=False,
                ssl_show_warn=False
            )
        else:
            # Local OpenSearch without SSL
            self.client = OpenSearch(
                hosts=[{'host': host, 'port': port}],
                http_compress=True,
                use_ssl=False,
                verify_certs=False,
                ssl_assert_hostname=False,
                ssl_show_warn=False
            )

        if self.client.indices.exists(index=self.index_name):
            count = self.client.count(index=self.index_name)['count']
            print(f"Connected to existing index with {count} items")
        else:
            self._create_index()
            print("Created new index")

    def _create_index(self):
        """Create the OpenSearch index with k-NN settings."""
        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100
                }
            },
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "title": {"type": "text"},
                    "url": {"type": "keyword"},
                    "score": {"type": "integer"},
                    "author": {"type": "keyword"},
                    "time": {"type": "date"},
                    "comments": {"type": "integer"},
                    "document": {"type": "text"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": self.embedding_dim,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "lucene",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 16
                            }
                        }
                    }
                }
            }
        }
        self.client.indices.create(index=self.index_name, body=index_body)

    def add_stories(self, stories: List[Dict], content_field: str = "search_content"):
        """
        Add stories to the vector store.

        Args:
            stories: List of story dictionaries
            content_field: Field name containing the content to embed
        """
        if not stories:
            print("No stories to add")
            return

        print(f"Generating embeddings for {len(stories)} stories...")

        documents = [story[content_field] for story in stories]
        embeddings = self.model.encode(documents, show_progress_bar=True).tolist()

        batch_size = 500
        for i in range(0, len(stories), batch_size):
            batch_end = min(i + batch_size, len(stories))
            bulk_data = []

            for j in range(i, batch_end):
                story = stories[j]
                # Action line
                bulk_data.append({"index": {"_index": self.index_name, "_id": str(story['id'])}})

                # Convert time to ISO format if needed
                time_value = story.get('time')
                if time_value:
                    if isinstance(time_value, (int, float)):
                        # Unix timestamp
                        time_value = datetime.fromtimestamp(time_value).isoformat()
                    elif hasattr(time_value, 'isoformat'):
                        # datetime object
                        time_value = time_value.isoformat()
                    else:
                        # Assume it's already a string in ISO format
                        time_value = str(time_value)
                else:
                    time_value = None

                # Document line
                bulk_data.append({
                    "id": str(story['id']),
                    "title": story.get('title', ''),
                    "url": story.get('url', ''),
                    "score": story.get('score', 0),
                    "author": story.get('author', ''),
                    "time": time_value,
                    "comments": story.get('comments', 0),
                    "document": documents[j],
                    "embedding": embeddings[j]
                })

            response = self.client.bulk(body=bulk_data)
            if response.get('errors'):
                print(f"Errors in batch {i//batch_size + 1}:")
                for item in response['items']:
                    if 'error' in item.get('index', {}):
                        print(f"  Error: {item['index']['error']}")
            else:
                print(f"Added batch {i//batch_size + 1} ({batch_end}/{len(stories)} stories)")

        self.client.indices.refresh(index=self.index_name)
        count = self.client.count(index=self.index_name)['count']
        print(f"Total items in index: {count}")

    def search(self, query: str, n_results: int = 10) -> List[Dict]:
        """
        Search for stories semantically similar to the query.

        Args:
            query: Search query
            n_results: Number of results to return

        Returns:
            List of search results with metadata and similarity scores
        """
        query_embedding = self.model.encode([query]).tolist()[0]

        search_body = {
            "size": n_results,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": n_results
                    }
                }
            }
        }

        response = self.client.search(index=self.index_name, body=search_body)

        search_results = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            result = {
                'id': source['id'],
                'title': source['title'],
                'url': source['url'],
                'score': source['score'],
                'author': source['author'],
                'time': str(source['time']),
                'comments': source['comments'],
                'similarity': hit['_score'],
                'document': source['document']
            }
            search_results.append(result)

        return search_results

    def count(self) -> int:
        """Return the number of items in the index."""
        return self.client.count(index=self.index_name)['count']

    def clear(self):
        """Clear all data from the index."""
        if self.client.indices.exists(index=self.index_name):
            self.client.indices.delete(index=self.index_name)
        self._create_index()
        print("Index cleared")
