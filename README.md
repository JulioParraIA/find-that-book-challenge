# 📚 Find That Book

**Technical Challenge for CBTW** — A book discovery application that takes messy, plain-text queries and uses AI to find the right book.

> Enter something like *"tolkien hobbit illustrated deluxe 1937"* and the app will interpret your intent, search Open Library, and return ranked results with covers, authors, and direct links.

## 🔗 Live Demo

| Service | URL |
|---------|-----|
| **Frontend** | [jolly-rock-06166d50f.6.azurestaticapps.net](https://jolly-rock-06166d50f.6.azurestaticapps.net) |
| **Backend API** | [ca-cbtw-books-api.agreeablesand-cb694fac.eastus2.azurecontainerapps.io](https://ca-cbtw-books-api.agreeablesand-cb694fac.eastus2.azurecontainerapps.io/docs) |

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Azure Infrastructure](#azure-infrastructure)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [API Contract](#api-contract)
- [Local Development](#local-development)
- [Testing](#testing)
- [CI/CD Pipeline](#cicd-pipeline)
- [Design Decisions](#design-decisions)
- [Future Improvements](#future-improvements)

---

## Overview

**Find That Book** is a full-stack application built as a technical challenge for **CBTW**. The problem it solves: users often remember fragments about a book — a partial title, an author's last name, a year, or random keywords — but can't find it through a standard search engine. This app leverages Claude AI to interpret those messy inputs and match them against Open Library's catalog.

### Key Features

- **AI-Powered Query Interpretation** — Claude Sonnet 4 extracts structured fields (title, author, keywords) from free-form text.
- **Multi-Strategy Matching** — Exact, normalized, variant, and near-match title comparisons with Jaccard similarity scoring.
- **Smart Deduplication** — Groups duplicate editions by canonical work and selects the best representative.
- **Primary Author Resolution** — Filters out illustrators, editors, translators, and narrators to surface the actual author.
- **Responsive UI** — Clean, dark-themed interface with skeleton loading states and example queries.

---

## Architecture

```
┌─────────────────────┐         ┌──────────────────────────┐         ┌──────────────────┐
│                     │  POST   │                          │  HTTP   │                  │
│   React Frontend    │────────▶│   FastAPI Backend         │────────▶│  Open Library    │
│   (Static Web App)  │◀────────│   (Container App)        │◀────────│  API             │
│                     │  JSON   │                          │  JSON   │                  │
└─────────────────────┘         └─────────┬────────────────┘         └──────────────────┘
                                          │
                                          │ API Call
                                          ▼
                                ┌──────────────────┐
                                │                  │
                                │  Claude AI       │
                                │  (Anthropic API) │
                                │                  │
                                └──────────────────┘
```

**Request Flow:**
1. User enters a messy text query in the frontend.
2. Frontend sends `POST /api/search` to the backend.
3. Backend sends the query to Claude AI for field extraction (title, author, keywords).
4. Backend searches Open Library using the extracted fields.
5. Results are deduplicated, scored, ranked, and returned to the frontend.
6. Frontend displays the top 5 candidates with covers, metadata, and match explanations.

---

## Azure Infrastructure

All resources are deployed in the **East US 2** region under the resource group `GR-CBTW-CHALLENGUE`.

| Azure Service | Resource Name | Purpose |
|---------------|---------------|---------|
| **Resource Group** | GR-CBTW-CHALLENGUE | Logical container for all project resources |
| **Azure Container Registry** | acrcbtwbooks | Stores Docker images for the backend API |
| **Azure Container Apps** | ca-cbtw-books-api | Runs the FastAPI backend as a serverless container |
| **Container Apps Environment** | cae-cbtw-books | Shared environment for container apps with logging |
| **Azure Static Web Apps** | swa-cbtw-books | Hosts the React frontend (free tier) |
| **Azure Key Vault** | kv-cbtw-books | Secure storage for API keys and secrets |
| **Log Analytics Workspace** | workspace-P8kT | Centralized logging for container apps |

### Why These Services?

- **Container Apps** was chosen over App Service or AKS for its simplicity, scale-to-zero capability, and native Docker support — ideal for a single-API microservice.
- **Static Web Apps** provides free hosting with global CDN for the React SPA, with automatic HTTPS.
- **Container Registry** (Basic tier) keeps Docker images private and close to the deployment target, minimizing pull latency.
- **Key Vault** ensures API keys are never hardcoded or exposed in source control.

---

## Tech Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.13 | Runtime |
| FastAPI | 0.115.x | Web framework with automatic OpenAPI docs |
| Anthropic SDK | 0.52.x | Claude AI integration for query interpretation |
| httpx | 0.28.x | Async HTTP client for Open Library API |
| Pydantic Settings | 2.7.x | Configuration management with env var validation |
| Uvicorn | 0.34.x | ASGI server |
| pytest | 8.3.x | Testing framework |

### Frontend
| Technology | Purpose |
|------------|---------|
| React 18 | UI library |
| Vite | Build tool and dev server |
| Tailwind CSS | Utility-first styling |

### AI Model
| Model | Identifier | Purpose |
|-------|------------|---------|
| Claude Sonnet 4 | `claude-sonnet-4-20250514` | Extracts structured fields from messy text queries |

### External APIs
| API | Purpose |
|-----|---------|
| [Open Library Search API](https://openlibrary.org/dev/docs/api/search) | Book catalog search |
| [Open Library Covers API](https://covers.openlibrary.org) | Book cover images |

---

## Project Structure

```
find-that-book-challenge/
├── .github/
│   └── workflows/
│       ├── deploy-backend.yml        # CI/CD: Build, push, deploy backend
│       └── deploy-frontend.yml       # CI/CD: Build and deploy frontend
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                 # Settings from environment variables
│   │   ├── main.py                   # FastAPI app initialization + CORS
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py             # POST /api/search, GET /api/health
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py            # Pydantic request/response models
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── ai_extractor.py       # Claude AI integration
│   │       ├── deduplicator.py       # Edition deduplication + author resolution
│   │       ├── matcher.py            # Scoring and ranking engine
│   │       ├── normalizer.py         # Text normalization utilities
│   │       └── open_library_client.py # Open Library API client
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py               # Shared fixtures and mocks
│   │   ├── test_api.py               # Integration tests (9 tests)
│   │   ├── test_deduplicator.py      # Deduplication tests (14 tests)
│   │   ├── test_matcher.py           # Scoring/ranking tests (18 tests)
│   │   └── test_normalizer.py        # Normalization tests (20 tests)
│   ├── .env.example
│   ├── Dockerfile                    # Production container image
│   └── requirements.txt
├── frontend/
│   ├── public/
│   │   └── favicon.svg
│   ├── src/
│   │   ├── App.css
│   │   ├── App.jsx                   # Main app component + search orchestration
│   │   ├── main.jsx                  # React entry point
│   │   ├── components/
│   │   │   ├── BookCard.jsx          # Individual book result card
│   │   │   ├── LoadingState.jsx      # Skeleton loading cards
│   │   │   ├── ResultsList.jsx       # Results list container
│   │   │   └── SearchBar.jsx         # Search input with examples
│   │   └── services/
│   │       └── api.js                # HTTP client for backend API
│   ├── Dockerfile.dev                # Dev container for local development
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   └── vite.config.js
├── .gitignore
├── docker-compose.yml                # Local development with Docker
├── README.md
└── setup_project.sh
```

---

## How It Works

### 1. AI Field Extraction
Claude receives the raw query with a system prompt instructing it to extract structured JSON:
```json
{
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "keywords": ["illustrated", "1937"]
}
```

### 2. Open Library Search
The extracted fields are used to query Open Library's Search API. If the primary search returns no results, the system falls back to a combined keyword search, then an author-only search.

### 3. Deduplication
Open Library often returns multiple editions of the same work. The deduplicator groups results by work key and selects the best edition based on: cover availability, publish year, author data, and edition count.

### 4. Scoring & Ranking
Each candidate receives a composite score:

| Match Type | Points |
|------------|--------|
| Exact title match | 100 |
| Known title variant (e.g., "Moby Dick" ↔ "The Whale") | 80 |
| Near title match (Jaccard similarity ≥ 40%) | Up to 60 |
| Primary author match | 50 |
| Contributor-only author match | 20 |
| Year keyword match | 15 |
| General keyword match | 10 |

The top 5 candidates are returned with explanations of why each was matched.

---

## API Contract

### POST /api/search

**Request:**
```json
{
  "query": "tolkien hobbit illustrated deluxe 1937"
}
```

**Response (200):**
```json
{
  "query": "tolkien hobbit illustrated deluxe 1937",
  "extracted_fields": {
    "title": "The Hobbit",
    "author": "J.R.R. Tolkien",
    "keywords": ["illustrated", "deluxe", "1937"]
  },
  "candidates": [
    {
      "title": "The Hobbit",
      "author": "J.R.R. Tolkien",
      "first_publish_year": 1937,
      "open_library_id": "/works/OL27479W",
      "open_library_url": "https://openlibrary.org/works/OL27479W",
      "cover_url": "https://covers.openlibrary.org/b/id/12345-M.jpg",
      "explanation": "Exact title match: 'The Hobbit'; J.R.R. Tolkien is primary author"
    }
  ],
  "total_results": 20
}
```

### GET /api/health

**Response (200):**
```json
{
  "status": "healthy",
  "service": "find-that-book-api"
}
```

---

## Local Development

### Prerequisites
- Docker and Docker Compose
- An Anthropic API key

### Setup

1. Clone the repository:
```bash
git clone https://github.com/JulioParraIA/find-that-book-challenge.git
cd find-that-book-challenge
```

2. Create a `.env` file in the `backend/` directory:
```bash
cp backend/.env.example backend/.env
# Edit backend/.env and add your ANTHROPIC_API_KEY
```

3. Start both services:
```bash
docker-compose up --build
```

4. Access the application:
   - Frontend: http://localhost:5173
   - Backend API docs: http://localhost:8000/docs

---

## Testing

The test suite includes **83 tests** covering all backend services:

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_normalizer.py | 20 | Text normalization, diacritics, variants, similarity |
| test_matcher.py | 18 | Title/author/keyword matching, scoring, ranking |
| test_deduplicator.py | 14 | Edition dedup, best edition selection, author resolution |
| test_api.py | 9 | Health endpoint, validation, search flow, error handling |
| conftest.py | — | Shared fixtures, mock clients, sample data |

### Running Tests

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

All tests run without external dependencies (Claude API and Open Library are mocked).

---

## CI/CD Pipeline

Two GitHub Actions workflows automate deployment on every push to `main`:

### deploy-backend.yml
**Trigger:** Changes in `backend/`
1. Checkout code
2. Login to Azure and ACR
3. Build Docker image and push to Azure Container Registry
4. Deploy new image to Azure Container Apps

### deploy-frontend.yml
**Trigger:** Changes in `frontend/`
1. Checkout code
2. Setup Node.js 20
3. Install dependencies and build with Vite
4. Deploy to Azure Static Web Apps

### GitHub Secrets Required
| Secret | Description |
|--------|-------------|
| `AZURE_CREDENTIALS` | Service principal JSON for Azure login |
| `ACR_USERNAME` | Azure Container Registry username |
| `ACR_PASSWORD` | Azure Container Registry password |
| `SWA_DEPLOYMENT_TOKEN` | Static Web Apps deployment token |

---

## Design Decisions

1. **Claude Sonnet 4 over Haiku** — Sonnet provides better accuracy for interpreting ambiguous queries while remaining cost-effective. The `max_tokens=300` limit keeps responses fast and focused.

2. **Multi-strategy matching over simple search** — Rather than passing the raw query directly to Open Library, the scoring system considers exact matches, known variants (e.g., "Frankenstein" ↔ "The Modern Prometheus"), and partial similarity, producing more relevant results.

3. **Deduplication at the application level** — Open Library returns multiple editions of the same work. Deduplicating by work key and selecting the edition with the most metadata ensures clean results.

4. **Contributor filtering for author resolution** — Open Library lists illustrators, editors, and translators alongside authors. The deduplicator filters these based on role indicators to surface the true author.

5. **Serverless architecture** — Azure Container Apps with scale-to-zero keeps costs minimal for a challenge project while maintaining the ability to handle traffic spikes.

6. **Frontend-backend separation** — The React SPA is hosted independently on Static Web Apps, communicating with the backend via REST. This allows independent scaling and deployment.

---

## Future Improvements

- **Caching layer** — Add Redis or in-memory caching for repeated queries to reduce Claude API calls and Open Library load.
- **Rate limiting** — Implement request throttling to protect the Anthropic API key from abuse.
- **Search history** — Allow users to see their recent searches.
- **Advanced filters** — Let users filter results by year range, language, or availability.
- **Fuzzy author matching** — Use Levenshtein distance for author name comparisons instead of substring matching.
- **E2E tests** — Add Playwright or Cypress tests for the frontend.
- **Key Vault integration** — Reference API keys from Azure Key Vault as Container Apps secrets instead of direct environment variables.
- **Monitoring and alerting** — Configure Azure Application Insights for performance monitoring and error tracking.

---

## Author

**Julio Parra** — Built for the CBTW Technical Challenge, March 2026.