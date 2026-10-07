"""Export OpenAPI JSON schema from FastAPI app."""

import json
import sys
from pathlib import Path

# Ensure root directory is on sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app  # noqa: E402


def export_openapi() -> Path:
    """Generate and write openapi.json to project root."""
    schema = app.openapi()
    output_path = root_dir / "openapi.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"OpenAPI schema successfully exported to: {output_path}")
    return output_path


if __name__ == "__main__":
    export_openapi()
