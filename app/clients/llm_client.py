"""
LLMClient — wrapper around Anthropic Claude API.

Used by ArticleFilterService to score and summarize articles.
Reads LLM_API_KEY and LLM_MODEL from Settings.
"""

# TODO: import anthropic, Settings


class LLMClient:
    """
    Sends prompts to Claude and returns text completions.
    """

    def __init__(self):
        # TODO: init anthropic.AsyncAnthropic(api_key=settings.LLM_API_KEY)
        #       store settings.LLM_MODEL
        pass

    async def complete(self, prompt: str) -> str:
        """
        Send prompt to Claude, return response text.
        Expects caller to handle JSON parsing of the response.
        """
        # TODO: call client.messages.create(model=..., max_tokens=..., messages=[...])
        #       return response.content[0].text
        raise NotImplementedError
