---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - RAG
title: Step-by-Step Guide to Building Enterprise-Level RAG Systems with Azure From Blob to AI Search
---

### Background

With the combined advantages of cost and performance, Azure Blob Storage is widely used in enterprise-level cloud systems.

Today, let's break down how to leverage Azure AI Search and Azure Blob Storage services to construct an enterprise-level RAG system.

If your enterprise or organization already has a large amount of data stored in Azure Blob and wants to leverage this data for RAG system development, then this article will definitely provide value to you!

### Azure AI Search 101

First, let's briefly understand today's protagonist, the Azure AI Search service:

Azure AI Search is a fully managed cloud service designed to connect your data to AI. Simply put, it enables agents and LLMs to leverage multi-source data to provide reliable, evidence-based answers.

This service is primarily used for two scenarios: classic search (traditional full-text search) and modern RAG retrieval-augmented generation. Whether you want to add search functionality to websites, apps, agents, or chatbots, Azure AI Search can handle it.

The core components of Azure AI Search include the following three:

**Data Source - Data Source**
- Unstructured files (such as Azure Blob), SQL tables, Cosmos DB documents

**Indexer - Indexer**
- The engine that drives indexing, supporting automatic, scheduled, or on-demand execution

**Index - Index**
- A collection of JSON documents containing rich data

Of course, these are the most basic functions. In addition, it includes these powerful capabilities:
- Supports full-text, vector, hybrid, and multimodal queries
- AI enrichment during indexing process, including language detection, key phrase extraction, sentiment analysis, entity recognition, OCR, custom skills
- Azure-level scalability, security, monitoring, and compliance
- Deep integration with Azure OpenAI, Microsoft Foundry, and various data platforms

In future articles, I'll introduce the implementation and application of these advanced features! Below, let's see how to build an enterprise-level RAG system based on Azure AI Search.

### Core Components of Enterprise-Level RAG System

The core services of this RAG system include the following three:

- Azure Blob Storage: As a data source, storing enterprise's original production data
- Azure AI Search: As vector storage layer and retrieval layer, providing high-performance vectorized search service
- Embedding Model on Microsoft Foundry: Providing embedding models and chat models for content generation

#### Azure Blob Data Source

![[Pasted image 20260324103310.png]]


In this example, I created an Azure Blob Container named `rag-time-1`, which contains multiple PDF files. For specific methods to create Azure Blob, you can refer to my previous articles or check Azure's documentation!

#### Azure AI Search Vectorization

There are two ways to construct vectorized data on Azure AI Search: you can write code through SDK or utilize the integrated vectorization pipeline in the UI interface. In today's article, we'll use the second approach, and in subsequent articles, we'll analyze SDK applications more deeply.

First, start "Import Data"

![[Pasted image 20260324104238.png]]

Then, select "Azure Blob Storage" as the data source

![[Pasted image 20260324105000.png]]

Next, define my scenario "RAG"

![[Pasted image 20260324105127.png]]

Below that, "Connect to your data", find the Azure Blob Container `rag-time-1` mentioned above

![[Pasted image 20260324105558.png]]

Then, configure the Embedding model on Microsoft Foundry to implement vectorization. Here, I deployed the `text-embedding-3-large` embedding model on my Foundry

![[Pasted image 20260324105709.png]]

Finally, you can set the schedule for this data indexing work, supporting Daily, Hourly, custom, etc.

![[Pasted image 20260324105857.png]]

A few minutes later, we can see the created resources: index, indexer, data source, as shown below.

![[Pasted image 20260324110443.png]]


![[Pasted image 20260324110531.png]]


![[Pasted image 20260324110556.png]]

#### RAG Based on Microsoft Foundry

Now that data vectorization and indexing are complete, let's use Azure AI Search's SDK to complete the RAG Q&A logic:

Create clients for Azure AI Search and Azure Open AI:
```
import os
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
from azure.search.documents import SearchClient
import dotenv
from azure.search.documents.models import VectorizedQuery, VectorizableTextQuery

dotenv.load_dotenv()

# Load Azure OpenAI environment variables
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME = os.getenv("AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME")

# Load Azure Search environment variables
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")

# 🔹 Initialize Azure OpenAI Client (API Key or Managed Identity)
if AZURE_OPENAI_API_KEY:
    openai_client = AzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version="2024-10-21"
    )
else:
    azure_credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
    openai_client = AzureOpenAI(
        azure_ad_token_provider=token_provider,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version="2024-10-21"
    )

# 🔹 Initialize Azure AI Search Client (API Key or Managed Identity)
if AZURE_SEARCH_ADMIN_KEY:
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)
    )
else:
    azure_credential = DefaultAzureCredential()
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX_NAME,
        credential=azure_credential
    )

def get_embedding(text):
    return openai_client.embeddings.create(
        model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME"),
        input=text
    ).data[0].embedding
```


Prepare a question:

```
user_question = "What is included in my Northwind Health Plus plan that is not in standard?"
user_question_vector = get_embedding(user_question)
print(user_question_vector)
```

Search based on vectorized data from Azure AI Search:

```
search_results = search_client.search(
    None,
    top=3,
    vector_queries=[
        VectorizableTextQuery(
            text=user_question, k_nearest_neighbors=3, fields="text_vector"
        )
    ],
)
```

Integrate search results with user questions and send to the large model:
```
SYSTEM_MESSAGE = f"""
You are an AI Assistant.
Be brief in your answers. Answer ONLY with the facts listed in the retrieved text.

Context:
{context}
"""

USER_MESSAGE = user_question

response = openai_client.chat.completions.create(
    model=os.getenv("AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME"),
    temperature=0.7,
    messages=[
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": USER_MESSAGE},
    ],
)

answer = response.choices[0].message.content
print(answer)
```


The code is as above. Please try it yourself to see if the results you get are based on the data source we just connected. I'll leave this task to you!

