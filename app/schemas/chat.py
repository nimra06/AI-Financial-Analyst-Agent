"""Chat API and agent response models."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ChartType = Literal["revenue", "profit", "expenses", "trends", "none"]


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatResult(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    chart: Optional[ChartType] = None


class ChatMessageRecord(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    sources: list[str] = Field(default_factory=list)
    created_at: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: str
    history: list[ChatTurn] = Field(default_factory=list)
    monthly_records: list[dict]
    top_expense_categories: list[dict] = Field(default_factory=list)
    source_file: str = "upload"


class ChatResponse(BaseModel):
    result: ChatResult


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageRecord]
