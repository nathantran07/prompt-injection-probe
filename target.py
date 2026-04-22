"""AcmeSoft support bot — demo target for prompt-injection probing."""
from __future__ import annotations

import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv()

SYSTEM_PROMPT = Path("system_prompt.txt").read_text(encoding="utf-8").strip()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

app = FastAPI(title="AcmeSoft Support Bot")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    result = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        temperature=0.7,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": req.message}],
    )
    text = "".join(block.text for block in result.content if block.type == "text")
    return ChatResponse(response=text)
