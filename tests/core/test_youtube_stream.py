import asyncio

import grpc
import pytest

from src.core.models import AppError


async def test_real_grpc_stream_uses_key_and_reads_text_and_eof():
    from src.adapters.proto.youtube_chat_pb2 import (
        LiveChatMessageListRequest,
        LiveChatMessageListResponse,
    )
    from src.adapters.youtube_stream import YouTubeStream

    requests = []

    async def respond(request, context):
        requests.append((request, dict(context.invocation_metadata())))
        yield LiveChatMessageListResponse(
            items=[
                {
                    "id": "m1",
                    "snippet": {
                        "type": 1,
                        "live_chat_id": "chat",
                        "text_message_details": {"message_text": "left"},
                    },
                    "author_details": {
                        "channel_id": "UCViewer",
                        "display_name": "Alice",
                    },
                }
            ]
        )

    server = grpc.aio.server()
    server.add_generic_rpc_handlers(
        (
            grpc.method_handlers_generic_handler(
                "youtube.api.v3.V3DataLiveChatMessageService",
                {
                    "StreamList": grpc.unary_stream_rpc_method_handler(
                        respond,
                        request_deserializer=LiveChatMessageListRequest.FromString,
                        response_serializer=LiveChatMessageListResponse.SerializeToString,
                    )
                },
            ),
        )
    )
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    stream = YouTubeStream(channel, "chat", "secret")
    try:
        page = await asyncio.wait_for(stream.read(), 2)
        assert (
            page["items"][0]["snippet"]["textMessageDetails"]["messageText"] == "left"
        )
        assert page["items"][0]["authorDetails"]["channelId"] == "UCViewer"
        assert requests[0][0].live_chat_id == "chat"
        assert set(requests[0][0].part) == {"id", "snippet", "authorDetails"}
        assert requests[0][1]["x-goog-api-key"] == "secret"
        with pytest.raises(AppError) as caught:
            await stream.read()
        assert caught.value.code == "connection_lost"
    finally:
        await stream.close()
        await server.stop(0)


@pytest.mark.parametrize(
    "status,code",
    [
        (grpc.StatusCode.RESOURCE_EXHAUSTED, "youtube_quota_exceeded"),
        (grpc.StatusCode.PERMISSION_DENIED, "youtube_key_invalid"),
        (grpc.StatusCode.FAILED_PRECONDITION, "youtube_chat_unavailable"),
    ],
)
async def test_rpc_status_is_translated_without_remote_details(status, code):
    from src.adapters.proto.youtube_chat_pb2 import (
        LiveChatMessageListRequest,
        LiveChatMessageListResponse,
    )
    from src.adapters.youtube_stream import YouTubeStream

    async def respond(request, context):
        await context.abort(status, "secret remote details")
        yield LiveChatMessageListResponse()

    server = grpc.aio.server()
    server.add_generic_rpc_handlers(
        (
            grpc.method_handlers_generic_handler(
                "youtube.api.v3.V3DataLiveChatMessageService",
                {
                    "StreamList": grpc.unary_stream_rpc_method_handler(
                        respond,
                        request_deserializer=LiveChatMessageListRequest.FromString,
                        response_serializer=LiveChatMessageListResponse.SerializeToString,
                    )
                },
            ),
        )
    )
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    stream = YouTubeStream(
        grpc.aio.insecure_channel(f"127.0.0.1:{port}"), "chat", "secret"
    )
    try:
        with pytest.raises(AppError) as caught:
            await asyncio.wait_for(stream.read(), 2)
        assert caught.value.code == code and "secret" not in str(caught.value)
    finally:
        await stream.close()
        await server.stop(0)
