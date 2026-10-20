# ExoAl

ExoAl is a Python library and interactive CLI for chatting with an AI API.

## Features

- Live model discovery through `GET ?command=models`.
- `/models` fetches the current server-side model list.
- `/model MODEL_NAME` switches to any model exposed by the API.
- Streaming support for Server-Sent Events (SSE) and NDJSON responses, with a token callback.
- JSON fallback when streaming is not provided.
- Conversation history support (managed by your application/CLI).
- Optional system prompt and extra request JSON fields.
- Timeout settings, retry on transient network/server errors, custom headers.
- Health endpoint helper and context-manager support.
- No hard-coded model registry: newly exposed API models can be discovered without updating ExoAl.

## Install

```bash
python -m pip install .
```

Dependency only:

```bash
python -m pip install requests
```

## Configure the API URL

```bash
exoal
```

Default URL is the configured HackerExos API endpoint. To override it:

Linux/macOS:
```bash
export EXOAL_API_URL="https://your-domain.com/api.php"
exoal
```

Windows CMD:
```bat
set EXOAL_API_URL=https://your-domain.com/api.php
exoal
```

## CLI commands

```text
/models
/model qwen3-8b
/health
/clear
/exit
```

## Library usage

```python
from exoal import ExoAl

ai = ExoAl("https://your-domain.com/api.php", model="qwen3-8b")

# Always reads the current model list from the API.
for model in ai.models():
    print(model["id"], model["name"])

# Validate and switch to a model advertised by the API.
ai.set_model("qwen3-8b")

answer = ai.chat("Hello!", stream=False)
print(answer)
```

## Streaming

```python
from exoal import ExoAl

ai = ExoAl("https://your-domain.com/api.php")
answer = ai.chat(
    "Explain Python dictionaries",
    stream=True,
    on_token=lambda piece: print(piece, end="", flush=True),
)
print()
```

Streaming works when the API returns `Content-Type: text/event-stream` (SSE) or an NDJSON content type such as `application/x-ndjson`. If the server sends a complete answer in one event/chunk, the callback receives that full fragment rather than token-by-token fragments. If the API does not return a streaming content type, ExoAl falls back to parsing the completed JSON response.

## History and system prompt

```python
from exoal import ExoAl

ai = ExoAl("https://your-domain.com/api.php", model="qwen3-8b")
history = [
    {"role": "user", "content": "My name is Sam."},
    {"role": "assistant", "content": "Nice to meet you."},
]
answer = ai.chat(
    "What did I tell you?",
    history=history,
    system="Answer clearly.",
    stream=False,
)
print(answer)
```

## Custom headers / optional API key

```python
ai = ExoAl(
    "https://your-domain.com/api.php",
    headers={"X-Client-App": "my-project"},
    api_key=None,  # supply a key only if your API explicitly requires one
)
```

## API compatibility note

This package sends POST JSON as:
`{"model": "...", "messages": [{"role": "user", "content": "..."}], "stream": true}`

The API must accept that shape. Model discovery expects a JSON response from `?command=models`, with model IDs in a `models` or `data` list (or a dictionary keyed by model ID). If your PHP endpoint uses a different POST schema, adjust the body in `exoal/client.py`.
