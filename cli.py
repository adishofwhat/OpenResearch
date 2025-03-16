"""
OpenResearch CLI - A user-friendly command-line interface for the OpenResearch API.
"""

import os
import sys
import json
import time
import argparse
import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import print as rprint

# Configuration
DEFAULT_API_URL = "http://localhost:8001"
CACHE_DIR = os.path.expanduser("~/.openresearch/cache")

# Initialize rich console
console = Console()

def ensure_cache_dir():
    """Ensure the cache directory exists."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)

def get_cached_session(session_id):
    """Get a cached session if it exists."""
    cache_file = os.path.join(CACHE_DIR, f"{session_id}.json")
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    return None

def save_session_to_cache(session_id, data):
    """Save session data to cache."""
    ensure_cache_dir()
    cache_file = os.path.join(CACHE_DIR, f"{session_id}.json")
    with open(cache_file, 'w') as f:
        json.dump(data, f, indent=2)

def create_research_session(api_url, query, config=None):
    """Create a new research session."""
    if config is None:
        config = {}
    
    url = f"{api_url}/research/create"
    payload = {
        "query": query,
        "config": config
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error creating research session: {str(e)}[/bold red]")
        sys.exit(1)

def get_research_status(api_url, session_id):
    """Get the status of a research session."""
    url = f"{api_url}/research/{session_id}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error getting research status: {str(e)}[/bold red]")
        return None

def submit_clarification_answers(api_url, session_id, answers):
    """Submit answers to clarification questions."""
    url = f"{api_url}/research/{session_id}/clarify"
    payload = {
        "answers": answers
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error submitting clarification answers: {str(e)}[/bold red]")
        return None

def force_continue_research(api_url, session_id):
    """Force continue the research process."""
    url = f"{api_url}/research/{session_id}/continue"
    
    try:
        response = requests.post(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error forcing research continuation: {str(e)}[/bold red]")
        return None

def display_progress(status):
    """Display the current progress of the research."""
    progress = status.get("progress", 0) * 100
    status_text = status.get("status", "unknown")
    message = status.get("message", "Research in progress...")
    
    table = Table(show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Status", status_text)
    table.add_row("Progress", f"{progress:.1f}%")
    table.add_row("Message", message)
    
    if status.get("errors") and len(status.get("errors", [])) > 0:
        errors = "\n".join(status.get("errors", []))
        table.add_row("Errors", f"[bold red]{errors}[/bold red]")
    
    console.print(Panel(table, title="Research Progress", border_style="blue"))

def handle_clarification_questions(api_url, session_id, status):
    """Handle clarification questions from the research process."""
    questions = status.get("clarification_questions", [])
    if not questions:
        return None
    
    console.print(Panel("[bold]Please answer the following clarification questions:[/bold]", border_style="yellow"))
    
    answers = {}
    for question in questions:
        # Remove the "Question X: " prefix if present
        if question.startswith("Question "):
            parts = question.split(":", 1)
            if len(parts) > 1:
                question = parts[1].strip()
        
        answer = Prompt.ask(f"[yellow]{question}[/yellow]")
        answers[question] = answer
    
    console.print("[bold green]Submitting your answers...[/bold green]")
    result = submit_clarification_answers(api_url, session_id, answers)
    
    # Cache the answers
    cached_data = get_cached_session(session_id) or {}
    cached_data["clarification_answers"] = answers
    save_session_to_cache(session_id, cached_data)
    
    return result

def monitor_research_progress(api_url, session_id, poll_interval=5):
    """Monitor the progress of a research session."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Researching...", total=100)
        
        last_status = None
        last_progress = 0
        stalled_count = 0
        max_stalled = 3  # Number of times progress can stall before offering to force continue
        
        # Track which clarification questions we've already handled
        handled_clarification_sets = set()
        
        while True:
            status = get_research_status(api_url, session_id)
            if not status:
                progress.stop()
                console.print("[bold red]Failed to get research status. Exiting.[/bold red]")
                return None
            
            current_progress = status.get("progress", 0) * 100
            current_status = status.get("status", "")
            
            # Update the progress description based on the current status
            status_description = {
                "initialized": "[cyan]Initializing research...[/cyan]",
                "clarification_needed": "[cyan]Waiting for clarification...[/cyan]",
                "query_refined": "[cyan]Refining query...[/cyan]",
                "query_decomposed": "[cyan]Breaking down research questions...[/cyan]",
                "search_completed": "[cyan]Gathering information...[/cyan]",
                "summaries_completed": "[cyan]Analyzing information...[/cyan]",
                "completed": "[green]Research completed![/green]"
            }.get(current_status, "[cyan]Researching...[/cyan]")
            
            progress.update(task, description=status_description, completed=current_progress)
            
            # Check if we need clarification
            if current_status == "clarification_needed" and status.get("clarification_questions"):
                # Create a hash of the questions to check if we've handled this set before
                questions = status.get("clarification_questions", [])
                questions_hash = hash(tuple(sorted(questions)))
                
                if questions_hash not in handled_clarification_sets:
                    progress.stop()
                    handle_clarification_questions(api_url, session_id, status)
                    handled_clarification_sets.add(questions_hash)
                    progress.start()
                    continue
            
            # Check if research is completed
            if current_status == "completed":
                progress.update(task, completed=100)
                break
            
            # Check if research is stalled (same progress for multiple checks)
            if last_progress == current_progress and last_status == current_status:
                stalled_count += 1
            else:
                stalled_count = 0
            
            # If research is stalled, automatically continue
            # But only if we're not already in a completed or error state
            if stalled_count >= max_stalled and current_status not in ["completed", "error"]:
                if current_status == "search_completed":
                    console.print("[yellow]Search phase completed. Moving to analysis phase...[/yellow]")
                elif current_status == "summaries_completed":
                    console.print("[yellow]Analysis completed. Generating final report...[/yellow]")
                else:
                    console.print("[yellow]Research appears stalled. Continuing to next phase...[/yellow]")
                
                force_continue_research(api_url, session_id)
                stalled_count = 0
            
            last_status = current_status
            last_progress = current_progress
            
            time.sleep(poll_interval)
    
    return get_research_status(api_url, session_id)

