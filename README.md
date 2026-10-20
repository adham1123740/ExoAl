🚀 ExoAl — Python AI API Library

ExoAl is a lightweight Python library and interactive command-line interface (CLI) designed to connect to AI APIs with ease. It supports dynamic model discovery, real-time streaming, conversation history, and customizable requests.

✨ No API key required when connecting to an API that does not require authentication.

🌟 Features

- 🔍 Dynamic Model Discovery — Fetch available models directly from "GET ?command=models".
- 📋 Live Model List — Use "/models" to retrieve the latest models available on the server.
- 🔄 Model Switching — Switch between supported models using "/model MODEL_NAME".
- ⚡ Streaming Support — Supports Server-Sent Events (SSE) and NDJSON responses with a token callback.
- 📦 JSON Fallback — Automatically handles regular JSON responses when streaming is unavailable.
- 💬 Conversation History — Maintain conversation context through application-managed message history.
- 🎭 Custom System Prompts — Configure the assistant's behavior with an optional system prompt.
- 🛠️ Custom Request Fields — Send additional JSON fields when needed.
- ⏱️ Configurable Timeouts — Set request timeouts to suit your API.
- 🔁 Automatic Retries — Retry requests after supported temporary network or server errors.
- 🧩 Custom Headers — Add custom HTTP headers when your application requires them.
- ❤️ Health Check Helper — Check API health through the library.
- 🔒 Optional Authentication — API keys are optional. You do not need to provide one unless your API explicitly requires it.
- 🧠 No Hard-Coded Model Registry — Newly available API models can be discovered without modifying ExoAl.

📦 Installation

Install from the Project Directory

python -m pip install .

Install the Required Dependency

python -m pip install requests

🚀 Quick Start

After installing ExoAl, launch the interactive CLI:

exoal

The CLI uses the configured HackerExos API endpoint by default.

⚙️ Configure the API URL

You can change the API endpoint using the "EXOAL_API_URL" environment variable.

🐧 Linux / macOS

export EXOAL_API_URL="https://dev-vnk.pantheonsite.io/api.php"
exoal

🪟 Windows CMD

set EXOAL_API_URL=https://dev-vnk.pantheonsite.io/api.php
exoal

💻 CLI Commands

Use these commands while running the interactive CLI:

Command| Description
"/models"| 🔍 Fetch the latest available models
"/model qwen3-8b"| 🔄 Switch to the specified model
"/health"| ❤️ Check the API health
"/clear"| 🧹 Clear the conversation history
"/exit"| 👋 Exit the CLI

🧑‍💻 Library Usage

You can use ExoAl directly in your Python projects.

from exoal import ExoAl

# Initialize the client without an API key.
ai = ExoAl(
    "https://dev-vnk.pantheonsite.io/api.php",
    model="qwen3-8b",
)

# 🔍 Fetch the current model list from the API.
for model in ai.models():
    print(model["id"], model["name"])

# 🔄 Validate and switch to a model advertised by the API.
ai.set_model("qwen3-8b")

# 💬 Send a message and receive a complete response.
answer = ai.chat("Hello!", stream=False)
print(answer)

✅ No API key is passed or required by this example.

⚡ Real-Time Streaming

ExoAl supports streaming responses when the API returns SSE or NDJSON data.

from exoal import ExoAl

# Initialize the client without an API key.
ai = ExoAl("https://dev-vnk.pantheonsite.io/api.php")

print("🤖 AI: ", end="", flush=True)

# ⚡ Receive response fragments as they arrive.
answer = ai.chat(
    "Explain Python dictionaries",
    stream=True,
    on_token=lambda piece: print(piece, end="", flush=True),
)

print()

📡 Streaming Compatibility

Streaming is supported when the API returns:

- "Content-Type: text/event-stream" — Server-Sent Events (SSE).
- "Content-Type: application/x-ndjson" — Newline-delimited JSON.

If the server sends the complete answer in a single event or chunk, the callback receives the entire fragment rather than individual tokens.

If the API does not return a supported streaming content type, ExoAl falls back to parsing the completed JSON response.

Note: Actual token-by-token streaming depends on the upstream API and server implementation.

💬 Conversation History & System Prompts

You can pass previous messages to maintain context and customize the assistant's behavior.

from exoal import ExoAl

ai = ExoAl(
    "https://dev-vnk.pantheonsite.io/api.php",
    model="qwen3-8b",
)

# 🧠 Previous conversation messages.
history = [
    {"role": "user", "content": "My name is Sam."},
    {"role": "assistant", "content": "Nice to meet you."},
]

# 💬 Send a message with conversation history and a system prompt.
answer = ai.chat(
    "What did I tell you?",
    history=history,
    system="Answer clearly.",
    stream=False,
)

print(answer)

🛠️ Custom Headers & Optional API Key

ExoAl supports custom HTTP headers for applications that need them.

Important: The API key is optional. Leave it as "None" when your API does not require authentication.

from exoal import ExoAl

ai = ExoAl(
    "https://dev-vnk.pantheonsite.io/api.php",
    headers={"X-Client-App": "ExoAl-Python"},
    api_key=None,
)

If your API does not require authentication, you can also initialize the client without specifying the "api_key" argument:

from exoal import ExoAl

ai = ExoAl("https://dev-vnk.pantheonsite.io/api.php")

🔌 API Compatibility

ExoAl sends POST requests using the following JSON structure:

{
  "model": "qwen3-8b",
  "messages": [
    {
      "role": "user",
      "content": "Hello!"
    }
  ],
  "stream": true
}

Your API must accept this request format for the library to work without modifications.

🔍 Model Discovery Requirements

The model discovery endpoint is:

GET /api.php?command=models

The API should return JSON containing model IDs in one of these formats:

- A "models" list.
- A "data" list.
- A dictionary keyed by model ID.

If your PHP endpoint uses a different POST request format or model-list structure, update "exoal/client.py" to match your API.

🛡️ Authentication & Security

- 🔓 ExoAl does not require an API key by default.
- 🔑 Only configure an API key if the target API explicitly requires authentication.
- 🌐 Use HTTPS when connecting to remote APIs.
- 🔐 Never publish private API keys or other secrets in public repositories.

📚 Project Summary

Property| Details
📛 Name| ExoAl
🐍 Language| Python
🔌 API Communication| HTTP / JSON
⚡ Streaming| SSE and NDJSON
🔍 Model Discovery| Dynamic
🔑 API Key| Optional
💻 Interface| Python Library & Interactive CLI

🎉 Get Started with ExoAl!

Connect your Python applications to your AI API with dynamic model discovery, streaming support, conversation history, and a simple interface.

ExoAl — Simple integration. Flexible models. Powerful AI conversations. 🚀
