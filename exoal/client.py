# -*- coding: utf-8 -*-
"""ExoAl API client with live model discovery, retries, streaming and history."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

import requests


DEFAULT_API_URL = "https://dev-vnk.pantheonsite.io/api.php"


class ExoAlError(Exception):
    """Base exception for ExoAl."""


class APIError(ExoAlError):
    """Raised when the remote API fails or returns an unsupported response."""


class ModelNotFoundError(APIError):
    """Raised when a requested model is not in the API's live model list."""


@dataclass(frozen=True)
class StreamEvent:
    """A parsed event from the server's SSE stream."""
    event: str
    data: Any
    raw: str = ""


class ExoAl:
    """Python client for a compatible AI API.

    The model catalogue is fetched from GET ?command=models on each models()
    call. No model names are hard-coded into the registry, so new API models
    are discoverable without updating this package.
    """

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        model: str = "qwen3-8b",
        timeout: Union[float, tuple] = (20, 240),
        retries: int = 2,
        retry_delay: float = 0.7,
        session: Optional[requests.Session] = None,
        headers: Optional[Dict[str, str]] = None,
        api_key: Optional[str] = None,
        validate_model: bool = False,
    ) -> None:
        if not isinstance(api_url, str) or not api_url.strip():
            raise ValueError("api_url must be a non-empty URL.")
        if retries < 0:
            raise ValueError("retries must be >= 0.")
        self.api_url = api_url.strip()
        self.current_model = (model or "").strip()
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = max(0.0, float(retry_delay))
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": "ExoAl-Python/1.1.0",
            "Accept": "application/json, text/event-stream",
        })
        if headers:
            self.session.headers.update(headers)
        if api_key:
            # Only sent when the user explicitly supplies a key.
            self.session.headers["Authorization"] = f"Bearer {api_key}"
        self._models_cache: List[Dict[str, Any]] = []
        self._models_cache_at = 0.0
        if validate_model and self.current_model:
            self.set_model(self.current_model)

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self) -> "ExoAl":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @staticmethod
    def _payload(response: requests.Response) -> Any:
        try:
            return response.json()
        except (ValueError, json.JSONDecodeError):
            return response.text

    @staticmethod
    def _error_message(payload: Any, status_code: int) -> str:
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                return str(error.get("message") or error.get("type") or f"HTTP {status_code}")
            if isinstance(error, str):
                return error
            for key in ("message", "detail", "description"):
                if payload.get(key):
                    return str(payload[key])
        if isinstance(payload, str) and payload.strip():
            return payload.strip()[:1200]
        return f"HTTP {status_code}"

    def _request(self, method: str, **kwargs) -> requests.Response:
        last_error = None
        attempts = self.retries + 1
        for attempt in range(attempts):
            try:
                response = self.session.request(
                    method, self.api_url, timeout=self.timeout, **kwargs
                )
                # Retry transient server/rate-limit errors only.
                if response.status_code not in (408, 425, 429, 500, 502, 503, 504):
                    return response
                if attempt == attempts - 1:
                    return response
                response.close()
            except requests.RequestException as exc:
                last_error = exc
                if attempt == attempts - 1:
                    raise APIError(f"Could not connect to API: {exc}") from exc
            time.sleep(self.retry_delay * (attempt + 1))
        raise APIError(f"Request failed: {last_error}")

    @staticmethod
    def _normalize_models(payload: Any) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            raise APIError("Models endpoint did not return a JSON object.")

        entries = payload.get("data", payload.get("models", payload.get("available_models", [])))
        if isinstance(entries, dict):
            entries = [
                {"id": model_id, **(value if isinstance(value, dict) else {"name": str(value)})}
                for model_id, value in entries.items()
            ]
        if not isinstance(entries, list):
            raise APIError(
                "Unsupported models response. Expected a list in 'models' or 'data'."
            )

        result: List[Dict[str, Any]] = []
        seen = set()
        for entry in entries:
            if isinstance(entry, str):
                model_id, name, stream = entry.strip(), entry.strip(), None
                extra = {}
            elif isinstance(entry, dict):
                model_id = str(
                    entry.get("id") or entry.get("model") or entry.get("model_id") or ""
                ).strip()
                name = str(entry.get("name") or entry.get("label") or model_id).strip()
                stream = entry.get("stream")
                extra = {
                    key: value for key, value in entry.items()
                    if key not in {"id", "model", "model_id", "name", "label", "stream"}
                }
            else:
                continue
            if model_id and model_id not in seen:
                result.append({
                    "id": model_id,
                    "name": name or model_id,
                    "stream": stream,
                    **extra,
                })
                seen.add(model_id)
        if not result:
            raise APIError("API returned no models. Check ?command=models on your server.")
        return result

    def models(self, refresh: bool = True) -> List[Dict[str, Any]]:
        """Get available models from the live API. `refresh=False` uses cached data."""
        if not refresh and self._models_cache:
            return [dict(item) for item in self._models_cache]
        response = self._request(
            "GET",
            params={"command": "models"},
            headers={"Accept": "application/json"},
        )
        payload = self._payload(response)
        if not response.ok:
            raise APIError(self._error_message(payload, response.status_code))
        models = self._normalize_models(payload)
        self._models_cache = models
        self._models_cache_at = time.time()
        return [dict(item) for item in models]

    @property
    def models_cache_age(self) -> Optional[float]:
        """Seconds since the model catalogue was last fetched, or None."""
        if not self._models_cache_at:
            return None
        return max(0.0, time.time() - self._models_cache_at)

    def set_model(self, name: str, validate: bool = True) -> str:
        """Set current model. Validation checks the live API model catalogue."""
        name = (name or "").strip()
        if not name:
            raise ValueError("Provide a model name, e.g. set_model('qwen3-8b').")
        if validate:
            available = self.models(refresh=True)
            found = next((item for item in available if item["id"] == name), None)
            if found is None:
                matches = [
                    item for item in available
                    if item["id"].casefold() == name.casefold()
                    or item["name"].casefold() == name.casefold()
                ]
                if len(matches) == 1:
                    found = matches[0]
            if found is None:
                available_ids = ", ".join(item["id"] for item in available)
                raise ModelNotFoundError(
                    f"Unknown model '{name}'. Available models: {available_ids}"
                )
            self.current_model = found["id"]
            return f"Model changed to: {found['name']} ({found['id']})"
        self.current_model = name
        return f"Current model set to: {name}"

    @staticmethod
    def _extract_text(obj: Any) -> str:
        if not isinstance(obj, dict):
            return ""
        choices = obj.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            choice = choices[0]
            message = choice.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
            delta = choice.get("delta")
            if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                return delta["content"]
            if isinstance(choice.get("text"), str):
                return choice["text"]
        for key in ("response", "content", "text", "answer", "output", "generated_text"):
            value = obj.get(key)
            if isinstance(value, str):
                return value
        return ""

    def chat(
        self,
        message: str,
        model: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        system: Optional[str] = None,
        stream: bool = True,
        on_token: Optional[Callable[[str], None]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send a chat request and return the complete answer.

        `history`: list of {"role": "user"|"assistant"|"system", "content": "..."}.
        `system`: optional system instruction.
        `on_token`: callback called for each text fragment received.
        `extra`: extra JSON fields accepted by your API.
        """
        message = (message or "").strip()
        if not message:
            raise ValueError("message cannot be empty")
        selected = (model or self.current_model).strip()
        if not selected:
            raise ValueError("No model selected. Set one with set_model().")

        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        for item in history or []:
            if not isinstance(item, dict):
                continue
            role, content = item.get("role"), item.get("content")
            if role in ("system", "user", "assistant") and isinstance(content, str):
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        body: Dict[str, Any] = {
            "model": selected,
            "messages": messages,
            "stream": bool(stream),
        }
        if extra:
            body.update(extra)

        response = self._request(
            "POST",
            json=body,
            stream=bool(stream),
            headers={"Accept": "text/event-stream, application/json"},
        )
        content_type = (response.headers.get("Content-Type") or "").lower()
        if not response.ok and "text/event-stream" not in content_type:
            payload = self._payload(response)
            response.close()
            raise APIError(self._error_message(payload, response.status_code))

        if stream and "text/event-stream" in content_type:
            return self._read_sse(response, on_token)
        if stream and any(marker in content_type for marker in (
            "application/x-ndjson", "application/ndjson", "application/jsonl"
        )):
            return self._read_ndjson(response, on_token)

        payload = self._payload(response)
        response.close()
        if not response.ok:
            raise APIError(self._error_message(payload, response.status_code))
        answer = self._extract_text(payload)
        if not answer:
            if isinstance(payload, dict) and payload.get("error"):
                raise APIError(self._error_message(payload, response.status_code))
            raise APIError(
                "Response contained no recognized answer field. "
                "Check the API's POST request format and JSON response."
            )
        if on_token:
            on_token(answer)
        return answer

    def _read_sse(
        self,
        response: requests.Response,
        on_token: Optional[Callable[[str], None]],
    ) -> str:
        pieces: List[str] = []
        event_name = "message"
        data_lines: List[str] = []

        def process_event() -> bool:
            nonlocal event_name, data_lines
            if not data_lines:
                event_name = "message"
                return False
            data = "\n".join(data_lines).strip()
            data_lines = []
            current_event = event_name
            event_name = "message"
            if not data or data == "[DONE]":
                return False
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                pieces.append(data)
                if on_token:
                    on_token(data)
                return False
            if isinstance(payload, dict) and payload.get("error"):
                raise APIError(self._error_message(payload, response.status_code))
            if isinstance(payload, dict) and payload.get("done") is True:
                return True
            piece = self._extract_text(payload)
            if piece:
                pieces.append(piece)
                if on_token:
                    on_token(piece)
            return False

        try:
            for raw in response.iter_lines(decode_unicode=True):
                if raw is None:
                    continue
                line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
                if line == "":
                    if process_event():
                        break
                elif line.startswith(":"):
                    continue
                elif line.startswith("event:"):
                    event_name = line[6:].strip() or "message"
                elif line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
            else:
                process_event()
        finally:
            response.close()

        answer = "".join(pieces)
        if not answer.strip():
            raise APIError("The API stream ended without an answer.")
        return answer

    def _read_ndjson(
        self,
        response: requests.Response,
        on_token: Optional[Callable[[str], None]],
    ) -> str:
        """Read newline-delimited JSON streams, such as Ollama-style NDJSON."""
        pieces: List[str] = []
        try:
            for raw in response.iter_lines(decode_unicode=True):
                if raw is None:
                    continue
                line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    pieces.append(line)
                    if on_token:
                        on_token(line)
                    continue
                if isinstance(payload, dict) and payload.get("error"):
                    raise APIError(self._error_message(payload, response.status_code))
                piece = self._extract_text(payload)
                if piece:
                    pieces.append(piece)
                    if on_token:
                        on_token(piece)
                if isinstance(payload, dict) and (
                    payload.get("done") is True or payload.get("completed") is True
                ):
                    break
        finally:
            response.close()

        answer = "".join(pieces)
        if not answer.strip():
            raise APIError("The API stream ended without an answer.")
        return answer

    def health(self) -> Any:
        """Fetch the API root/status response."""
        response = self._request("GET", headers={"Accept": "application/json"})
        payload = self._payload(response)
        response.close()
        if not response.ok:
            raise APIError(self._error_message(payload, response.status_code))
        return payload

    def ask(self, message: str, **kwargs: Any) -> str:
        """Alias for chat()."""
        return self.chat(message, **kwargs)
