from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatThreadCreateRequest(BaseModel):
    title: str | None = None
    class_id: str | None = None
    chapter_id: str | None = None
    assignment_id: str | None = None


class ChatSendMessageRequest(BaseModel):
    content: str


class ChatGeneratedAssetResponse(BaseModel):
    asset_type: str
    title: str | None = None
    description: str | None = None
    external_url: str | None = None
    payload_json: dict[str, Any] = Field(default_factory=dict)


class ChatToolCallResponse(BaseModel):
    tool_name: str
    status: str
    reason: str | None = None
    output_json: dict[str, Any] | None = None


class ChatMessageResponse(BaseModel):
    message_id: str
    chat_id: str
    role: str
    content: str
    tool_name: str | None = None
    tool_input_json: dict[str, Any] | None = None
    tool_output_json: dict[str, Any] | None = None
    asset_type: str | None = None
    asset_json: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatThreadResponse(BaseModel):
    chat_id: str
    student_id: str
    class_id: str | None = None
    chapter_id: str | None = None
    assignment_id: str | None = None
    title: str | None = None
    status: str
    context_json: dict[str, Any]
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatThreadListItem(BaseModel):
    chat_id: str
    title: str | None = None
    class_id: str | None = None
    chapter_id: str | None = None
    assignment_id: str | None = None
    status: str
    message_count: int = 0
    last_message_preview: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatSendMessageResponse(BaseModel):
    chat: ChatThreadResponse
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    tool_calls: list[ChatToolCallResponse] = Field(default_factory=list)
    generated_assets: list[ChatGeneratedAssetResponse] = Field(default_factory=list)
