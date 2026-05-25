from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from llmify import (
    AssistantMessage,
    ContentPartTextParam,
    Message,
    SystemMessage,
    UserMessage,
    ChatInvokeCompletion,
)

logger = logging.getLogger(__name__)


def _serialize_message(msg: Message) -> dict[str, Any]:
    match msg:
        case SystemMessage():
            return {"role": "system", "text": msg.text}
        case AssistantMessage():
            return {"role": "assistant", "text": msg.text}
        case UserMessage(content=str()):
            return {"role": "user", "text": msg.content}
        case UserMessage():
            text = "".join(
                part.text
                for part in msg.content
                if isinstance(part, ContentPartTextParam)
            )
            return {"role": "user", "text": text}


def _serialize_completion(completion: Any) -> Any:
    if isinstance(completion, BaseModel):
        return completion.model_dump(mode="json")
    return str(completion)


class TraceStore:
    def __init__(self, path: str | Path) -> None:
        self._root = Path(path)
        self._root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        *,
        messages: list[Message],
        result: ChatInvokeCompletion,
        model: str,
        output_format: type[BaseModel] | None,
        duration_s: float,
        params: dict[str, Any],
    ) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S.%f")[:-3]
        trace_dir = self._root / f"{ts}_{uuid.uuid4().hex[:6]}"
        trace_dir.mkdir(parents=True)

        trace = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "output_format": output_format.__name__ if output_format else None,
            "params": params,
            "duration_s": round(duration_s, 4),
            "messages": [_serialize_message(m) for m in messages],
            "completion": _serialize_completion(result.completion),
            "usage": result.usage.model_dump() if result.usage else None,
        }

        (trace_dir / "trace.json").write_text(
            json.dumps(trace, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def save_async(
        self,
        *,
        messages: list[Message],
        result: ChatInvokeCompletion,
        model: str,
        output_format: type[BaseModel] | None,
        duration_s: float,
        params: dict[str, Any],
    ) -> None:
        thread = threading.Thread(
            target=self._save_in_thread,
            kwargs={
                "messages": messages,
                "result": result,
                "model": model,
                "output_format": output_format,
                "duration_s": duration_s,
                "params": params,
            },
            daemon=True,
        )
        thread.start()

    def _save_in_thread(self, **kwargs: Any) -> None:
        try:
            self.save(**kwargs)
        except Exception:
            logger.exception("Failed to persist LLM trace")


class TracedChatModel:
    def __init__(self, llm: Any, store: TraceStore) -> None:
        self._llm = llm
        self._store = store

    @property
    def model(self) -> str:
        return self._llm.model

    async def invoke[T: BaseModel](
        self,
        messages: list[Message],
        output_format: type[T] | None = None,
        **kwargs: Any,
    ) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
        start = time.perf_counter()
        result = await self._llm.invoke(messages, output_format, **kwargs)
        duration = time.perf_counter() - start

        self._store.save_async(
            messages=messages,
            result=result,
            model=self.model,
            output_format=output_format,
            duration_s=duration,
            params=kwargs,
        )
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._llm, name)


def trace_llm(llm: Any, store: TraceStore | str | Path) -> TracedChatModel:
    if not isinstance(store, TraceStore):
        store = TraceStore(store)
    return TracedChatModel(llm, store)
