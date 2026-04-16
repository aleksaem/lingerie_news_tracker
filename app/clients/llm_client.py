"""
LLMClient — wrapper around Anthropic Claude API.

Used by ArticleFilterService to score and summarize articles.
Reads LLM_API_KEY and LLM_MODEL from Settings.
"""

import anthropic
from app.config import settings


class LLMClient:

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.LLM_API_KEY)
        self.model = settings.LLM_MODEL

    async def complete(self, prompt: str) -> str:
        """
        Відправляє промпт і повертає текст відповіді.
        Єдина точка входу для всіх LLM викликів у проєкті.
        """
        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text

        except anthropic.RateLimitError:
            print("[LLMClient] Rate limit — чекаємо 60 секунд")
            import asyncio
            await asyncio.sleep(60)
            return await self.complete(prompt)

        except anthropic.APIError as e:
            print(f"[LLMClient] API error: {e}")
            return ""

        except Exception as e:
            print(f"[LLMClient] Unexpected error: {e}")
            return ""
