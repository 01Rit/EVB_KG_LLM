# AGENTS.md

## Project Overview
- **Type**: Python FastAPI backend + React TypeScript frontend
- **Core**: Knowledge graph (Neo4j) + GraphRAG for battery disassembly planning
- **Entry point**: `src/main.py`

## Developer Commands

### Backend (from project root)
```bash
uvicorn src.main:app --reload --port 8000
# or
python src/main.py
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
Python imports in tests are relative to project root, not `src/`.

### config.yaml
System parameters for MTM timing, AS scoring, thresholds, RAG retrieval. Do not commit secrets here.

### Environment
Copy `.env.example` to `.env`. Required: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`.

## Ports (docker-compose host mappings)
- Frontend: 9333 (container 3000)
- Backend: 8000
- Neo4j: 17474 (browser), 17687 (bolt)

## Architecture

```
src/
├── main.py              # FastAPI entry, includes all routers
├── config.py            # Configuration loader
├── logs.py              # Logging setup
├── kg/                  # Neo4j/Milvus clients
├── graphrag/            # GraphRAG: query_rewriter, retriever, ranker, generator, planner
├── sequence/            # Disassembly planning: cycle_detector, topological_sort, time_estimator
├── allocator/           # Human-robot allocation: scorer, as_calculator
├── graph_output/        # Mermaid + JSON output generation
├── importer/            # PDF/document import: pdf_parser, entity_extractor
├── api/                 # FastAPI routes
│   ├── routes.py        # Core /api/v1 routes
│   ├── graph_routes.py  # Graph /api/v1/graph/*
│   ├── query_routes.py # Query /api/v1/query/*
│   ├── import_routes.py# Import /api/v1/import/*
│   ├── admin_routes.py # Admin /admin/*
│   ├── config_routes.py# Config /api/v1/config/*
│   ├── progress_routes.py
│   ├── schemas.py       # Pydantic models
│   └── middleware.py
└── utils/               # LLM client wrapper

frontend/                # React + TypeScript + Vite
tests/                   # Mirrors src/ structure
```

## Code Conventions
- Python: PEP 8, use Pydantic for data validation
- API routes use `/api/v1` prefix (except admin and progress)
- Health check: `GET /api/v1/health`
- Main disassembly endpoint: `POST /api/v1/disassembly/plan`
