# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Type**: Python FastAPI backend + React TypeScript frontend
**Core**: Knowledge graph (Neo4j) + GraphRAG for battery disassembly planning
**Entry point**: `src/main.py`

A three-layer knowledge graph system for intelligent battery disassembly planning with natural language query support.

---

## Development Commands

### Backend (from project root)
```bash
uvicorn src.main:app --reload --port 8000
python -m uvicorn src.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend && npm run dev
cd frontend && npm run build  # production build
```

### Docker
```bash
docker-compose up -d
docker-compose logs -f backend
docker-compose down
```

### Tests
```bash
python -m pytest tests/ -v                           # all tests
python -m pytest tests/<module>/ -v                # single module
python -m pytest tests --cov=src --cov-report=html   # with coverage
python -m pytest tests/<module>/test_specific.py::test_name -v  # single test
```

---

## Architecture

### Three-Layer Knowledge Graph

| Layer | Type | Description | Cross-layer relations |
|-------|------|-------------|----------------------|
| L1 | Component | Disassembly parts/steps (user-specified) | L1→L2: REFERENCE_OF, L1→L3: CONSTRAINED_BY |
| L2 | Document + Entity | Reference documents (PDF imported) | L2→L3: DEFINITION_OF |
| L3 | Term | Extracted terminology definitions | L1→L3: CONSTRAINED_BY |

### Core Modules

```
src/
├── main.py                 # FastAPI entry, includes all routers
├── config.py               # Configuration loader (from config.yaml)
├── logs.py                 # Logging setup
├── kg/                     # Neo4j/Milvus clients
├── graphrag/               # GraphRAG inference
│   ├── query_rewriter.py   # Query expansion
│   ├── retriever.py        # Multi-path retrieval (Component/Document/Term)
│   ├── ranker.py           # Evidence ranking
│   ├── generator.py        # LLM response generation
│   ├── constrained_retriever.py
│   ├── cross_layer_retriever.py  # Cross-layer reference creation
│   └── feedback.py         # Iterative evidence supplementation
├── sequence/               # Disassembly planning
│   ├── planner.py          # Main orchestration
│   ├── cycle_detector.py   # Tarjan algorithm for dependency cycles
│   ├── topological_sort.py # Sequence ordering
│   └── time_estimator.py   # MTM-based time estimation
├── allocator/              # Human-robot allocation
│   ├── scorer.py           # LLM 9-factor scoring
│   ├── as_calculator.py    # AS score computation
│   ├── entropy_weight.py   # Weight calculation
│   └── batch_scorer.py     # Batch scoring
├── cross_layer/           # Cross-layer connection builder
│   ├── batch_builder.py    # Batch processing for L2→L3 connections
│   ├── embedder.py         # Embedding generation
│   ├── llm_judge.py        # LLM-based entity matching
│   ├── merger.py           # Connection merging
│   └── rules.py            # Cross-layer rules
├── importer/              # Document import
│   ├── pdf_parser.py      # PyMuPDF parsing
│   ├── path_classifier.py # Path classification
│   └── importer.py        # Import orchestration
├── graph_output/          # Output generation
│   ├── generator.py       # Main output
│   ├── mermaid_gen.py     # Mermaid flowchart
│   └── json_builder.py    # JSON structure
└── api/                   # FastAPI routes
    ├── routes.py           # Core /api/v1 routes
    ├── graph_routes.py     # Graph /api/v1/graph/*
    ├── query_routes.py     # Query /api/v1/query/*
    ├── import_routes.py    # Import /api/v1/import/*
    ├── cross_layer_routes.py
    ├── admin_routes.py     # Admin endpoints
    ├── schemas.py           # Pydantic models
    └── middleware.py
```

### Frontend Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── GanttChart.tsx     # Gantt chart visualization
│   │   ├── GraphView/         # Knowledge graph visualization
│   │   ├── SequenceView/      # Disassembly sequence visualization
│   │   └── QueryPanel/        # Query interface
│   ├── pages/                 # Route pages
│   └── api/client.ts          # API client
└── vite.config.ts             # Dev server with /api proxy to backend:8000
```

---

## Configuration

### Environment (.env)
Copy `.env.example` to `.env`. Required variables:
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` — Neo4j connection
- `OPENAI_API_KEY`, `OPENAI_BASE_URL` — LLM access
- `MODEL=gpt-4o`, `TEMPERATURE=0.1`, `MAX_TOKENS=2000`

### config.yaml
System parameters for MTM timing, AS scoring, thresholds, RAG retrieval. **Do not commit secrets here.**

### pytest.ini
```
pythonpath = .
testpaths = tests
```
Python imports in tests are relative to project root, not `src/`.

---

## Key API Endpoints

| Method | Path | Function |
|--------|------|----------|
| GET | /api/v1/health | Health check |
| POST | /api/v1/disassembly/plan | Main disassembly planning |
| GET | /api/v1/graph/nodes | Get all nodes |
| POST | /api/v1/query/ask | Natural language query |
| POST | /api/v1/import/l2 | L2 PDF import |
| POST | /api/v1/cross-layer/build | Build cross-layer connections |
| POST | /admin/components/promote | Promote L2 to L1 |

---

## Ports (docker-compose host mappings)
- Frontend: 3090 (container 3000)
- Backend API: 8000
- Neo4j Browser: 17474
- Neo4j Bolt: 17687
- Milvus: 19530
