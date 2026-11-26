---
date: 2026-10-13
authors:
  - chris-bao
categories:
  - AI Gateway
title: From 6 Seconds to 0.5 Seconds - Azure AI Gateway Semantic Caching with Redis
---
#apim

## Background

In this article, I want to share a particularly interesting AI solution: **semantic caching**. It can improve response speed, reduce latency, and deliver a better user experience for LLM-powered applications.

After reading this post, you can understand why semantic caching matters, how it differs from KV caching inside the model, and how to implement it with **Azure Managed Redis**, **Azure AI Gateway**, and **Microsoft Foundry**.

![[Semantic_Caching_Reduces_Model_Latency.png]]

## Why Do We Need Semantic Caching?

##### LLM latency fundamentals

If we analyze latency based on how large language models work, we can split it into two phases: **Prompt Processing** (input token handling) and **Autoregressive Generation** (output token generation).

**Prompt Processing**

- Processing style: thanks to self-attention in the Transformer architecture, all input tokens can be processed in parallel
- Latency pattern: the model handles the full prompt as one batch
- Per-token cost: very low (about 0.01–0.05 ms)
- Scalability: grows roughly linearly with token count

Think of this phase as reading an entire paragraph at once, not word by word. Whether your prompt is 100 tokens or 1,000 tokens, the model can process the whole prompt in one shot.

**Autoregressive Generation**

- Processing style: strictly sequential, one token at a time
- Latency pattern: each generated token becomes input for the next token (autoregressive)
- Per-token cost: much higher (about 5–20 ms)
- Scalability: still linear in token count, but at a much larger constant factor

Think of this phase as writing a reply word by word. Each new token depends on everything generated before it. This step cannot be parallelized—you must wait for token *n* before generating token *n+1*.

So in theory, most end-to-end latency comes from the generation phase. To address that, the industry has introduced many optimizations at the model level, such as:

- **Key-Value (KV) caching**: this mainly optimizes attention computation. Without cache, every new token forces the model to recompute relationships across all previous tokens. That leads to roughly O(n²) work. With KV cache, previously computed key-value pairs are reused to avoid redundant computation.
- **Mixture of Experts (MoE)**: the model is partitioned so that only relevant experts are activated per token, reducing global computation while preserving quality.

Beyond these low-level techniques, can we optimize at the **Agent application layer**? One practical answer is **semantic caching**!

##### What is semantic caching?

Unlike **KV caching** above, semantic caching works at the Agent/application layer. It builds on classic software caching patterns, then adds vectorization via an **embedding model** and **semantic search**.

In essence, it is the same idea as “index building” and “retrieval” in RAG—applied to the caching domain.

In the following sections, let’s see how to implement semantic caching with **Azure Managed Redis**, **Azure AI Gateway**, and **Microsoft Foundry**.

## Architecture: Semantic Caching with Redis

![[Pasted image 20260604112902.png]]

The overall design looks like this:

- **Microsoft Foundry**: deploy `text-embedding-3-small` and `gpt-4.1-mini`, and expose their endpoints.
- **APIM**: create two `backend` instances for the embedding and chat endpoints, plus an `api` surface for Agents to consume. Semantic caching is enabled through **Azure AI Gateway** policies on this layer. We will walk through the policy configuration shortly.
- **Azure Managed Redis**: provision a Redis cluster and its underlying data store.

##### Model deployment

Below are the deployed models in this lab:

![[Pasted image 20260604115442.png]]

##### Azure Managed Redis

**Azure Managed Redis** is the current recommended caching service on Azure, replacing the older **Azure Cache for Redis**:

![[Pasted image 20260604131322.png]]

In this article, we focus on architecture and measured latency improvements. I will dive deeper into Redis semantic search capabilities in a follow-up post—stay tuned!

##### APIM integration

First, we create two backends: `embeddings-backend` and `foundry1`, mapped to the embedding and chat endpoints:

![[Pasted image 20260604130317.png]]

Next, we create an `api` instance, enable its **managed identity**, and grant roles so it can call models deployed on Microsoft Foundry:

![[Pasted image 20260604131611.png]]

Those steps are standard APIM setup. The interesting part is cache placement: by default, APIM can use its built-in cache, but here we onboard the Redis cluster above as an **external cache**:

![[Pasted image 20260604130944.png]]

