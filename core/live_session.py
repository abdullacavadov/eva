"""EVA üçün Gemini Live sessiyasının köməkçi idarəedicisi."""

from contextlib import asynccontextmanager

from google import genai


class LiveSessionManager:
    """Gemini client yaradılmasını və Live API bağlantısını idarə edir."""

    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key

    def create_client(self) -> genai.Client:
        """EVA-nın Live API versiyası ilə Gemini client yaradır."""
        return genai.Client(
            api_key=self.api_key,
            http_options={"api_version": "v1alpha"},
        )

    @asynccontextmanager
    async def connect(self, config):
        """Gemini Live sessiyasına qoşulur və çıxışda sessiyanı bağlayır."""
        client = self.create_client()
        async with client.aio.live.connect(
            model=self.model,
            config=config,
        ) as session:
            yield session
