---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - RAG
title: Evaluating RAG Systems with LLM-as-a-judge - The final piece of Agentic RAG puzzle
---
#azureai #azureaisearch #rag 
### Background

In my previous articles, based on Azure AI Search services, we discussed advanced RAG techniques and how to build multimodal RAG systems. While these concepts and techniques are great, from an engineering perspective, we've overlooked an important aspect: evaluating RAG systems. The importance of RAG evaluation systems is reflected in two aspects:

- Only with an automated quantitative evaluation system can we measure and choose among various RAG optimization methods!
- Only with a RAG evaluation system can we achieve the ultimate Agentic RAG system!

If you also have doubts about the above two aspects, this article will definitely provide value to you!

### Why Do We Need RAG Evaluation

![[Pasted image 20260402060443.png]]

Actually, this problem is quite easy to understand. We develop a RAG system, make many optimizations to it, and we need to know whether the results are good or not. However, we can't always rely on manual checking - this is both time-consuming and inaccurate, so we need an effective RAG evaluation system.

If we compare this with traditional software engineering, it's similar to various tests performed on code and software, such as unit tests and integration tests.

Moreover, we should put this evaluation system into the CI pipeline, just like before, to achieve automation. Every time you modify the RAG system's strategy, you can run the evaluation system!

### How to Do RAG Evaluation

**RAG evaluation systems can be divided into two main categories:**

- Internal evaluation: Focuses on the effectiveness of retrieval and generation modules individually, and how they work together.
- External evaluation: Focuses on the overall performance of the RAG system: security, accuracy, performance, etc.

In today's article, we'll focus on internal evaluation. Internal evaluation examines the effectiveness of retrieval and generation modules separately, each focusing on different metrics:

- Retrieval
  - Relevance: Are the retrieved document fragments related to the question?
  - Coverage: Are all document fragments in the database that are actually related to the question retrieved?
  - Correctness: Among all retrieved document fragments, what proportion is actually relevant (the so-called signal-to-noise ratio), and are the relevant fragments ranked in the front?
- Generation
  - Relevance: Is the answer related to the question? Are they on the same channel? Is there any "talking at cross-purposes"?
  - Factuality: Is the answer "loyal" to the retrieved documents? Or is it "made up"?
  - Correctness: Is the answer accurate?

Evaluation methods can be broadly divided into two categories:
- Traditional evaluation metrics: Includes established algorithms and metrics widely used in natural language processing (NLP) to evaluate the quality of generated text, such as ROUGE (Recall-Oriented Understudy for Gisting Evaluation), BLEU (Bilingual Evaluation Understudy), etc.!
- LLM-as-a-judge: As the name suggests, using "magic to defeat magic." Today's article is primarily based on this method.

Let's now look at how to develop an evaluation system for a RAG system built on Azure AI Search.

### RAG Evaluation Based on Azure

#### RAG Index Introduction

In my previous articles, I've already introduced how to develop RAG systems based on Azure AI Search, so I won't repeat that here. If you're interested, you can check out my previous articles.

Simply put, we put a company's employee handbook PDF files in Azure Blob as a data source, then create an Azure AI Search Index: `rag-evalution-chris`. You can see that the core of this index is the vectorized data in the `text_vector` field.

![[Pasted image 20260402063125.png]]

This index isn't large, it has about 50 document chunks.

![[Pasted image 20260402063317.png]]



The following code creates Azure AI Search and Azure OpenAI clients:

```python
import os
import azure.identity
import dotenv
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import OpenAI
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

dotenv.load_dotenv()

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_EVALUATION_INDEX_NAME")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_LLM_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_LLM_DEPLOYMENT_NAME")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME")

azure_credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)

openai_client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version="2024-10-21"
)

def get_embedding_vector(query: str) -> list[float]:
    response = openai_client.embeddings.create(
        model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME,
        input=[query],
    )
    embedding_vector = response.data[0].embedding
    return embedding_vector

search_client = SearchClient(
    endpoint=AZURE_SEARCH_ENDPOINT,
    index_name=AZURE_SEARCH_INDEX_NAME,
    credential=azure_credential
)
```

Now, let's do a set of experiments. We'll use Keyword Search, Vector Search, and Hybrid Search respectively to search for the same query (`What does a product manager do?`), then score the results based on the evaluation system, so we can scientifically evaluate the pros and cons of the three methods!

#### Keyword Search

```python
user_question = "What does a product manager do?"

r = search_client.search(
        search_text= user_question,
        top=5)

sources = "\n\n".join([f"{doc['chunk']}\n" for doc in r])
```

#### Vector Search

