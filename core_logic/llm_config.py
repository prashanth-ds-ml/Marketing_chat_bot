"""
LLM configuration for Marketeer.

This module exposes helpers to get a LangChain ChatHuggingFace model,
backed by a local Hugging Face pipeline (for development).

Later, we can add a get_endpoint_chat_model() for HF Inference API.
"""

from functools import lru_cache

from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from transformers import BitsAndBytesConfig


MODEL_ID = "google/gemma-2-2b-it"  # <-- change if you're using a different repo


@lru_cache(maxsize=1)
def get_local_chat_model() -> ChatHuggingFace:
    """
    Return a singleton ChatHuggingFace model running locally via transformers pipeline.

    Uses 4-bit quantization to fit comfortably on a 6GB RTX 3060.
    """
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype="float16",
        bnb_4bit_use_double_quant=True,
    )

    # HuggingFacePipeline wraps a transformers.pipeline under the hood
    base_llm = HuggingFacePipeline.from_model_id(
        model_id=MODEL_ID,
        task="text-generation",
        pipeline_kwargs=dict(
            max_new_tokens=256,
            do_sample=True,
            temperature=0.8,
            top_p=0.9,
            return_full_text=False,  # we only want the generated continuation
        ),
        model_kwargs={
            "quantization_config": quant_config,
        },
    )

    chat_model = ChatHuggingFace(llm=base_llm)
    return chat_model
