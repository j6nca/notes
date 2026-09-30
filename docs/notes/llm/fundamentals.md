---
tags:
  - WIP
  - llm
  - ai
date: "2026-09-25"
title: LLM Fundamentals
---

> [!faq]- Disclaimer:
> Concepts here are stable; the numbers around them (context sizes, prices, what counts as "long") are not. Anything quantitative is deliberately vague. Check the provider's docs or `llama-server` output for the real figure.

# Why this page

Every tool built on an LLM, from a chat window to a coding agent, is a thin layer over the same handful of mechanics. Once you can see tokens, the context window, and the prefill/decode split, most "weird" model behaviour (cost, latency, forgetting, refusing mid-sentence) stops being weird. This page is the mental model; provider-specific notes go elsewhere.

# The one-sentence model

An LLM takes a sequence of tokens and predicts the next one. Everything else, chat, tools, agents, memory, is scaffolding that decides *what sequence to hand it* and *what to do with the token that comes back*.

# Tokens

Models don't read characters or words. Text is chopped into **tokens** by a tokenizer (usually byte-pair encoding), and each model family has its own vocabulary. Rules of thumb:

- English prose lands around 3 to 4 characters per token, or roughly 3/4 of a word.
- Code, JSON, URLs, and non-English text tokenize *worse*. Whitespace-heavy YAML is expensive; base64 is brutal.
- The same string tokenizes differently across model families, so token counts don't transfer between providers.

Tokens are the unit of everything: pricing, context limits, rate limits, speed (tokens/sec), and `max_tokens`. When something is "too long", it's too long in tokens, not characters.

**Why it matters in practice**

- Tokens are why a model can be bad at counting letters or reversing strings. It never saw the letters.
- Tool output that you dump into the conversation (a `kubectl get -o json`, a full log file) is often the single biggest token cost in an agent session. Truncate or summarize at the source.
- Most providers expose a count-tokens endpoint, and `llama.cpp` has `/tokenize`. Use them rather than guessing.

# Context window

The **context window** is the maximum number of tokens the model can attend to in one call: system prompt + conversation history + tool definitions + tool results + the response it's currently generating. It's a hard limit, and *input and output share it*.

Things that quietly eat context:

| Source | Notes |
| --- | --- |
| System prompt | Paid on every single call |
| Tool/function definitions | JSON schemas add up fast with many tools (MCP servers are a common culprit) |
| Tool results | Usually the dominant cost in agent loops |
| Conversation history | Grows monotonically unless something trims it |
| Reserved output | `max_tokens` is carved out of the same budget |

**Advertised vs effective context.** A model that *accepts* a very long context doesn't necessarily *use* it well. Retrieval quality tends to degrade with length, and information in the middle of a long prompt is recalled worse than the start or end ("lost in the middle"). Put the important stuff early or late, and don't treat the max as a target.

