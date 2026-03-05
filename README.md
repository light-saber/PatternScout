# PatternScout

AI-powered UX pattern research platform for Product Managers.

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/light-saber/PatternScout.git
cd PatternScout
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required:
- `GOOGLE_API_KEY` - Google Custom Search API key
- `GOOGLE_CX` - Google Custom Search Engine ID

Get these at: https://developers.google.com/custom-search/v1/overview

### 3. Install Dependencies

Using uv (recommended):
```bash
uv sync
```

Or with pip:
```bash
pip install -r requirements.txt
```

### 4. Setup Ollama Models

```bash
# Install Ollama: https://ollama.com/download

# Pull vision model for screenshot analysis
ollama pull qwen2.5-vl

# Pull text model for clustering and hybrid generation
ollama pull qwen3.5
```

### 5. Run the Application

Terminal 1 - Backend:
```bash
uv run uvicorn app.main:app --reload
```

Terminal 2 - Frontend:
```bash
uv run streamlit run frontend/app.py
```

Or with separate virtual envs:
```bash
# Backend
cd PatternScout
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd PatternScout
source .venv/bin/activate
streamlit run frontend/app.py --server.port 8501
```

### 6. Access the App

- **Frontend**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Usage

1. **Search**: Enter a UI pattern (e.g., "e-commerce checkout flow")
2. **Wait**: The system scrapes images and analyzes them with AI
3. **Browse**: View screenshots with AI-generated tags and descriptions
4. **Filter**: Use tags to narrow down patterns

## Project Structure

```
PatternScout/
├── app/                    # FastAPI backend
│   ├── api/v1/endpoints/   # API routes
│   ├── core/               # Config, database
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic schemas
│   ├── scrapers/           # Google Images client
│   └── services/           # Ollama inference
├── frontend/               # Streamlit frontend
│   └── app.py
├── PRD.md                  # Product Requirements
├── .env.example            # Environment template
└── pyproject.toml          # Dependencies
```

## Development Roadmap

- [x] Sprint 1: Core search + scraping + analysis
- [ ] Sprint 2: Pattern clustering + hybrid generation
- [ ] Sprint 3: Comparison view + export functionality

## Architecture

- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Scraping**: Google Custom Search API + Scrapling
- **AI**: Ollama (Qwen2.5-VL for vision, Qwen 3.5 for text)
- **Frontend**: Streamlit (MVP) → React (v2 if traction)

## License

Internal use at Walmart. Not for public distribution.
