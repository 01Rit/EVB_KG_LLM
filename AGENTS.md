# AGENTS.md

## Project Overview
- **Type**: Python FastAPI backend + React TypeScript frontend
- **Core**: Knowledge graph (Neo4j) + GraphRAG for battery disassembly planning
- **Entry point**: `src/main.py`

## Developer Commands

### Backend (from project root)
```bash
uvicorn src.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend && npm run dev
```

### Docker
```bash
docker-compose up -d
```

### Tests
```bash
python -m pytest tests/ -v
python -m pytest tests/<module>/ -v    # single module
python -m pytest tests --cov=src --cov-report=html  # with coverage
```

## Important Configuration

### pytest.ini
```
pythonpath = .
testpaths = tests
```
This means Python imports in tests must be relative to project root, not `src/`.

### Ports
- Frontend: 3000
- Backend: 8000
- Neo4j: 7687 (bolt), 7474 (browser)

### Environment
- Copy `.env.example` to `.env` for local development
- Required: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `OPENAI_API_KEY`
- Optional: `MILVUS_HOST`, `MILVUS_PORT`

### config.yaml
System parameters for MTM timing, AS scoring, thresholds, RAG retrieval. Do not commit secrets here.

## Architecture

```
src/
├── main.py              # FastAPI entry, includes all routers
├── config.py            # Configuration loader
├── kg/                  # Neo4j/Milvus clients
├── graphrag/            # GraphRAG: query_rewriter, retriever, ranker, generator
├── sequence/            # Disassembly planning: cycle_detector, topological_sort, time_estimator
├── allocator/           # Human-robot allocation: scorer, as_calculator
├── graph_output/        # Mermaid + JSON output generation
├── importer/            # PDF/document import: pdf_parser, entity_extractor
├── api/                 # FastAPI routes
│   ├── routes.py        # Core /api/v1 routes
│   ├── graph_routes.py
│   ├── query_routes.py
│   ├── import_routes.py
│   ├── admin_routes.py
│   ├── config_routes.py
│   └── schemas.py
└── utils/               # LLM client wrapper

frontend/                # React + TypeScript + Vite
tests/                   # Mirrors src/ structure
```

## Code Conventions
- Python: PEP 8, use Pydantic for data validation
- API routes use `/api/v1` prefix
- Health check: `GET /api/v1/health`
- Main disassembly endpoint: `POST /api/v1/disassembly/plan`
