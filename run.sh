#!/bin/bash

# OpenResearch run script
# This script provides a simple way to run the OpenResearch application

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print a header
print_header() {
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${BLUE}       OpenResearch Application       ${NC}"
    echo -e "${BLUE}=======================================${NC}"
    echo ""
}

# Function to print usage
print_usage() {
    echo -e "Usage: ${YELLOW}./run.sh [OPTION]${NC}"
    echo ""
    echo "Options:"
    echo -e "  ${GREEN}api${NC}        Start the API server"
    echo -e "  ${GREEN}cli${NC}        Run the CLI interface"
    echo -e "  ${GREEN}cli-quiet${NC}  Run the CLI interface in quiet mode (minimal output)"
    echo -e "  ${GREEN}docker${NC}     Start all services with Docker Compose"
    echo -e "  ${GREEN}docker-build${NC} Rebuild and start all services"
    echo -e "  ${GREEN}install${NC}    Install dependencies"
    echo -e "  ${GREEN}help${NC}       Show this help message"
    echo ""
}

# Function to install dependencies
install_deps() {
    echo -e "${BLUE}Installing API dependencies...${NC}"
    pip install -r requirements.txt
    
    echo -e "${BLUE}Installing CLI dependencies...${NC}"
    pip install -r cli_requirements.txt
    
    echo -e "${GREEN}Dependencies installed successfully!${NC}"
}

# Function to start the API server
start_api() {
    echo -e "${BLUE}Starting API server...${NC}"
    echo -e "${YELLOW}API will be available at http://localhost:8001${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
}

# Function to run the CLI
run_cli() {
    echo -e "${BLUE}Starting CLI interface...${NC}"
    echo ""
    python cli.py "$@"
}

# Function to run the CLI in quiet mode
run_cli_quiet() {
    echo -e "${BLUE}Starting CLI interface in quiet mode...${NC}"
    echo ""
    python cli.py --quiet "$@"
}

# Function to start Docker Compose
start_docker() {
    echo -e "${BLUE}Starting services with Docker Compose...${NC}"
    echo -e "${YELLOW}This may take a few minutes${NC}"
    echo ""
    docker-compose up
}

# Function to rebuild and start Docker Compose
rebuild_docker() {
    echo -e "${BLUE}Rebuilding and starting services with Docker Compose...${NC}"
    echo -e "${YELLOW}This may take a few minutes${NC}"
    echo ""
    docker-compose up --build
}

# Main script
print_header

# Check command line arguments
if [ $# -eq 0 ]; then
    print_usage
    exit 0
fi

case "$1" in
    api)
        start_api
        ;;
    cli)
        shift
        run_cli "$@"
        ;;
    cli-quiet)
        shift
        run_cli_quiet "$@"
        ;;
    docker)
        start_docker
        ;;
    docker-build)
        rebuild_docker
        ;;
    install)
        install_deps
        ;;
    help)
        print_usage
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        print_usage
        exit 1
        ;;
esac 