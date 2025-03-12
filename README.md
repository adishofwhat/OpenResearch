# OpenResearch

An automated research assistant that uses LLMs and web search to conduct comprehensive research on any topic.

## Features

- Interactive research sessions with clarification questions
- Automated web search and information gathering
- Fact-checking and summarization
- Customizable research depth and output formats
- RESTful API for integration with other applications

## Project Structure

```
app/
├── __init__.py                  # Package initialization
├── main.py                      # FastAPI application entry point
├── agents/                      # Research agent components
│   ├── __init__.py
│   ├── orchestrator.py          # Research workflow orchestrator
│   ├── prompts.py               # LLM prompts for research agents
│   └── research_agents.py       # Individual research agent functions
├── models/                      # Data models and schemas
│   ├── __init__.py
│   ├── llm.py                   # LLM configuration and setup
│   └── schemas.py               # Pydantic models for the application
├── routes/                      # API routes
│   ├── __init__.py
│   └── research_routes.py       # Research API endpoints
└── services/                    # External services integration
    ├── __init__.py
    ├── database.py              # Weaviate vector database service
    └── search_api.py            # SearxNG search service
```

## API Endpoints

- `POST /research/create` - Create a new research session
- `GET /research/{session_id}` - Get the status of a research session
- `POST /research/{session_id}/clarify` - Submit answers to clarification questions
- `DELETE /research/{session_id}` - Cancel a research session

## Setup and Installation

### Prerequisites

- Docker and Docker Compose
- Python 3.10+
- HuggingFace API token (for LLM access)

### Environment Variables

Create a `.env` file with the following variables:

```
HUGGINGFACE_API_TOKEN=your_huggingface_token
```

### Running with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Access the API at http://localhost:8001
```

### Running Locally (Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload --port 8001
```

## Usage Example

```python
import requests

# Create a research session
response = requests.post(
    "http://localhost:8001/research/create",
    json={
        "query": "What are the latest advancements in quantum computing?",
        "config": {
            "output_format": "full_report",
            "research_speed": "deep",
            "depth_and_breadth": 3
        }
    }
)

session_id = response.json()["session_id"]

# Check status and get clarification questions
status = requests.get(f"http://localhost:8001/research/{session_id}")

# Submit clarification answers
if status.json()["status"] == "clarification_needed":
    questions = status.json()["clarification_questions"]
    answers = {q: "My answer to: " + q for q in questions}
    
    requests.post(
        f"http://localhost:8001/research/{session_id}/clarify",
        json={"answers": answers}
    )

# Poll for completion
while True:
    status = requests.get(f"http://localhost:8001/research/{session_id}")
    if status.json()["status"] == "completed":
        print(status.json()["final_report"])
        break
    elif status.json()["status"] == "error":
        print("Error:", status.json()["errors"])
        break
```

## License

MIT