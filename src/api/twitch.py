from fastapi import APIRouter


def create_twitch_router(auth):
    router = APIRouter(prefix="/api/twitch/auth")

    @router.get("")
    async def state():
        return auth.state()

    @router.post("/start")
    async def start():
        return await auth.start()

    @router.post("/cancel")
    async def cancel():
        await auth.cancel()
        return auth.state()

    @router.delete("")
    async def disconnect():
        await auth.disconnect()
        return auth.state()

    return router
