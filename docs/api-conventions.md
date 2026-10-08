# ProjectOps API Conventions

## 1. Versioning & Base Path
All REST API endpoints are versioned under `/api/v1`.

## 2. Request & Response Standards
- **Serialization**: JSON using Pydantic v2 schemas.
- **Dates & Times**:
  - Dates use ISO 8601 strings: `YYYY-MM-DD` (e.g., `2026-10-15`).
  - Timestamps use UTC ISO 8601 strings with `Z` or `+00:00` offset (e.g., `2026-10-15T09:00:00Z`).
- **IDs**: UUID v4 strings for entities, or hierarchical identifiers for tasks (e.g., `TASK-01`).

## 3. HTTP Status Codes
- `200 OK`: Successful retrieval or synchronous operation.
- `201 Created`: Successful creation of a new resource (e.g., plan snapshot).
- `400 Bad Request`: Malformed payload or validation error.
- `404 Not Found`: Resource does not exist.
- `409 Conflict`: Version collision (e.g., attempting to overwrite an immutable plan version).
- `422 Unprocessable Content`: Domain rule validation failure (e.g., cycle detected in task graph).
- `500 Internal Server Error`: Unexpected unhandled server exception.

## 4. OpenAPI Documentation
FastAPI automatically generates the OpenAPI v3 specification available at:
- Interactive Docs: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`