**Context is also a compute and memory cost**, not just a limit. See [[#KV cache]] below and the memory-budget discussion in [[projects/homelab/strix_halo_ai_box|strix_halo_ai_box]].

# Prefill and decode

Every request has two phases, and they have completely different performance profiles.

**Prefill (prompt processing).** The model ingests the entire input in one parallel pass and builds its internal state for every token. This is compute-bound: lots of matrix math at once. Cost scales with input length, and it's what you wait for before the first token appears (time-to-first-token, TTFT).

**Decode (token generation).** The model then produces output one token at a time, each step reading back the state it built. This is memory-bandwidth-bound: every step streams the model's weights through the GPU again. Speed is reported as tokens/sec and is roughly constant per token regardless of how long the prompt was.

This split explains a lot:

- A long prompt with a short answer is prefill-dominated. Long-context RAG and "read this whole repo" prompts live here.
- A short prompt with a long answer is decode-dominated. Most chat is this.
- Different hardware wins different phases. On the AI box, ROCm beats Vulkan on prompt processing but not on generation, which is why that page splits the decision by workload.
- Input tokens are cheaper than output tokens at every provider. Prefill is batched and parallel; decode isn't.

> [!note] "Prefill" has a second meaning
> In chat APIs, **assistant prefill** means starting the assistant's turn for it, e.g. seeding the response with `{` to force JSON, or with a phrase that steers the tone. The model continues from what you wrote. Same word, different concept: one is a phase of inference, the other is a prompting technique. Context usually makes it clear which one is meant.

# KV cache

During prefill the model computes a key and value vector for every token in every attention layer. It keeps them around so decode doesn't have to recompute the whole prompt for each new token. That stash is the **KV cache**.

- It lives in GPU memory alongside the weights, and it grows linearly with context length. On a classic dense transformer, a long context can cost as much memory as the model itself.
- This is why a local server has a `--ctx-size` flag: it pre-allocates the cache. Bigger context = less room for a second model.
- Architectures vary a lot here. Grouped-query attention, sliding windows, and hybrid linear-attention layers all shrink the cache. Don't assume the KV footprint of one model family applies to another.
- When a local server "unloads on idle", the KV cache is the thing being freed.

# Prompt caching

Because prefill is deterministic for a given prefix, providers (and `llama-server`) can **cache the KV state of a prompt prefix** and reuse it on the next call. Cached input tokens are billed at a fraction of the price and skip most of the prefill latency.

The rule that follows: **stable content first, volatile content last.** A cache hit requires an exact prefix match, so:

- System prompt and tool definitions go at the top and never change mid-session.
- Long reference documents come next.
- The conversation turn goes last.
- Anything that changes on every call (timestamps, request IDs, a random nonce) placed early in the prompt will bust the cache for everything after it.

Agents lean on this heavily. Each turn in a loop re-sends the whole history, and without caching every turn would re-prefill the entire session.

# Compaction

Conversation history only grows, and the context window doesn't. **Compaction** (also called context management or summarization) is what a harness does when it gets near the limit:

1. Take the older part of the transcript.
2. Replace it with a summary written by the model itself (or a cheaper one), usually covering goals, decisions made, files touched, and open questions.
3. Keep the most recent turns verbatim so the immediate task isn't lost.
4. Continue in a fresh, smaller context.

Related, lighter-touch strategies:

- **Tool-result pruning.** Drop or truncate old tool outputs (that huge JSON blob from ten turns ago) while keeping the message that says the call happened.
- **Sliding window.** Just drop the oldest turns. Cheap, but loses the "why".
- **External memory.** Write durable facts to a file or store and re-load them on demand instead of carrying them in context. This is what a coding agent's memory directory or a project `CLAUDE.md` is doing.

Compaction is lossy by design. Things that survive it well are things that were written down explicitly (a plan, a decision, a file path). Things that don't are implicit context you assumed the model "remembered". If a long agent session starts going sideways after a compaction, that's usually why. Ask it to write the plan down before the limit, not after.

# Sampling

Given the probability distribution over the next token, **sampling** decides which one to emit.

| Knob | What it does |
| --- | --- |
| `temperature` | Flattens (high) or sharpens (low) the distribution. 0 is near-deterministic; higher gives more varied output |
| `top_p` | Only sample from the smallest set of tokens whose probabilities sum to *p* |
| `top_k` | Only sample from the *k* most likely tokens |
| `max_tokens` | Hard stop on output length. Hitting it truncates mid-thought, so check the stop reason |
| `stop` | Sequences that end generation early |

For anything structured (code, JSON, tool calls) keep temperature low. Most APIs ask you to set temperature *or* top_p, not both. Reasoning/thinking modes often ignore or fix these knobs entirely.

# Chat structure

The model still only sees one token sequence. A chat API wraps messages in a **chat template** with role markers (`system`, `user`, `assistant`, `tool`) that the model was trained to respect. Consequences:

- The **system prompt** is just tokens at the front of the sequence. Its authority comes from training, not from any enforcement, which is why prompt injection works: injected text in a tool result is the same kind of thing as the system prompt from the model's point of view.
- Local models require the *right* template for their family. A model that seems dumb through an OpenAI-compatible endpoint is frequently a template mismatch.
- **Tool use** is the model emitting a specially formatted token sequence that the harness parses, executes, and feeds back as a `tool` message. The model never runs anything. The loop (model → tool call → tool result → model) is the whole of what an "agent" is.

# Fitting it together

A single agent turn, end to end:

1. Harness assembles the sequence: system prompt, tool schemas, history (possibly compacted), latest user message.
2. Tokenize. Check it fits the context window with room for output.
3. Prefill. The cached prefix is reused if the prompt was ordered well. TTFT is paid here.
4. Decode. Tokens stream out until a stop sequence, `max_tokens`, or a tool call.
5. If it's a tool call, run it, append the result, go to 1. Otherwise show the user the text.
6. Somewhere in here, if history got too long, compact.

Cost is tokens in and tokens out. Latency is prefill for the input plus decode for the output. Quality is bounded by what's actually in the context, not by what you assumed was there.

# Glossary

- **Token**: the unit of text the model operates on; roughly 3/4 of an English word.
- **Context window**: the max tokens per call, shared between input and output.
- **Prefill**: the parallel pass that processes the input; compute-bound.
- **Decode**: the sequential pass that generates output one token at a time; bandwidth-bound.
- **TTFT**: time-to-first-token; mostly prefill.
- **KV cache**: per-token attention state kept in memory so decode doesn't recompute the prompt.
- **Prompt caching**: reusing KV state across calls for an identical prefix.
- **Compaction**: summarizing older history to reclaim context.
- **Assistant prefill**: starting the model's response for it to steer output.
- **Chat template**: the role markup that turns a message list into one token sequence.
- **Quantization**: storing weights at lower precision to shrink memory and speed decode, at some quality cost. See [[projects/homelab/strix_halo_ai_box|strix_halo_ai_box]].

# References

- [Tiktokenizer](https://tiktokenizer.vercel.app/) for seeing how text actually tokenizes
- [Lost in the Middle](https://arxiv.org/abs/2307.03172) on long-context recall
- [llama.cpp server docs](https://github.com/ggml-org/llama.cpp/tree/master/tools/server) for `--ctx-size`, prompt caching, and `/tokenize`
- [[projects/homelab/ai_workspace|ai_workspace]] and [[projects/homelab/strix_halo_ai_box|strix_halo_ai_box]] for where these ideas meet real hardware
