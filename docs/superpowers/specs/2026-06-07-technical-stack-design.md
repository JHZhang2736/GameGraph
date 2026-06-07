# Technical Stack Design Spec

## 1. Purpose

This document defines the recommended technical stack for the Indie Game Idea Graph system. It translates the product design into a concrete frontend, backend, data, and development stack while avoiding implementation planning.

The goal is to choose a stack that supports fast prototyping, clear module boundaries, explainable graph reasoning, and independent testing of each product module.

## 2. Stack Decision Summary

The system should use a frontend/backend split:

```text
Frontend: Next.js + React + TypeScript
Backend: Python + FastAPI + Pydantic
Graph Database: Neo4j
Development Runtime: Docker Compose for local infrastructure
LLM Layer: Provider adapter abstraction
Progress Updates: SSE first, polling as fallback
```

This stack keeps user-facing workflow code in the frontend and keeps graph reasoning, annotation pipelines, opportunity framing, and concept generation in the backend.

## 3. Frontend Stack

### 3.1 Core Framework

Use:

- Next.js App Router
- React
- TypeScript

Rationale:

- Next.js gives a stable app structure for a workbench-style product.
- React is a strong fit for interactive editing, graph browsing, and concept comparison.
- TypeScript helps keep frontend contracts aligned with backend artifact schemas.

### 3.2 UI And Styling

Use:

- Tailwind CSS
- shadcn/ui
- Radix UI primitives
- lucide-react icons

Rationale:

- The product should feel like an efficient workbench, not a marketing page.
- shadcn/ui and Radix provide accessible controls with low design-system overhead.
- Tailwind supports fast iteration while keeping visual rules local and explicit.

### 3.3 Data Fetching And Client State

Use:

- TanStack Query for API fetching, caching, mutation states, and refresh behavior.
- URL state for filters, selected graph nodes, selected concept cards, and current workspace context.
- Small local component state only for transient UI interactions.

Rationale:

- The product has many server-backed artifacts: game profiles, design claims, opportunity frames, concept cards, and validation briefs.
- TanStack Query keeps server state explicit and testable.
- Avoiding a large global client store reduces early complexity.

### 3.4 Graph Visualization

Use:

- React Flow for the first prototype graph exploration experience.
- Consider Sigma.js later only if graph size or graph layout requirements outgrow React Flow.

Rationale:

- The MVP needs understandable graph inspection, not large-scale graph analytics.
- React Flow is easier to integrate into a workbench interface with selectable nodes, side panels, and editable relationships.

### 3.5 Frontend Responsibilities

The frontend owns:

- Developer profile entry and editing.
- Game intake forms.
- Game design profile and design claim browsing.
- Graph exploration and explanation views.
- Opportunity frame review.
- Concept card comparison.
- Prototype validation brief display.
- Long-running task progress display.

The frontend must not own:

- Graph traversal logic.
- LLM prompting logic.
- Concept scoring logic.
- Evidence-path assembly.
- Canonical artifact validation.

## 4. Backend Stack

### 4.1 Core Framework

Use:

- Python
- FastAPI
- Pydantic v2

Rationale:

- The backend will contain graph reasoning, annotation extraction, concept generation, and artifact validation.
- Python has strong ergonomics for AI workflows and graph/database integration.
- FastAPI and Pydantic make request/response contracts explicit and easy to test.

### 4.2 Backend Architecture Style

Use modular service boundaries that mirror the product modules:

- Game intake service
- Game design annotation service
- Design graph service
- Developer profile service
- Opportunity matching service
- Opportunity framing service
- Concept generation service
- Concept evaluation service
- Prototype validation service
- Audit and explanation service

Each service should receive and return typed Pydantic models. Services should avoid depending on HTTP-specific objects so they can be tested directly.

### 4.3 API Style

Use:

- REST endpoints for artifact CRUD and workflow actions.
- SSE endpoints for long-running progress updates.
- Polling fallback for environments where SSE is inconvenient.

Rationale:

- REST is sufficient for the MVP and keeps contracts easy to inspect.
- Some operations, such as game import, annotation, opportunity generation, and concept generation, may take time.
- SSE gives a simple one-way progress stream without introducing a full realtime layer.

### 4.4 LLM Integration

Use:

- A provider adapter abstraction.
- Prompt inputs based on typed artifacts, especially Opportunity Frame.
- Structured outputs validated by Pydantic.

The backend must not let generation run directly from broad user text. Concept generation must be downstream of an Opportunity Frame.

