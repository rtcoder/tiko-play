"""Cancellable gRPC transport, no worker thread or local server."""

import grpc
from google.protobuf.json_format import MessageToDict

from src.adapters.proto.youtube_chat_pb2 import (
    LiveChatMessageListRequest,
    LiveChatMessageListResponse,
)
from src.core.models import AppError


class YouTubeStream:
    def __init__(self, channel, chat_id, key):
        self.channel = channel
        rpc = channel.unary_stream(
            "/youtube.api.v3.V3DataLiveChatMessageService/StreamList",
            request_serializer=LiveChatMessageListRequest.SerializeToString,
            response_deserializer=LiveChatMessageListResponse.FromString,
        )
        self.call = rpc(
            LiveChatMessageListRequest(
                live_chat_id=chat_id, part=["id", "snippet", "authorDetails"]
            ),
            metadata=(("x-goog-api-key", key),),
        )

    async def read(self):
        try:
            response = await self.call.read()
            if response is grpc.aio.EOF:
                raise AppError(
                    "connection_lost",
                    "YouTube zakończył połączenie z czatem. Uruchom nasłuch ponownie.",
                )
            return MessageToDict(response)
        except grpc.aio.AioRpcError as exc:
            status = exc.code()
            if status == grpc.StatusCode.RESOURCE_EXHAUSTED:
                raise AppError(
                    "youtube_quota_exceeded",
                    "Limit YouTube API został wyczerpany. Sprawdź projekt Google Cloud lub spróbuj później.",
                ) from None
            if status in (
                grpc.StatusCode.UNAUTHENTICATED,
                grpc.StatusCode.PERMISSION_DENIED,
            ):
                raise AppError(
                    "youtube_key_invalid",
                    "YouTube odrzucił dostęp. Sprawdź klucz API i dostępność transmisji.",
                ) from None
            if status in (
                grpc.StatusCode.FAILED_PRECONDITION,
                grpc.StatusCode.NOT_FOUND,
            ):
                raise AppError(
                    "youtube_chat_unavailable",
                    "Czat YouTube jest wyłączony, zakończony lub niedostępny.",
                ) from None
            raise AppError(
                "connection_lost",
                "Utracono połączenie z YouTube. Uruchom nasłuch ponownie.",
            ) from None

    async def close(self):
        self.call.cancel()
        await self.channel.close()


async def open_youtube_stream(chat_id, key):
    channel = grpc.aio.secure_channel(
        "youtube.googleapis.com:443",
        grpc.ssl_channel_credentials(),
        options=(
            ("grpc.max_receive_message_length", 4 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 60000),
            ("grpc.keepalive_timeout_ms", 20000),
        ),
    )
    try:
        return YouTubeStream(channel, chat_id, key)
    except BaseException:
        await channel.close()
        raise
