import asyncio
from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    """Bound chunked uploads to 16 KiB with a ten-second upload deadline."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        chunks = []
        size = 0
        try:
            async with asyncio.timeout(10):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    size += len(message.get("body", b""))
                    if size > 16384:
                        return await JSONResponse({"detail": "Request too large"}, 413)(scope, receive, send)
                    chunks.append(message)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            return await JSONResponse({"detail": "Upload timeout"}, 408)(scope, receive, send)

        async def buffered_receive():
            if chunks:
                return chunks.pop(0)
            return await receive()
        await self.app(scope, buffered_receive, send)
