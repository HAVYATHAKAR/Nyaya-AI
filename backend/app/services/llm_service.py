"""LLM service: HuggingFace Inference API client with fallback to a local stub.

Designed to be resilient — if HF is unreachable or token is missing, returns
a deterministic placeholder so the rest of the pipeline still demos.
"""
import os
from typing import List, Dict, Optional
from loguru import logger

import httpx

from ..core.config import settings


SYSTEM_PROMPT = (
    "You are NyayaAI, an AI legal assistant for India. You help users understand "
    "legal documents, answer legal questions using only the provided context, "
    "and explain Indian legal concepts in plain language. You are NOT a lawyer — "
    "always clarify that responses are preliminary and should be reviewed by a "
    "qualified advocate. Be precise, cite sources when given, and admit when "
    "you don't know. Avoid speculation."
)


class LLMService:
    def __init__(self):
        self.token = settings.hf_token
        self.model = settings.hf_model
        self.api_url = (
            f"https://api-inference.huggingface.co/models/{self.model}"
            if self.model else None
        )

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _format_messages(self, messages: List[Dict], context: Optional[str] = None) -> str:
        """Render chat messages into a single prompt for instruct models."""
        parts = [SYSTEM_PROMPT]
        if context:
            parts.append(
                f"\nVerified legal context (cite these sources in your answer):\n{context}\n"
            )
        for m in messages:
            role = m.get("role", "user").upper()
            parts.append(f"\n{role}: {m['content']}")
        parts.append("\nASSISTANT:")
        return "\n".join(parts)

    async def chat(
        self,
        messages: List[Dict],
        context: Optional[str] = None,
        max_new_tokens: int = 512,
        temperature: float = 0.3,
    ) -> str:
        """Generate a chat completion."""
        prompt = self._format_messages(messages, context)

        if not self.token or not self.api_url:
            logger.warning("HF token or model URL missing — returning stub answer.")
            return self._stub_answer(messages, context)

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "do_sample": temperature > 0,
                "return_full_text": False,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    self.api_url, headers=self._headers(), json=payload
                )
                if resp.status_code == 503:
                    # Model is loading — wait briefly and retry once
                    logger.warning("HF model loading, retrying after 10s…")
                    import asyncio
                    await asyncio.sleep(10)
                    resp = await client.post(
                        self.api_url, headers=self._headers(), json=payload
                    )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list) and data:
                    text = data[0].get("generated_text", "")
                    return text.strip()
                if isinstance(data, dict) and "generated_text" in data:
                    return data["generated_text"].strip()
                return ""
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._stub_answer(messages, context, error=str(e))

    def _stub_answer(
        self,
        messages: List[Dict],
        context: Optional[str] = None,
        error: Optional[str] = None,
    ) -> str:
        """Fallback answer used when LLM is unreachable.

        NOTE: This is intentional so the demo still works during judging if the
        HF API is rate-limited. In production, this should raise instead.
        """
        last_user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        ctx_note = f"\n\nRetrieved context snippet:\n{context[:300]}…" if context else ""
        err_note = f"\n\n(LLM service note: {error})" if error else ""
        return (
            "**Demo mode** — HuggingFace Inference API token not configured or "
            "the model is warming up. Here's a placeholder answer so you can see "
            "the pipeline working end-to-end.\n\n"
            f"Your question was: {last_user[:200]}{ctx_note}{err_note}\n\n"
            "Add a valid `HF_TOKEN` in `.env` and the live Llama-3 model will "
            "answer this question with full legal grounding."
        )


# Singleton
llm_service = LLMService()