def display_final_report(status):
    """Display the final research report."""
    if not status:
        console.print("[bold red]Failed to retrieve research status. No report available.[/bold red]")
        return
    
    final_report = status.get("final_report")
    
    if not final_report or final_report.strip() == "":
        console.print("[bold red]No final report available in the research results.[/bold red]")
        
        if status.get("status") == "error" and status.get("errors"):
            console.print("[bold red]Errors encountered during research:[/bold red]")
            for error in status.get("errors", []):
                console.print(f"- {error}")
        return
    
    console.print("\n")
    console.print("=" * 80)
    console.print("[bold cyan]PROCESS WORKFLOW[/bold cyan]")
    console.print("=" * 80)
    console.print("\n")
    
    report_lines = final_report.split('\n')
    report_start_index = -1
    
    for i, line in enumerate(report_lines):
        if "Executive Summary" in line:
            report_start_index = i
            break
    
    if report_start_index != -1:
        process_workflow = '\n'.join(report_lines[:report_start_index])
        console.print(Markdown(process_workflow))
        
        console.print("\n")
        console.print("=" * 80)
        console.print("[bold green]RESEARCH REPORT BEGINS[/bold green]")
        console.print("=" * 80)
        console.print("\n")
        
        actual_report = '\n'.join(report_lines[report_start_index:])
        console.print(Markdown(actual_report))
    else:
        console.print(Markdown(final_report))

def save_report_to_file(status, filename):
    """Save the final report to a file."""
    if not status:
        console.print("[bold red]No research status available. Cannot save report.[/bold red]")
        return
    
    final_report = status.get("final_report")
    if not final_report or final_report.strip() == "":
        console.print("[bold red]No report content available to save.[/bold red]")
        return
    
    report_lines = final_report.split('\n')
    report_start_index = -1
    
    for i, line in enumerate(report_lines):
        if "Executive Summary" in line:
            report_start_index = i
            break
    
    if report_start_index != -1:
        actual_report = '\n'.join(report_lines[report_start_index:])
    else:
        actual_report = final_report
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(actual_report)
        console.print(f"[bold green]Report saved to {filename}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error saving report: {str(e)}[/bold red]")

