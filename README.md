# OpenResearch

An automated research assistant that uses LLMs and web search to conduct comprehensive research on any topic.

> **Getting Started in 30 Seconds**
> 
> **Windows**: Run `run.bat docker` then `run.bat cli` in Command Prompt
> 
> **Mac/Linux**: Run `chmod +x run.sh` then `./run.sh docker` and `./run.sh cli` in Terminal
> 
> First time? See the [Quick Start Guide](#quick-start-guide) below.

## Quick Start Guide

### For First-Time Users

1. **Prerequisites**:
   - Install [Docker](https://www.docker.com/products/docker-desktop/) and Docker Compose (usually included with Docker Desktop)
   - Make sure you have Python 3.10 or newer installed

2. **Get a HuggingFace API Token**:
   - Create a free account at [HuggingFace](https://huggingface.co/)
   - Go to your profile → Settings → Access Tokens
   - Create a new token and copy it

3. **Set Up Your Environment**:
   - Copy the `.env.example` file to `.env` in the project folder
   - Replace `your_huggingface_token_here` with your actual token
   - Example: `HUGGINGFACE_API_TOKEN=hf_abcdefghijklmnopqrstuvwxyz`

4. **Run the Application with Docker (Recommended)**:

   **On Windows**:
   ```
   # Start all services with Docker (including SearxNG for web searches)
   run.bat docker

   # In a new terminal window, start the CLI interface
   run.bat cli
   ```

   **On Linux/macOS**:
   ```
   # Make the script executable (first time only)
   chmod +x run.sh

   # Start all services with Docker (including SearxNG for web searches)
   ./run.sh docker

   # In a new terminal window, start the CLI interface
   ./run.sh cli
   ```

5. **Alternative: Run Without Docker (NOT recommended for first-time users)**:

   **On Windows**:
   ```
   # Install dependencies (first time only)
   run.bat install

   # Start the API server
   run.bat api

   # In a new terminal window, start the CLI interface
   run.bat cli
   ```

   **On Linux/macOS**:
   ```
   # Make the script executable (first time only)
   chmod +x run.sh

   # Install dependencies (first time only)
   ./run.sh install

   # Start the API server
   ./run.sh api

   # In a new terminal window, start the CLI interface
   ./run.sh cli
   ```

   > **Note**: Running without Docker will disable SearxNG web search functionality, significantly limiting research capabilities. Docker is strongly recommended.

6. **Start Researching**:
   - Enter your research question when prompted
   - Configure your research parameters (or accept the defaults)
   - Answer any clarification questions
   - Wait for your research report to be generated

### What to Expect

When you run the application, here's what will happen:

1. **Configuration**: You'll be asked to select an AI model, research speed, output format, and depth.
2. **Clarification**: The system may ask you 2-3 questions to better understand your research needs.
3. **Research Process**: You'll see a progress bar as the system:
   - Breaks down your query into sub-questions
   - Searches for information on each sub-question
   - Summarizes and analyzes the findings
4. **Final Report**: When complete, you'll receive a comprehensive research report with:
   - Executive summary
   - Detailed findings organized by topic
   - Analysis and implications
   - References to sources

The entire process typically takes 5-15 minutes depending on your research depth settings.

### For Returning Users

**On Windows**:
```
# Start Docker services (if not already running)
run.bat docker

# In a new terminal window
run.bat cli
```

**On Linux/macOS**:
```
# Start Docker services (if not already running)
./run.sh docker

# In a new terminal window
./run.sh cli
```

## Features

- Interactive research sessions with clarification questions
- Automated web search and information gathering
- Fact-checking and summarization
- Customizable research depth and output formats
- RESTful API for integration with other applications

## Detailed Usage Guide

### Using the Command-Line Interface (CLI)

The CLI is the easiest way to use OpenResearch. It provides an interactive experience with real-time progress updates.

#### Basic Usage

```bash
# On Windows (after starting Docker services)
run.bat cli

# On Linux/macOS (after starting Docker services)
./run.sh cli
```

#### With Command-Line Options

```bash
# Specify a research query directly
python cli.py --query "What are the latest advancements in quantum computing?"

# Save the report to a file
python cli.py --query "What are the latest advancements in quantum computing?" --save report.md

# Use quiet mode (minimal output, only shows the final report)
python cli.py --quiet
# Or with the run scripts
run.bat cli-quiet  # Windows
./run.sh cli-quiet  # Linux/macOS
```

#### Research Configuration Options

When running the CLI, you'll be prompted to configure your research:

1. **LLM Model**: Choose which AI model to use for your research
2. **Research Speed**:
   - **Fast**: Quicker results but less comprehensive
   - **Deep**: More thorough research but takes longer
3. **Output Format**:
   - **Full Report**: Comprehensive with sections and details
   - **Executive Summary**: Concise overview with key points
   - **Bullet List**: Just the essential facts in bullet points
4. **Research Depth and Breadth** (1-5):
   - 1 = Basic overview
   - 5 = Extremely detailed
5. **Skip Clarification**: Choose whether to skip clarification questions

### Advanced Setup Options

#### Running with Docker (Recommended)

The Docker setup provides all necessary services including the SearxNG search engine:

```bash
# Build and start all services
run.bat docker  # Windows
./run.sh docker  # Linux/macOS

# Access the API at http://localhost:8001
```

Then use the CLI to interact with the API:

```bash
run.bat cli  # Windows
./run.sh cli  # Linux/macOS
```

#### Running the API Server Without Docker (Limited Functionality)

If you cannot use Docker for some reason:

```bash
# On Windows
run.bat api

# On Linux/macOS
./run.sh api
```

The API will be available at http://localhost:8001, but SearxNG search functionality will be limited.

## Troubleshooting

### Common Issues

1. **"Error connecting to API"**:
   - Make sure the API server is running
   - Check that you're using the correct API URL (default is http://localhost:8001)

2. **"Error with HuggingFace API"**:
   - Verify your HuggingFace API token is correct in the `.env` file
   - Check your internet connection

3. **"Research appears stalled"**:
   - The CLI will automatically continue if research stalls
   - You can manually force continuation by pressing Ctrl+C and restarting with the same session ID

4. **"Failed to search with SearxNG"**:
   - Make sure you're running the application with Docker (`run.bat docker`)
   - If SearxNG fails after many searches, it might be rate-limited - try again later

### Getting Help

If you encounter issues not covered here, please:
1. Check the logs for error messages
2. Ensure all dependencies are installed correctly
3. Try running with the `--quiet` option to see if the issue persists

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

For developers who want to integrate with the API directly:

- `POST /research/create` - Create a new research session
- `GET /research/{session_id}` - Get the status of a research session
- `POST /research/{session_id}/clarify` - Submit answers to clarification questions
- `DELETE /research/{session_id}` - Cancel a research session

## License

MIT