The full lab environment is more complex than we can unpack in one post. You can find the complete project in my GitHub repo: [azure-ai-gateway-labs](https://github.com/baoqger/azure-ai-gateway-labs.git).

Now let’s look at the core semantic caching policies.

## Semantic caching policies

![[Pasted image 20260604132621.png]]

Three policy elements work together: `llm-semantic-cache-lookup`, `set-backend-service`, and `llm-semantic-cache-store`. This is a classic **cache-aside** pattern:

- `llm-semantic-cache-lookup`: the gateway queries Redis using semantic search to find the closest cached entry.
- `set-backend-service`: on a cache miss, route the request to the LLM backend.
- `llm-semantic-cache-store`: write the LLM response back to cache.

Semantic caching adds a few important knobs:

- `embedding-backend-id`: the gateway calls the embedding backend first to vectorize the current prompt.
- `score-threshold`: Redis computes similarity against stored vectors; this threshold decides whether the cache is considered a hit. On a hit, the gateway returns cached data directly.
- `duration`: on a miss, after the LLM responds, the result is stored with this TTL.

That is the high-level flow. I will break down Redis semantic search internals in a future article.

Next step, let’s run the demo.

## Demo

We validate the behavior with the script below:

```python
from openai import AzureOpenAI

import time, random

runs = 20
sleep_time_ms = 10
questions = ["How to Brew the Perfect Cup of Coffee?",
             "What are the steps to Craft the Ideal Espresso?",
             "Tell me how to create the best steaming Java?",
             "Explain how to make a caffeinated brewed beverage?"]
api_runs = []  # Response Times for each run
client = AzureOpenAI(
    azure_endpoint = f"{apim_resource_gateway_url}/{inference_api_path}",
    api_key = api_key,
    api_version = inference_api_version
)

for i in range(runs):
    print(f"▶️ Run {i+1}/{runs}:")
    random_question = random.choice(questions)
    print("💬 ", random_question)

    start_time = time.time()
    response = client.chat.completions.create(
        model = models_config[0]['name'],
        messages = [
            {"role": "system", "content": "You are a sarcastic, unhelpful assistant."},
            {"role": "user", "content": random_question}
        ])
    response_time = time.time() - start_time

    print(f"⌚ {response_time:.2f} seconds")

    # Uncomment to print the response
    #print(f"💬 {response.choices[0].message.content}\n")

    api_runs.append(response_time)
    time.sleep(sleep_time_ms/1000)
```

I prepared several semantically similar prompts, then sent 20 requests to the Azure AI Gateway endpoint—each run picks a random prompt and records latency:

```plain
▶️ Run 1/20:
💬 Tell me how to create the best steaming Java?
⌚ 6.27 seconds

▶️ Run 2/20:
💬 What are the steps to Craft the Ideal Espresso?
⌚ 0.56 seconds

▶️ Run 3/20:
💬 Explain how to make a caffeinated brewed beverage?
⌚ 0.66 seconds

▶️ Run 4/20:
💬 How to Brew the Perfect Cup of Coffee?
⌚ 0.60 seconds

▶️ Run 5/20:
💬 How to Brew the Perfect Cup of Coffee?
⌚ 0.65 seconds

▶️ Run 6/20:
💬 Tell me how to create the best steaming Java?
⌚ 0.47 seconds

▶️ Run 7/20:
💬 Tell me how to create the best steaming Java?
⌚ 0.56 seconds

▶️ Run 8/20:
💬 Explain how to make a caffeinated brewed beverage?
⌚ 0.54 seconds

▶️ Run 9/20:
💬 Explain how to make a caffeinated brewed beverage?
⌚ 0.58 seconds

▶️ Run 10/20:
💬 Tell me how to create the best steaming Java?
⌚ 0.64 seconds

▶️ Run 11/20:
💬 Explain how to make a caffeinated brewed beverage?
⌚ 0.50 seconds

▶️ Run 12/20:
💬 Explain how to make a caffeinated brewed beverage?
⌚ 0.54 seconds

▶️ Run 13/20:
💬 What are the steps to Craft the Ideal Espresso?
⌚ 0.55 seconds

▶️ Run 14/20:
💬 How to Brew the Perfect Cup of Coffee?
⌚ 0.53 seconds

▶️ Run 15/20:
💬 Tell me how to create the best steaming Java?
⌚ 0.62 seconds

▶️ Run 16/20:
💬 Explain how to make a caffeinated brewed beverage?
⌚ 0.56 seconds

▶️ Run 17/20:
💬 How to Brew the Perfect Cup of Coffee?
⌚ 0.56 seconds

▶️ Run 18/20:
💬 Tell me how to create the best steaming Java?
⌚ 0.56 seconds

▶️ Run 19/20:
💬 What are the steps to Craft the Ideal Espresso?
⌚ 0.52 seconds

▶️ Run 20/20:
💬 How to Brew the Perfect Cup of Coffee?
⌚ 0.55 seconds
```

![[Pasted image 20260604164739.png]]

The result is very clear: the first request took about **6 seconds**, while subsequent runs stayed around **0.5 seconds**. Great, right?

As we discussed in the latency analysis above, the bottleneck is usually the **decode/generation** phase. The model generates output token-by-token, and each token depends on the previous one. With longer outputs or higher load, this phase can take hundreds of milliseconds to several seconds.

By contrast, **embedding + Redis similarity lookup** is typically much cheaper:

- Embedding: one forward pass to produce a fixed-size vector
- Redis: in-memory index search and fetch

On a cache hit, you pay the smaller embedding + Redis cost and skip the expensive decode step. That is why latency drops so dramatically.

## Summary

In this article, we explored semantic caching at the Agent layer—distinct from KV caching inside the model—and implemented it with Azure AI Gateway, external Azure Managed Redis, and Microsoft Foundry-hosted models.

The demo showed a practical outcome: semantically similar prompts can move from ~6s to ~0.5s after warm-up. If you are building Agent platforms where users ask the “same question” in different wording, this pattern is worth trying.

I will share more Azure AI Gateway scenarios—and a deeper dive into Redis semantic search—in upcoming articles.

---

I am Chris Bao, a Microsoft Certified Trainer focused on the Azure AI platform, with hands-on experience in Azure AI services and agent development.  
I provide training and consulting services for both enterprises and individuals. For collaboration, please contact: baoqger@gmail.com