def configure_research():
    """Configure research parameters interactively."""
    console.print(Panel("[bold]Research Configuration[/bold]", border_style="blue"))
    
    model_options = [
        {"name": "Mistral-7B-Instruct-v0.2", "id": "mistralai/Mistral-7B-Instruct-v0.2", "description": "Default - Balanced performance and quality"},
        {"name": "Gemma-7B-Instruct", "id": "google/gemma-7b-it", "description": "Google's efficient instruction-tuned model"},
        {"name": "Llama-3-8B-Instruct", "id": "meta-llama/Llama-3-8b-instruct", "description": "Meta's latest instruction-tuned model"},
        {"name": "Qwen-7B-Chat", "id": "Qwen/Qwen-7B-Chat", "description": "Alibaba's conversational model"},
        {"name": "Custom", "id": "custom", "description": "Specify a custom model from Hugging Face"}
    ]
    
    console.print("[cyan]Select LLM model:[/cyan]")
    for i, model in enumerate(model_options, 1):
        console.print(f"{i}. [bold]{model['name']}[/bold] - {model['description']}")
    
    model_index = console.input(f"Enter choice (1-{len(model_options)}) [default=1]: ")
    
    try:
        model_index = int(model_index) - 1 if model_index else 0
        if model_index < 0 or model_index >= len(model_options):
            model_index = 0
    except ValueError:
        model_index = 0
    
    selected_model = model_options[model_index]
    model_id = selected_model["id"]
    
    if model_id == "custom":
        model_id = Prompt.ask(
            "\n[cyan]Enter the Hugging Face model ID[/cyan] (e.g., 'organization/model-name')",
            default="mistralai/Mistral-7B-Instruct-v0.2"
        )
    
    speed_options = ["fast", "deep"]
    speed_index = console.input(
        "\n[cyan]Select research speed:[/cyan]\n"
        "1. [bold]Fast[/bold] - Quicker results, less comprehensive\n"
        "2. [bold]Deep[/bold] - More thorough research, takes longer\n"
        "Enter choice (1-2) [default=2]: "
    )
    
    try:
        speed_index = int(speed_index) - 1 if speed_index else 1
        if speed_index < 0 or speed_index >= len(speed_options):
            speed_index = 1
    except ValueError:
        speed_index = 1
    
    research_speed = speed_options[speed_index]
    
    format_options = ["full_report", "executive_summary", "bullet_list"]
    format_index = console.input(
        "\n[cyan]Select output format:[/cyan]\n"
        "1. [bold]Full Report[/bold] - Comprehensive with sections and details\n"
        "2. [bold]Executive Summary[/bold] - Concise overview with key points\n"
        "3. [bold]Bullet List[/bold] - Just the essential facts in bullet points\n"
        "Enter choice (1-3) [default=1]: "
    )
    
    try:
        format_index = int(format_index) - 1 if format_index else 0
        if format_index < 0 or format_index >= len(format_options):
            format_index = 0
    except ValueError:
        format_index = 0
    
    output_format = format_options[format_index]
    
    depth_input = console.input(
        "\n[cyan]Research depth and breadth (1-5)[/cyan]\n"
        "1 = Basic overview, 5 = Extremely detailed\n"
        "Enter value [default=3]: "
    )
    
    try:
        depth_and_breadth = int(depth_input) if depth_input else 3
        if depth_and_breadth < 1 or depth_and_breadth > 5:
            depth_and_breadth = 3
    except ValueError:
        depth_and_breadth = 3
    
    skip_clarification = Confirm.ask(
        "\n[cyan]Skip clarification questions?[/cyan]",
        default=False
    )
    
    config = {
        "research_speed": research_speed,
        "output_format": output_format,
        "depth_and_breadth": depth_and_breadth,
        "skip_clarification": skip_clarification,
        "model_id": model_id
    }
    
    console.print("\n[bold green]Configuration complete![/bold green]")
    return config

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="OpenResearch CLI")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=f"API URL (default: {DEFAULT_API_URL})")
    parser.add_argument("--session-id", help="Resume an existing research session")
    parser.add_argument("--save", help="Save the final report to a file")
    parser.add_argument("--query", help="Research query (if not provided, will prompt)")
    parser.add_argument("--poll-interval", type=int, default=5, help="Polling interval in seconds (default: 5)")
    parser.add_argument("--quiet", action="store_true", help="Minimal output mode (only show the final report)")
    args = parser.parse_args()
    
    if not args.quiet:
        console.print(Panel.fit(
            "[bold blue]OpenResearch CLI[/bold blue]\n"
            "[cyan]A user-friendly interface for automated research[/cyan]",
            border_style="blue"
        ))
    
    session_id = args.session_id
    
    if not session_id:
        query = args.query
        if not query:
            query = Prompt.ask("[bold cyan]What would you like to research?[/bold cyan]")
        
        if not args.quiet:
            console.print("\n[bold]Let's configure your research:[/bold]")
        config = configure_research()
        
        if not args.quiet:
            console.print("\n[bold]Creating research session...[/bold]")
        response = create_research_session(args.api_url, query, config)
        session_id = response.get("session_id")
        
        save_session_to_cache(session_id, {
            "query": query,
            "config": config,
            "session_id": session_id
        })
        
        if not args.quiet:
            console.print(f"[bold green]Research session created! Session ID: {session_id}[/bold green]")
    else:
        if not args.quiet:
            console.print(f"[bold]Resuming research session {session_id}...[/bold]")
        
        cached_data = get_cached_session(session_id)
        if cached_data and not args.quiet:
            console.print(f"[green]Loaded cached session data for {session_id}[/green]")
    
    if not args.quiet:
        console.print("\n[bold]Starting research process...[/bold]")
    
    try:
        final_status = monitor_research_progress(args.api_url, session_id, args.poll_interval)
        
        if not final_status:
            console.print("[yellow]Attempting to retrieve final research status...[/yellow]")
            final_status = get_research_status(args.api_url, session_id)
        
        display_final_report(final_status)
        
        if args.save and final_status and final_status.get("final_report"):
            save_report_to_file(final_status, args.save)
        elif final_status and final_status.get("final_report") and not args.quiet:
            if Confirm.ask("[cyan]Would you like to save the report to a file?[/cyan]"):
                filename = Prompt.ask("[cyan]Enter filename[/cyan]", default="research_report.md")
                save_report_to_file(final_status, filename)
    except Exception as e:
        console.print(f"[bold red]Error during research process: {str(e)}[/bold red]")
        try:
            final_status = get_research_status(args.api_url, session_id)
            if final_status:
                display_final_report(final_status)
        except Exception:
            console.print("[bold red]Could not retrieve research results.[/bold red]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Research interrupted by user.[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]An error occurred: {str(e)}[/bold red]")
        sys.exit(1) 