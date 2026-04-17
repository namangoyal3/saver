"""Saver CLI — interactive chat interface with Rich formatting."""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from saver.agents.supervisor import _detect_provider, run_turn
from saver.data.db import get_conn, init_db
from saver.data.seed import seed_all
from saver.models import AgentTurnResponse, ReasoningStep, UserProfileSnapshot

load_dotenv()

console = Console()

# ── User profile loading ──────────────────────────────────────────────

def load_profile(user_key: str) -> UserProfileSnapshot:
    """Load a user profile from the database."""
    # Map short names to user IDs
    user_map = {"budi": "budi-001", "siti": "siti-001"}
    user_id = user_map.get(user_key.lower(), user_key)

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    if not row:
        console.print(f"[red]User '{user_key}' not found. Run: python -m saver.data.seed[/red]")
        sys.exit(1)

    return UserProfileSnapshot(
        user_id=row["user_id"],
        name=row["name"],
        market=row["market"],
        preferred_lang=row["preferred_lang"],
        partner_types=[row["partner_types"]],
        earnings_tier=row["earnings_tier"],
        financial_persona=row["financial_persona"],
        currency=row["currency"],
    )


# ── Trace display ─────────────────────────────────────────────────────

def display_trace(response: AgentTurnResponse):
    """Display the reasoning trace in a formatted table."""
    if not response.reasoning_trace:
        console.print("[dim]No trace available for last turn.[/dim]")
        return

    table = Table(title="Reasoning Trace", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Agent", width=12)
    table.add_column("Action", width=10)
    table.add_column("Tool", width=24)
    table.add_column("Result", width=50)
    table.add_column("ms", justify="right", width=6)

    for step in response.reasoning_trace:
        table.add_row(
            str(step.idx),
            step.agent,
            step.action,
            step.tool_name or "—",
            step.result_summary or step.tool_args_summary or "—",
            str(step.latency_ms),
        )

    console.print(table)

    # Guardrail report
    gr = response.guardrail_report
    guard_text = Text()
    guard_text.append("Guardrails: ", style="bold")
    guard_text.append(f"PII={'redacted' if gr.input_pii_redacted else 'clean'} ", style="yellow" if gr.input_pii_redacted else "green")
    guard_text.append(f"| InScope={gr.input_scope_check} ", style="green" if gr.input_scope_check == "pass" else "red")
    guard_text.append(f"| Grounding={gr.output_grounding_check} ", style="green" if gr.output_grounding_check == "pass" else "yellow")
    guard_text.append(f"| OutScope={gr.output_scope_check}", style="green" if gr.output_scope_check == "pass" else "red")
    console.print(guard_text)


# ── Thinking display ──────────────────────────────────────────────────

def display_thinking(response: AgentTurnResponse):
    """Show abbreviated thinking steps inline."""
    for step in response.reasoning_trace:
        if step.action == "tool_call" and step.tool_name:
            console.print(f"  [dim cyan]tool:[/dim cyan] [dim]{step.tool_name}[/dim] [dim]→ {step.result_summary or '...'}[/dim]")
        elif step.action == "plan":
            console.print(f"  [dim yellow]plan:[/dim yellow] [dim]{step.tool_args_summary or step.result_summary or '...'}[/dim]")
        elif step.action == "refuse":
            console.print(f"  [dim red]refuse:[/dim red] [dim]{step.result_summary or '...'}[/dim]")


# ── Main chat loop ────────────────────────────────────────────────────

def chat_loop(user_key: str):
    """Main interactive chat loop."""
    init_db()
    profile = load_profile(user_key)
    history: list = []
    last_response: AgentTurnResponse | None = None

    provider = _detect_provider()
    console.print(Panel(
        f"[bold green]Saver[/bold green] — Financial Wellness Coach\n"
        f"[dim]User: {profile.name} | Market: {profile.market.value} | "
        f"Currency: {profile.currency} | Lang: {profile.preferred_lang}[/dim]\n"
        f"[dim]Model: {provider}[/dim]\n\n"
        f"[dim]Commands: /trace — show reasoning trace | /help — help | /quit — exit[/dim]",
        title="Welcome",
        border_style="green",
    ))

    while True:
        try:
            user_input = console.input("\n[bold green]You>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue

        # Handle commands
        if user_input.lower() in ("/quit", "/exit", "quit", "exit"):
            console.print("[dim]Goodbye![/dim]")
            break

        if user_input.lower() == "/trace":
            if last_response:
                display_trace(last_response)
            else:
                console.print("[dim]No previous turn to trace.[/dim]")
            continue

        if user_input.lower() == "/help":
            console.print(Panel(
                "Ask me about your finances:\n"
                "  • \"Where did my money go this week?\"\n"
                "  • \"How much did I earn last month?\"\n"
                "  • \"Can I save 500 a month?\"\n"
                "  • \"Help me set up an emergency fund\"\n"
                "  • \"What's my cashflow forecast?\"\n\n"
                "Commands:\n"
                "  /trace  — Show reasoning trace for last response\n"
                "  /help   — Show this help\n"
                "  /quit   — Exit",
                title="Help",
                border_style="blue",
            ))
            continue

        if user_input.lower() == "/seed":
            console.print("[yellow]Reseeding data...[/yellow]")
            seed_all()
            continue

        # Run agent turn
        console.print("[dim]Thinking...[/dim]")
        try:
            last_response, history = run_turn(user_input, profile, history)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            continue

        # Display thinking steps
        display_thinking(last_response)

        # Display response
        console.print()
        console.print(Panel(
            Markdown(last_response.reply),
            title=f"[bold green]Saver[/bold green]",
            border_style="green",
            padding=(1, 2),
        ))


def main():
    parser = argparse.ArgumentParser(description="Saver — Financial Wellness Coach CLI")
    subparsers = parser.add_subparsers(dest="command")

    # chat command
    chat_parser = subparsers.add_parser("chat", help="Start interactive chat")
    chat_parser.add_argument("--user", "-u", default="budi", help="User persona: budi or siti (default: budi)")

    # seed command
    subparsers.add_parser("seed", help="Generate synthetic data")

    # web command
    web_parser = subparsers.add_parser("web", help="Start web dashboard")
    web_parser.add_argument("--port", "-p", type=int, default=8000, help="Port (default: 8000)")

    args = parser.parse_args()

    if args.command == "seed":
        seed_all()
    elif args.command == "chat":
        chat_loop(args.user)
    elif args.command == "web":
        from saver.web.app import start_server
        start_server()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
