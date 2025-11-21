Nice, let’s turn all that into a **clean roadmap** you can actually work through, phase by phase. Think of this as the “Marketeer x LangChain x HF” blueprint you can keep coming back to.

---

# 🧭 Marketeer Roadmap (LangChain + Hugging Face)

## Phase 0 – Current Baseline (where you are now)

**You already have:**

* Local HF model (Gemma) running on RTX 3060.
* Core modules:

  * `core_logic/llm_client.py` (manual `generate_text`)
  * `core_logic/copy_pipeline.py` (template-based copy + validators)
  * `core_logic/video_pipeline.py` (video beats + parsing + validators)
  * `ui/gradio_ui.py` (Gradio UI: Copy tab + Video tab)
  * Simple chat mode using:

    * `core_logic/chat_chain.py` (PromptTemplate + our custom MarketeerLLM / now simplified)
* Platform rules + validators from the notebook.

We’ll **evolve this** instead of throwing it away.

---

## Phase 1 – Switch to ChatHuggingFace Backend

**Goal:** Use **official LangChain-HuggingFace** integration instead of a custom wrapper, so future features (tools, structured outputs, etc.) are easier.

### 1.1. Dependencies

* Add to `requirements.txt`:

  ```txt
  langchain-huggingface
  langchain-core
  transformers
  accelerate
  bitsandbytes
  ```

### 1.2. LLM config module

Create something like `core_logic/llm_config.py`:

* **Local dev (pipeline-based):**

  ```python
  from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
  from transformers import BitsAndBytesConfig

  def get_local_chat_model():
      quant_config = BitsAndBytesConfig(
          load_in_4bit=True,
          bnb_4bit_quant_type="nf4",
          bnb_4bit_compute_dtype="float16",
          bnb_4bit_use_double_quant=True,
      )

      base_llm = HuggingFacePipeline.from_model_id(
          model_id="google/gemma-2-2b-it",
          task="text-generation",
          pipeline_kwargs=dict(
              max_new_tokens=256,
              do_sample=True,
              temperature=0.8,
              top_p=0.9,
              return_full_text=False,
          ),
          model_kwargs={"quantization_config": quant_config},
      )

      return ChatHuggingFace(llm=base_llm)
  ```

* Later we’ll add a `get_endpoint_chat_model()` for Spaces.

### 1.3. Deprecate `MarketeerLLM`

* Keep `core_logic/llm_client.py` around if other code still uses it.
* For chat + new logic, use `ChatHuggingFace` from `llm_config.get_local_chat_model()`.

**Deliverable:**
A single `ChatHuggingFace` object you can import anywhere as your main chat LLM.

---

## Phase 2 – Proper Chat Chain with System + History Messages

**Goal:** Make the copy chat flow use **LangChain-style messages** instead of raw strings, so context handling is cleaner.

### 2.1. New chat chain file

Refactor `core_logic/chat_chain.py`:

* Import:

  ```python
  from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
  from langchain_core.prompts import ChatPromptTemplate
  from core_logic.llm_config import get_local_chat_model
  from helpers.platform_rules import ...
  from helpers.validators import validate_and_edit
  ```

* Build a **System prompt** from campaign context + platform rules:

  ```python
  def build_system_message(req, platform_cfg):
      content = f"""
      You are an expert social media marketer.

      Brand: {req.brand}
      Product/Offer: {req.product}
      Target audience: {req.audience}
      Campaign goal: {req.goal}
      Platform: {platform_cfg.name}
      Tone: {req.tone}
      CTA style: {req.cta_style}
      Extra context: {req.extra_context}

      Follow platform rules and keep the final post within ~{platform_cfg.char_cap} characters.
      Respond ONLY with the post text (no explanations).
      """
      return SystemMessage(content=content.strip())
  ```

* Convert `chat_history` (list `[user, assistant]`) to messages:

  ```python
  def history_to_messages(history_pairs):
      msgs = []
      for u, a in history_pairs:
          if u:
              msgs.append(HumanMessage(content=u))
          if a:
              msgs.append(AIMessage(content=a))
      return msgs
  ```

* `chat_turn(...)`:

  ```python
  def chat_turn(req, user_message, history_pairs):
      platform_cfg = _get_platform_config(req.platform_name)
      chat_model = get_local_chat_model()

      system_msg = build_system_message(req, platform_cfg)
      history_msgs = history_to_messages(history_pairs)
      user_msg = HumanMessage(content=user_message)

      messages = [system_msg] + history_msgs + [user_msg]

      ai_msg = chat_model.invoke(messages)
      raw_text = ai_msg.content
      final_text, audit = validate_and_edit(raw_text, platform_cfg)
      return final_text, raw_text, audit
  ```

### 2.2. UI stays mostly same

