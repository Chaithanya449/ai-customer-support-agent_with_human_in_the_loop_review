"""FastAPI HTTP interface for the e-commerce support agent."""

from uuid import uuid4
import sqlite3
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import chat
from tools import (
    DB_PATH,
    ensure_refund_requests_table,
    ensure_review_schema,
    list_pending_refunds,
    list_pending_reviews,
    review_refund,
    review_return,
)


app = FastAPI(
    title="E-commerce Customer Support API",
    description="Chat with the LangGraph support agent about orders and returns.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}):3000",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, max_length=128)


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str


class ReviewDecision(BaseModel):
    decision: Literal["approve", "reject"]
    note: str = Field(default="", max_length=1000)


@app.get("/health")
def health() -> dict[str, str]:
    """Report API and SQLite database availability."""
    try:
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as connection:
            connection.execute("SELECT 1 FROM orders LIMIT 1").fetchone()
    except sqlite3.Error as error:
        raise HTTPException(status_code=503, detail="Database unavailable") from error
    return {"status": "ok", "database": "ok"}


@app.post("/chat", response_model=ChatResponse)
def send_message(request: ChatRequest) -> ChatResponse:
    """Send a message and continue the supplied conversation, if provided."""
    conversation_id = request.conversation_id or str(uuid4())
    try:
        reply = chat(request.message.strip(), thread_id=conversation_id)
    except Exception as error:
        message = str(error).lower()
        if "rate" in message or "429" in message:
            raise HTTPException(
                status_code=503,
                detail="The AI service is busy. Please try again shortly.",
            ) from error
        raise HTTPException(
            status_code=500,
            detail="The support agent could not process this message.",
        ) from error
    return ChatResponse(conversation_id=conversation_id, reply=reply)


@app.get("/review/queue")
def review_queue() -> dict[str, list[dict]]:
    """Return pending return and refund requests for the human review panel."""
    ensure_review_schema()
    ensure_refund_requests_table()
    return {
        "returns": [dict(row) for row in list_pending_reviews()],
        "refunds": [dict(row) for row in list_pending_refunds()],
    }


@app.post("/review/{request_type}/{request_id}")
def decide_review(request_type: Literal["returns", "refunds"], request_id: int, decision: ReviewDecision) -> dict[str, str]:
    """Approve or reject one pending return or refund request as a human reviewer."""
    if request_type == "returns":
        result = review_return(request_id, decision.decision, decision.note)
    else:
        result = review_refund(request_id, decision.decision, decision.note)
    return {"message": result}