```python
user_question = "What does a product manager do?"

user_question_vector = get_embedding_vector(user_question)

r = search_client.search(
        None,
        top=5,
        vector_queries=[
            VectorizedQuery(vector=user_question_vector, k_nearest_neighbors=50, fields="text_vector")])

sources = "\n\n".join([f"{doc['chunk']}\n" for doc in r])
```

#### Hybrid Search

```python
user_question = "What does a product manager do?"

user_question_vector = get_embedding_vector(user_question)

r = search_client.search(
        user_question,
        top=5,
        vector_queries=[
            VectorizedQuery(vector=user_question_vector, k_nearest_neighbors=50, fields="text_vector")],
        query_type="semantic",
        semantic_configuration_name="rag-evaluation-chris-semantic-configuration")

sources = "\n\n".join([f"{doc['chunk']}\n" for doc in r])
```

As shown above, we've completed the retrieval work using three different methods. For specific usage, please refer to my previous articles about Azure AI Search! Then we can submit the search results (the `sources` variable above) as part of the prompt to the large model and get the answer (the `answer` variable below). Note that these two variables will be relied upon by the evaluation system later.

```python
SYSTEM_MESSAGE = """
Assistant helps company employees questions about the employee handbook. Be brief in your answers.
Answer ONLY with the facts listed in the list of sources below.
If there isn't enough information below, say you don't know. Do not generate answers that don't use the sources below.
Each source has a name followed by colon and the actual information, include the source name for each fact you use.
Use square brackets to reference the source, for example [info1.txt].
"""

USER_MESSAGE = user_question + "\nSources: " + sources

response = openai_client.chat.completions.create(
    model=AZURE_OPENAI_LLM_DEPLOYMENT_NAME,
    temperature=0.7,
    messages=[
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": USER_MESSAGE},
    ],
)

answer = response.choices[0].message.content

print(answer)
```

Next step, let's evaluate the effectiveness of the three methods!

#### RAG Evaluation Based on Azure SDK

Here we use the evaluation package from Azure SDK: `azure.ai.evaluation`, to complete this evaluation work.

There are a few notable points here. First, we adopted the LLM-as-a-judge strategy, where we use the `gpt-4.1` model, configured in the environment variable `AZURE_OPENAI_LLM_DEPLOYMENT_NAME`.

```python
import os
from azure.ai.evaluation import AzureOpenAIModelConfiguration, GroundednessEvaluator, RelevanceEvaluator

model_config: AzureOpenAIModelConfiguration = {
    "azure_endpoint": AZURE_OPENAI_ENDPOINT,
    "azure_deployment": AZURE_OPENAI_LLM_DEPLOYMENT_NAME,
    "api_key": AZURE_OPENAI_API_KEY
}

relevance_eval = RelevanceEvaluator(model_config)
groundedness_eval = GroundednessEvaluator(model_config)

relevance_score = relevance_eval(
    query=user_question,
    response=answer,
    context=sources,
)
print(relevance_score)

groundedness_score = groundedness_eval(
    response=answer,
    context=sources,
)
print(groundedness_score)
```

Additionally, the Azure SDK's evaluation module is a very comprehensive evaluation tool. RAG evaluation is just one part of it. In the future, I'll write articles specifically about other evaluation features.

![[Pasted image 20260402091437.png]]

For RAG, it provides multiple built-in evaluators. Here we use `GroundednessEvaluator` and `RelevanceEvaluator`.

- Groundedness (Factuality): This metric evaluates the consistency between AI-generated answers and source contexts, ensuring these answers are supported by the context. Even if the large language model (LLM) response is factually correct, if it cannot be verified with the provided sources, it will be considered ungrounded.
- Relevance: High relevance scores indicate the AI system's understanding of input and ability to generate coherent and contextually appropriate outputs. Conversely, low relevance scores indicate that the generated response may be off-topic, lack context, or be insufficient to satisfy the user's intent query.

Simply put, Groundedness evaluates the relationship between the generated answer and retrieval results, so from the code above, you can see it only uses the `answer` and `sources` variable values.

Relevance evaluates the relationship between the generated answer and the complete context, so in addition to the `answer` and `sources` variable values, it also considers the original input `user_question` variable value.

Running the evaluation code above for the three methods respectively, we obtained the following comparison results:

|                | Groundedness | Relevance |
| -------------- | ------------ | --------- |
| Keyword Search | 5.0          | 5.0       |
| Vector Search  | 5.0          | 4.0       |
| Hybrid Search  | 5.0          | 4.0       |

Azure SDK's built-in evaluator scores range from 1.0 to 5.0. From the results above, for this simple search task, keyword search is actually the best, quite unexpected, right? Haha!

