"""Gemini Live session helpers for EVA."""

from contextlib import asynccontextmanager

from google import genai


class LiveSessionManager:
    """Own Gemini client creation and Live session connection details."""

    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key

    def create_client(self) -> genai.Client:
        """Create a Gemini client with EVA's Live API version."""
        return genai.Client(
            api_key=self.api_key,
            http_options={"api_version": "v1alpha"},
        )

    @asynccontextmanager
    async def connect(self, config):
        """Yield a connected Gemini Live session and close it afterwards."""
        client = self.create_client()
        async with client.aio.live.connect(
            model=self.model,
            config=config,
        ) as session:
            yield session