* `ui/gradio_ui.py` continues passing `chat_history` and `user_message`.
* Internally, `chat_turn` now uses **true chat messages** and a **SystemMessage**.

**Deliverable:**
Your chat bot respects system instructions + history in a robust, LangChain-native way.

---

## Phase 3 – Structured Output for Video Script Generator

**Goal:** Instead of fragile JSON/beat parsing, use LangChain’s structured output to get reliable beat objects.

### 3.1. Define a Pydantic model

In `core_logic/video_schema.py`:

```python
from typing import List
from pydantic import BaseModel

class Beat(BaseModel):
    title: str
    voiceover: str
    on_screen: str
    shots: List[str]
    broll: List[str]
    captions: List[str]
    t_start: float
    t_end: float

class VideoPlan(BaseModel):
    blueprint_name: str
    duration_sec: int
    platform_name: str
    style: str
    beats: List[Beat]
```

### 3.2. Use structured output in `video_pipeline`

* Build a prompt that instructs the model to output that schema.
* Use `StructuredTool` or LangChain’s `with_structured_output(VideoPlan)` (depending on version).
* Replace manual JSON parsing with a direct Pydantic model.

**Deliverable:**
`generate_video_script()` returns a `VideoPlan` object directly, with clean per-beat data and fewer parsing errors.

---

## Phase 4 – LangChain Memory (Optional but Powerful)

**Goal:** Advanced memory if you want more than simple chat history.

### 4.1. Token-based memory

Use `ConversationTokenBufferMemory` instead of raw `chat_history`:

* Wrap it around your `ChatHuggingFace` model.
* Limit memory by tokens (e.g., last 1024 tokens).
* Still easy to connect to Gradio by syncing the memory with `chat_history`.

### 4.2. Knowledge-style memory (later)

If you want persistence per brand/campaign:

* Store brand facts in a DB and summarize them per session.
* Memory retrieval each time a session starts.

**Deliverable:**
Chat sessions that scale better (longer conversations) without bloating context.

---

## Phase 5 – Tools & Agents for “Smart Marketing Assistant”

**Goal:** Turn Marketeer from a “single LLM” into a **tool-using assistant**.

### 5.1. Tools

Some concrete tools:

* `generate_hashtags(copy, platform)`
* `rewrite_tone(copy, tone)`
* `check_length(copy, platform)` (wraps your validators)
* `summarize_campaign(history)`

Use LangChain’s tool abstraction (`@tool` or `Tool` class) to define them.

### 5.2. Router / Agent

Use an agent that decides:

* When user asks “shorten this” → use `rewrite_tone`.
* When user says “give options” → generate variants.
* When user says “turn this into a video script” → call video generator.

**Deliverable:**
Single chat entry point that can:

* Write copy
* Edit copy
* Generate video storyboards
* Explain why choices were made (if you want)

---

## Phase 6 – Hugging Face Spaces Deployment Plan

**Goal:** Clean, reproducible deployment.

### 6.1. Repo structure (already close, just formalize)

* `app.py` – Gradio entry
* `ui/` – UI code
* `core_logic/` – pipelines, chain logic
* `helpers/` – platform rules, validators
* `requirements.txt`
* `README.md`

### 6.2. Backend choice for Spaces

* **Dev / personal Space:**
  Use local model (pipeline) in `app.py` (like now).
* **Production / shared Space:**
  Switch `llm_config.get_local_chat_model()` to `get_endpoint_chat_model()` that uses `HuggingFaceEndpoint` and reads `HUGGINGFACEHUB_API_TOKEN` from secrets.

**Deliverable:**
A Space that others can open and:

* Fill brand/product/audience/goal
* Chat with the Marketeer bot
* Generate copy + video scripts
* With stable HF-hosted backend

---

## Phase 7 – “Strategist Mode” (Bonus)

**Goal:** Move beyond just *copy* to *campaign thinking*.

Ideas:

* A mode that, given brand + budget + timeframe, outputs:

  * channel mix (IG / LinkedIn / YouTube Shorts)
  * example posts per channel
  * rough posting cadence
* Use LangChain prompts with a “marketing strategist” SystemMessage.
* Let user toggle between “Copywriter Mode” and “Strategist Mode” in the UI.

**Deliverable:**
Marketeer feels like a mini marketing partner, not just a caption generator.

---

## How to Use This Roadmap

You can literally go phase by phase:

1. **Phase 1** – Swap to `ChatHuggingFace` backend.
2. **Phase 2** – Refactor `chat_chain` to use System + messages.
3. **Phase 3** – Structured outputs for the video planner.
4. **Phase 4+** – Optional memory / tools / agents / deployment polish.

Whenever you’re ready, tell me:

> “Let’s start Phase 1 step-by-step”

and I’ll write the exact code changes (file-by-file, minimal diff style) to get that phase done.









