# -*- coding: utf-8 -*-
"""Interactive terminal interface for ExoAl."""

import json
import os

from .client import ExoAl, ExoAlError

DEFAULT_API_URL = os.environ.get(
    "EXOAL_API_URL", "https://dev-vnk.pantheonsite.io/api.php"
)


def print_models(client: ExoAl) -> None:
    models = client.models(refresh=True)
    print("\nAvailable models (loaded live from API):")
    for item in models:
        stream = "stream=true" if item.get("stream") is True else (
            "stream=false" if item.get("stream") is False else "stream capability unknown"
        )
        marker = "  < current" if item["id"] == client.current_model else ""
        print(f"  {item['id']} — {item['name']} [{stream}]{marker}")
    print(f"\nCurrent model: {client.current_model}\n")


def main() -> None:
    client = ExoAl(api_url=DEFAULT_API_URL)
    history = []
    print("=" * 52)
    print("                  ExoAl")
    print("         Dynamic AI API Python Client")
    print("=" * 52)
    print("Commands: /models, /model NAME, /health, /clear, /exit")
    try:
        print_models(client)
    except ExoAlError as exc:
        print(f"[Models error] {exc}")

    while True:
        try:
            line = input(f"[{client.current_model}] You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not line:
            continue
        command, _, argument = line.partition(" ")
        command = command.lower()

        if command in ("/exit", "/quit", "exit", "quit"):
            print("Goodbye.")
            break
        if command == "/models":
            try:
                print_models(client)
            except ExoAlError as exc:
                print(f"[Error] {exc}")
            continue
        if command == "/model":
            try:
                print(client.set_model(argument))
            except (ExoAlError, ValueError) as exc:
                print(f"[Error] {exc}")
            continue
        if command == "/health":
            try:
                print(json.dumps(client.health(), ensure_ascii=False, indent=2))
            except ExoAlError as exc:
                print(f"[Error] {exc}")
            continue
        if command == "/clear":
            history.clear()
            print("Conversation history cleared.")
            continue
        if line.startswith("/"):
            print("Unknown command. Use /models, /model NAME, /health, /clear, or /exit.")
            continue

        print("AI: ", end="", flush=True)
        try:
            answer = client.chat(
                line,
                history=history,
                stream=True,
                on_token=lambda part: print(part, end="", flush=True),
            )
            print()
            history.extend([
                {"role": "user", "content": line},
                {"role": "assistant", "content": answer},
            ])
            history = history[-40:]
        except ExoAlError as exc:
            print(f"\n[Error] {exc}")


if __name__ == "__main__":
    main()
