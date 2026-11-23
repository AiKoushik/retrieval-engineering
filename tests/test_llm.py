import sys
import types

import pytest

from rx.llm import (NOT_FOUND, AnthropicLLM, ExtractiveLLM, OpenAILLM,
                    make_llm)

PROMPT = """Passages:
[1] (SPEC-112-C) Scope applies to housings. Packaging uses crates.
[2] (TR-7731) Tensile strength of lot H-2291 was 312 MPa. Result PASS.

Question: What tensile strength did lot H-2291 reach?
Answer briefly and cite passages like [1]."""


def test_extractive_quotes_and_cites():
    text = ExtractiveLLM(max_sentences=1).complete("sys", PROMPT)
    assert text == "Tensile strength of lot H-2291 was 312 MPa. [2]"


def test_extractive_says_not_found():
    prompt = PROMPT.replace("What tensile strength did lot H-2291 "
                            "reach?", "Who painted the canteen?")
    assert ExtractiveLLM().complete("sys", prompt) == NOT_FOUND


def fake_module(monkeypatch, name: str, **attrs) -> None:
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    monkeypatch.setitem(sys.modules, name, module)


def test_anthropic_adapter_without_network(monkeypatch):
    calls = {}

    class Messages:
        def create(self, **kwargs):
            calls.update(kwargs)
            block = types.SimpleNamespace(type="text", text="312 MPa [2]")
            return types.SimpleNamespace(content=[block])

    class Client:
        messages = Messages()
    fake_module(monkeypatch, "anthropic", Anthropic=Client)
    llm = AnthropicLLM(model="test-model")
    assert llm.complete("sys", "prompt") == "312 MPa [2]"
    assert calls["model"] == "test-model" and calls["system"] == "sys"


def test_openai_adapter_without_network(monkeypatch):
    class Completions:
        def create(self, **kwargs):
            msg = types.SimpleNamespace(content="ok [1]")
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=msg)])

    class Client:
        chat = types.SimpleNamespace(completions=Completions())
    fake_module(monkeypatch, "openai", OpenAI=Client)
    assert OpenAILLM(model="m").complete("sys", "p") == "ok [1]"


def test_make_llm():
    assert isinstance(make_llm(), ExtractiveLLM)
    with pytest.raises(ValueError):
        make_llm("oracle")
