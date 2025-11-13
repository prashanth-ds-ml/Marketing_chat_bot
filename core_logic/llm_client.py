"""
LLM client for Marketeer.

This module exposes a single function:

    generate_text(prompt: str, max_new_tokens: int = 256, temperature: float = 0.8, top_p: float = 0.9) -> str

Internally it:
- Loads the tokenizer & model once.
- Uses MODEL_ID from environment (or a sensible default).
- Lets `device_map="auto"` handle GPU/CPU placement when CUDA is available.
"""

import os
from typing import Optional

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM


# ----- Configuration -----

DEFAULT_MODEL_ID = "google/gemma-2-2b-it"
_MODEL_ID = os.getenv("MODEL_ID", DEFAULT_MODEL_ID)

_tokenizer: Optional[AutoTokenizer] = None
_model: Optional[AutoModelForCausalLM] = None


def _load_model_if_needed():
    """Lazy-load tokenizer and model into global variables."""
    global _tokenizer, _model

    if _tokenizer is not None and _model is not None:
        return

    has_cuda = torch.cuda.is_available()

    # bfloat16/float16 on GPU, float32 on CPU
    if has_cuda:
        dtype = torch.bfloat16
        device_map = "auto"   # let accelerate handle offload across GPU/CPU
    else:
        dtype = torch.float32
        device_map = None

    _tokenizer = AutoTokenizer.from_pretrained(_MODEL_ID)

    _model = AutoModelForCausalLM.from_pretrained(
        _MODEL_ID,
        dtype=dtype,          # use dtype instead of deprecated torch_dtype
        device_map=device_map,
    )

    # Ensure pad token exists (some causal models don't define it)
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token

    _model.eval()   # IMPORTANT: no _model.to(...) here


def generate_text(
    prompt: str,
    max_new_tokens: int = 256,
    temperature: float = 0.8,
    top_p: float = 0.9,
) -> str:
    """
    Generate text from the model given a plain prompt.

    Args:
        prompt: The input text prompt.
        max_new_tokens: Maximum number of new tokens to generate.
        temperature: Sampling temperature (>1 = more random, <1 = more focused).
        top_p: Nucleus sampling probability mass.

    Returns:
        The generated text (prompt excluded where possible).
    """
    if not isinstance(prompt, str):
        raise TypeError("prompt must be a string")

    cleaned_prompt = prompt.strip()
    if not cleaned_prompt:
        raise ValueError("prompt is empty after stripping whitespace")

    _load_model_if_needed()
    assert _tokenizer is not None
    assert _model is not None

    # DO NOT .to(device) here; accelerate handles device placement for us
    inputs = _tokenizer(
        cleaned_prompt,
        return_tensors="pt",
    )

    with torch.no_grad():
        output_ids = _model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            pad_token_id=_tokenizer.pad_token_id,
            eos_token_id=_tokenizer.eos_token_id,
        )

    full_text = _tokenizer.decode(
        output_ids[0],
        skip_special_tokens=True,
        clean_up_tokenization_spaces=True,
    )

    # Strip echoed prompt if present
    if full_text.startswith(cleaned_prompt):
        generated = full_text[len(cleaned_prompt):].lstrip()
    else:
        generated = full_text

    return generated.strip()
