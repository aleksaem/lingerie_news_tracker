"""
LLMClient — wrapper around Google Gemini API (google-genai SDK).

Used by ArticleFilterService to score and summarize articles.
Reads LLM_API_KEY and LLM_MODEL from Settings.
"""

from google import genai
from app.config import settings


class LLMClient:

    def __init__(self):
        self.client = genai.Client(api_key=settings.LLM_API_KEY)
        self.model = settings.LLM_MODEL

    async def complete(self, prompt: str) -> str:
        """
        Відправляє промпт і повертає текст відповіді.
        Єдина точка входу для всіх LLM викликів у проєкті.
        """
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            return response.text or ""

        except Exception as e:
            print(f"[LLMClient] Error: {e}")
            return ""
