"""
Test that all dependencies are installed correctly.
"""
import sys


def test_imports():
    """Test that all required packages can be imported."""
    required_packages = [
        ('datasets', 'datasets'),
        ('duckdb', 'duckdb'),
        ('sentence_transformers', 'sentence-transformers'),
        ('opensearchpy', 'opensearch-py'),
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('pydantic', 'pydantic'),
    ]

    print("🧪 Testing package imports...\n")

    all_good = True
    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
            print(f"✅ {package_name}")
        except ImportError as e:
            print(f"❌ {package_name} - {e}")
            all_good = False

    print()

    if all_good:
        print("✅ All dependencies are installed correctly!")
        print("\nYou're ready to build the search index:")
        print("  python build_index.py")
        return 0
    else:
        print("❌ Some dependencies are missing.")
        print("\nPlease install them:")
        print("  pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    sys.exit(test_imports())
