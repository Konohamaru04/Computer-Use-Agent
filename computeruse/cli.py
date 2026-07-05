from __future__ import annotations

import asyncio
from typing import Any

import typer
from rich.console import Console
from rich.json import JSON
from rich.table import Table

from computeruse.config import DEFAULT_MAX_STEPS

app = typer.Typer(help="Run the ComputerUse local desktop-control agent.")
console = Console()


@app.command("models")
def models() -> None:
    """List installed Ollama models, with known vision models first."""

    async def _run() -> None:
        from computeruse.agent.ollama_client import OllamaClient

        client = OllamaClient()
        try:
            model_list = await client.list_models()
        finally:
            await client.close()

        table = Table(title="Ollama models")
        table.add_column("Model")
        table.add_column("Vision", justify="center")
        table.add_column("Size", justify="right")
        for model in model_list:
            table.add_row(model.name, "yes" if model.vision else "no", str(model.size or ""))
        console.print(table)

    asyncio.run(_run())


@app.command("screenshot")
def screenshot() -> None:
    """Capture the current screen to screenshots/current.png."""

    from computeruse.tools.screenshot import capture_screenshot

    shot = capture_screenshot()
    console.print(f"Captured {shot.width}x{shot.height}: {shot.path}")


@app.command("mcp")
def mcp() -> None:
    """Run the built-in stdio MCP server for external agents."""

    from computeruse.mcp_server import main

    main()


@app.command("run")
def run(
    task: str = typer.Argument(..., help="Natural-language computer task to run."),
    model: str | None = typer.Option(None, "--model", "-m", help="Ollama model to use."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate actions but do not execute mouse/keyboard."),
    max_steps: int = typer.Option(DEFAULT_MAX_STEPS, "--max-steps", help="Maximum agent steps."),
    debug_timing: bool = typer.Option(False, "--debug-timing", help="Print per-phase timing events."),
) -> None:
    """Run a task through the observe-plan-act loop."""

    async def _run() -> None:
        from computeruse.agent.loop import AgentRunner
        from computeruse.agent.ollama_client import OllamaClient

        client = OllamaClient()
        selected_model = model
        try:
            if not selected_model:
                models = await client.list_models()
                if not models:
                    raise typer.BadParameter("Ollama returned no installed models.")
                selected_model = models[0].name
                console.print(f"Using model: [bold]{selected_model}[/bold]")

            async def emit(event: dict[str, Any]) -> None:
                event_type = event.get("type")
                if event_type == "model_action":
                    console.print("[bold]model_action[/bold]")
                    console.print(JSON.from_data(event["action"]))
                elif event_type == "tool_result":
                    console.print(f"tool_result ok={event.get('ok')}: {event.get('message')}")
                elif event_type == "screenshot":
                    console.print(f"screenshot {event.get('width')}x{event.get('height')} {event.get('path')}")
                elif event_type == "timing" and debug_timing:
                    console.print(JSON.from_data(event))
                elif event_type in {"session_done", "session_failed", "session_cancelled"}:
                    console.print(JSON.from_data(event))
                elif event_type == "step_started":
                    console.print(f"\n[bold]step {event.get('step_index')}[/bold]")

            runner = AgentRunner(ollama=client, emit=emit)
            await runner.run_task(task=task, model=selected_model, dry_run=dry_run, max_steps=max_steps)
        finally:
            await client.close()

    asyncio.run(_run())


if __name__ == "__main__":
    app()
