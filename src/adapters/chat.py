from typing import Awaitable, Callable, Protocol
import asyncio

CommentHandler = Callable[[str, str], Awaitable[None]]


class ChatAdapter(Protocol):
    async def connect(self, on_comment: CommentHandler) -> asyncio.Task[None]: ...
    async def disconnect(self) -> None: ...
