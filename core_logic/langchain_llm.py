"""
LangChain-compatible LLM wrapper around our existing generate_text().

This lets us use LangChain chains, prompts, and memory
without changing the underlying HF model logic.
"""

from typing import Any, Dict, List, Optional

from langchain_core.language_models.llms import LLM

from .llm_client import generate_text


class MarketeerLLM(LLM):
    """
    Minimal LangChain LLM that just calls our generate_text() helper.
    """

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        # You can pass temp/top_p via kwargs if you want, or keep fixed config.
        text = generate_text(
            prompt=prompt,
            max_new_tokens=kwargs.get("max_new_tokens", 256),
            temperature=kwargs.get("temperature", 0.8),
            top_p=kwargs.get("top_p", 0.9),
        )

        # Apply stop tokens if provided
        if stop:
            for s in stop:
                if s in text:
                    text = text.split(s)[0]
                    break

        return text.strip()

    @property
    def _llm_type(self) -> str:
        return "marketeer_llm"
