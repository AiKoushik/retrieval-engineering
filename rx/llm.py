"""One interface for language models, an offline stub, three adapters."""
from __future__ import annotations

import os
import re
from typing import Protocol, runtime_checkable

from rx.textutil import analyze, split_sentences


# region: llm-protocol
@runtime_checkable
class LLM(Protocol):
    """Anything that turns a system prompt and a prompt into text."""

    def complete(self, system: str, prompt: str) -> str:
        ...
# endregion: llm-protocol


# region: extractive-llm
# "[3] (TR-7731) text...": number, optional (doc_id) label, text
PASSAGE_RE = re.compile(r"^\[(\d+)\]\s*(?:\([^)]*\)\s*)?(.*)$",
                        re.MULTILINE)
QUESTION_RE = re.compile(r"^Question:\s*(.*)$", re.MULTILINE)
NOT_FOUND = "I cannot find the answer in the provided passages."


class ExtractiveLLM:
    """An offline stand-in that quotes the best-matching sentences.

    It reads the numbered passages ('[n] ...' lines) and the
    'Question:' line out of the prompt, scores every sentence by
    how many question words it shares, and returns the top ones
    with their [n] citations. Deterministic and free; it cannot
    reason, add up numbers or notice contradictions.
    """

    def __init__(self, max_sentences: int = 2, min_overlap: int = 2):
        self.max_sentences = max_sentences
        self.min_overlap = min_overlap

    def complete(self, system: str, prompt: str) -> str:
        match = QUESTION_RE.search(prompt)
        wanted = set(analyze(match.group(1))) if match else set()
        scored = []
        for m in PASSAGE_RE.finditer(prompt):
            n = int(m.group(1))
            for pos, sentence in enumerate(split_sentences(m.group(2))):
                overlap = len(wanted & set(analyze(sentence)))
                scored.append((-overlap, n, pos, sentence))
        scored.sort()
        best = [s for s in scored[:self.max_sentences]
                if -s[0] >= self.min_overlap]
        if not best:
            return NOT_FOUND
        return " ".join(f"{s} [{n}]" for _, n, _, s in best)
# endregion: extractive-llm


# region: anthropic-llm
class AnthropicLLM:
    """Claude through the Anthropic SDK (pip install -e .[llm]).

    Reads ANTHROPIC_API_KEY; RX_ANTHROPIC_MODEL picks the model.
    """

    def __init__(self, model: str | None = None,
                 max_tokens: int = 1024):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get(
            "RX_ANTHROPIC_MODEL", "claude-sonnet-5-5")
        self.max_tokens = max_tokens

    def complete(self, system: str, prompt: str) -> str:
        reply = self.client.messages.create(
            model=self.model, max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}])
        return "".join(block.text for block in reply.content
                       if block.type == "text")
# endregion: anthropic-llm


# region: openai-llm
class OpenAILLM:
    """A chat model through the OpenAI SDK (pip install -e .[llm]).

    Reads OPENAI_API_KEY; RX_OPENAI_MODEL picks the model.
    """

    def __init__(self, model: str | None = None):
        import openai
        self.client = openai.OpenAI()
        self.model = model or os.environ.get(
            "RX_OPENAI_MODEL", "gpt-4.1-mini")

    def complete(self, system: str, prompt: str) -> str:
        reply = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt}])
        return reply.choices[0].message.content or ""
# endregion: openai-llm


# region: local-llm
THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


def thinking_off(url: str) -> dict:
    """The request field that turns a model's thinking mode off:
    Ollama reads reasoning_effort, vLLM and llama.cpp the template."""
    if ":11434" in url:
        return {"reasoning_effort": "none"}
    return {"chat_template_kwargs": {"enable_thinking": False}}


class LocalLLM:
    """An open model on your own machine, free and with no key.

    Any server that speaks the OpenAI chat API works: Ollama, vLLM,
    llama.cpp's server, LM Studio. RX_LOCAL_URL picks the server
    (default: Ollama on this machine), RX_LOCAL_MODEL the model.
    """

    def __init__(self, model: str | None = None,
                 url: str | None = None, max_tokens: int = 600):
        self.model = model or os.environ.get(
            "RX_LOCAL_MODEL", "qwen3.8:27b")
        self.url = (url or os.environ.get(
            "RX_LOCAL_URL", "http://127.0.0.1:11434/v1")).rstrip("/")
        self.max_tokens = max_tokens
        self.usage: dict = {}       # the server's token counts, last call

    def complete(self, system: str, prompt: str) -> str:
        import json
        import urllib.error
        import urllib.request
        messages = [{"role": "user", "content": prompt}]
        if system:
            messages.insert(0, {"role": "system", "content": system})
        body = {"model": self.model, "messages": messages,
                "temperature": 0, "seed": 0,
                "max_tokens": self.max_tokens, **thinking_off(self.url)}
        req = urllib.request.Request(
            self.url + "/chat/completions", json.dumps(body).encode(),
            {"Content-Type": "application/json",
             "Authorization": "Bearer local"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data = json.load(r)
        except urllib.error.HTTPError as e:
            said = e.read().decode(errors="replace")[:300]
            hint = (f"does it serve {self.model!r}? RX_LOCAL_MODEL"
                    if "context" not in said else
                    "the prompt is longer than the server's context: "
                    "OLLAMA_CONTEXT_LENGTH=32768, or vLLM's "
                    "--max-model-len 32768")
            raise RuntimeError(f"the model server at {self.url} "
                               f"answered {e.code}: {said} ({hint})") from e
        except (urllib.error.URLError, OSError) as e:
            raise RuntimeError(
                f"no model server at {self.url} ({e}); start Ollama "
                "or vLLM, or set RX_LOCAL_URL") from e
        reply = data["choices"][0]["message"]
        self.usage = data.get("usage") or {}
        text = THINK_RE.sub("", reply.get("content") or "")
        return text.split("<think>")[0].strip()   # cut off mid-thought
# endregion: local-llm


# region: make-llm
def make_llm(name: str = "extractive") -> LLM:
    """'extractive' (offline), 'local', 'anthropic' or 'openai'."""
    makers = {"extractive": ExtractiveLLM, "local": LocalLLM,
              "anthropic": AnthropicLLM, "openai": OpenAILLM}
    if name not in makers:
        raise ValueError(f"unknown LLM {name!r}")
    return makers[name]()
# endregion: make-llm
