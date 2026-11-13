"""
Arthsavora OpenAPI Specification Generator
Extracts and serializes the complete, authoritative OpenAPI 3.1 schema
from the FastAPI application instance for frontend client generation and contract verification.
"""

import argparse
import json
import os
import sys

# Ensure backend root is in Python module search path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.main import app


def generate_openapi_spec(output_path: str = "docs/openapi.json") -> dict:
    """Generates the OpenAPI specification and writes it to disk."""
    openapi_schema = app.openapi()
    
    # Resolve absolute path relative to repository root if needed
    repo_root = os.path.abspath(os.path.join(backend_root, ".."))
    resolved_path = os.path.join(repo_root, output_path) if not os.path.isabs(output_path) else output_path
    
    os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
    with open(resolved_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)

    routes_count = len(openapi_schema.get("paths", {}))
    components_count = len(openapi_schema.get("components", {}).get("schemas", {}))

    print(f"OpenAPI Schema exported successfully to: {resolved_path}")
    print(f"Summary: {routes_count} paths, {components_count} schema components (OpenAPI {openapi_schema.get('openapi')})")
    return openapi_schema


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Arthsavora OpenAPI JSON Specification")
    parser.add_argument(
        "--output",
        default="docs/openapi.json",
        help="Target output file path relative to repo root (default: docs/openapi.json)",
    )
    args = parser.parse_args()
    generate_openapi_spec(args.output)