Rationale:

- The product should not be tied to one model provider.
- Typed inputs and outputs make generation failures visible.
- The Opportunity Frame protects the system from unconstrained idea generation.

## 5. Data Stack

### 5.1 Primary Database

Use:

- Neo4j as the primary database for the MVP.

Rationale:

- The core domain is graph-shaped: games connect to mechanics, experiences, constraints, innovation patterns, source claims, and concept derivation paths.
- Recommendation quality depends on traversable evidence paths, not only tabular records.
- Starting with one primary database keeps the MVP simpler.

### 5.2 PostgreSQL Decision

Do not use PostgreSQL in the first version.

Add PostgreSQL later only when the product needs:

- Multi-user accounts.
- Permissions and organizations.
- Durable task history independent of the graph.
- Billing.
- Analytics tables.
- Non-graph operational data that becomes awkward in Neo4j.

### 5.3 Data Fixtures

Use fixture data for early development:

- Seed games.
- Example game design profiles.
- Example design claims.
- Example developer profiles.
- Example opportunity frames.
- Example concept cards.

Rationale:

- Fixture data lets every module be tested before full import and generation workflows are reliable.
- Fixtures make frontend development possible before every backend path is finished.

## 6. Repository Shape

Recommended top-level structure:

```text
backend/
frontend/
data/
  fixtures/
docs/
  superpowers/
    specs/
```

The structure should keep frontend, backend, data fixtures, and design docs clearly separated.

## 7. Testing Strategy

### 7.1 Frontend Tests

Use:

- Component tests for core workbench components.
- Integration tests for API-backed views with mocked responses.
- Browser smoke tests for the main workflow once the UI exists.

Priority views:

- Developer profile form.
- Game design profile view.
- Graph explanation view.
- Opportunity frame view.
- Concept comparison view.

### 7.2 Backend Tests

Use:

- Unit tests for each service.
- Contract tests for Pydantic artifact schemas.
- Integration tests for Neo4j graph traversal.
- API tests for route behavior.

Priority behavior:

- Claims preserve evidence, confidence, and quality status.
- Opportunity frames cite evidence paths.
- Concept generation cannot bypass Opportunity Frame.
- Low-confidence claims reduce downstream confidence.
- Hard constraints block incompatible recommendations.

### 7.3 End-To-End Tests

Use a small fixture-backed flow:

```text
Seed games
-> design claims
-> graph
-> developer profile
-> opportunity frame
-> concept cards
-> validation brief
```

The first end-to-end test should use fixtures rather than live LLM calls.

## 8. Local Development

Use:

- Docker Compose for Neo4j and future local infrastructure.
- Local frontend dev server.
- Local backend dev server.
- Environment variables for credentials and provider configuration.

The MVP should be runnable locally before any hosted deployment is considered.

## 9. Deployment Direction

For the first prototype, prioritize local-first development.

Later deployment can use:

- Frontend hosted on a platform suitable for Next.js.
- Backend hosted as a Python service.
- Managed Neo4j or self-hosted Neo4j depending on cost and operational needs.

Deployment details are intentionally out of scope for the first technical stack decision.

## 10. Explicit Non-Goals

The first version should not use:

- A pure Next.js full-stack architecture.
- Django as the main backend.
- A desktop application shell.
- PostgreSQL as a second primary database.
- A full realtime websocket layer.
- A large global frontend state store.
- Multiple LLM provider implementations before the adapter boundary is proven.

These choices can be revisited after the prototype demonstrates that the core workflow works.

## 11. Success Criteria

The stack is successful if:

- Each product module can be tested independently.
- The frontend can evolve as a workbench without absorbing backend reasoning logic.
- The backend can validate every artifact shape with Pydantic.
- The graph database can explain recommendations through evidence paths.
- LLM usage is isolated behind typed adapter boundaries.
- The local development setup remains simple enough for rapid iteration.

The stack fails if:

- Graph reasoning leaks into frontend components.
- LLM prompts become scattered across route handlers.
- Low-confidence claims are treated as high-confidence data.
- Two databases are introduced before the MVP needs them.
- The project becomes harder to run locally than the prototype justifies.

## 12. Reference Documentation

- Next.js App Router: https://nextjs.org/docs/app
- FastAPI: https://fastapi.tiangolo.com/
- Neo4j Cypher: https://neo4j.com/docs/cypher/
- TanStack Query: https://tanstack.com/query/

