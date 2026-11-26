---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - RAG
title: Breaking Through RAG Bottlenecks_ Azure AI Search Takes You to Advanced RAG
---
### Background

In my previous article, I shared how to build an enterprise-level RAG system using Azure Blob Storage and Azure AI Search. In that article, we only used the most basic retrieval capabilities of Azure AI Search. In this article, I'll take you deeper into Azure AI Search's advanced features, with the goal of upgrading our RAG system to an Advanced RAG system.

### Naive RAG vs Advanced RAG

![[Pasted image 20260328095406.png|451]]

As we learned in the previous article, the standard approach is to vectorize both the knowledge base and user questions using embedding models, create and store indexes, retrieve relevant document fragments through similarity search, and then have the large model generate answers. This is the most basic RAG system, also known as Naive RAG.

Compared to Naive RAG, Advanced RAG introduces corresponding improvement techniques at various stages of the pipeline:

- **Pre-retrieval**
  - Improve retrieval success probability by rewriting and expanding queries
- **Post-retrieval**
  - Use parallel keyword and semantic hybrid search, and apply reranking and fusion to retrieved documents

Let's examine how Azure AI Search provides these advanced capabilities, making it easier to construct an Advanced RAG system.

### Demo Index on Azure AI Search

To demonstrate the various advanced retrieval techniques that follow, we first need to create an index on Azure AI Search. Here I've pre-created an index containing over 400 products, where each product corresponds to a document in the index. The key fields are as follows:

![[Pasted image 20260328153504.png]]

![[Pasted image 20260328154515.png]]

As you can see, fields like `name`, `description`, and `price` support search, plus there's a field called `embedding` that supports vector search: it's the vectorized result of combining the three most critical fields' content: `name`, `description`, and `categories`. Here I used the `text-embedding-3-large` embedding model.

For how to create an Index on Azure AI Search using SDK, you can refer to my previous article!

### Keyword Search vs Vector Search

In the GenAI era, many people assume that Vector Search has comprehensive advantages over Keyword Search in every aspect. Actually, that's not the case. Each has its own strengths. To illustrate this point, let's look at the following set of demos.

First, let's establish a connection to Azure AI Search:

```python
import os
from azure.identity import AzureDeveloperCliCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv
from render_table import render_product_results
from azure.core.credentials import AzureKeyCredential

load_dotenv()

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")

azure_credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)

search_client = SearchClient(
    endpoint=AZURE_SEARCH_ENDPOINT,
    index_name=AZURE_SEARCH_INDEX_NAME,
    credential=azure_credential
)
```

Then we send a search request to the Index with the query `25 foot hose`. This is standard keyword search:

```python
search_query = "25 foot hose"

results = search_client.search(search_text=search_query, top=5)

render_product_results(results)
```

The search results are as follows, and they're extremely accurate! This demonstrates Keyword Search's strength—precise matching!

![[Pasted image 20260328154833.png]]

Next, let's look at another keyword search example:

```python
search_query = "water plants efficiently without waste"

results = search_client.search(search_text=search_query, top=5)

render_product_results(results)
```

When we change the query to `water plants efficiently without waste`, let's check the returned results:

![[Pasted image 20260328155102.png]]

Here, all 5 results returned by keyword search aren't quite right. In this case, we'd prefer to search based on the semantic meaning of this query, so vector search is more appropriate. Let's see the comparison:

First, in addition to the Azure AI Search client, we also need to establish an Azure OpenAI client, because vector search requires using the embedding model on Azure OpenAI!

```python
import os
from azure.identity import AzureDeveloperCliCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv
from openai import AzureOpenAI
from render_table import render_product_results
from azure.core.credentials import AzureKeyCredential

load_dotenv()

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")

# Load Azure OpenAI environment variables
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

azure_credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)

openai_client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version="2024-10-21"
)

def get_embedding_vector(query: str) -> list[float]:
    response = openai_client.embeddings.create(
        model=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME"],
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

For the same query (`water plants efficiently without waste`), this time let's use vector search. Here's the specific usage:

```python
search_query = "water plants efficiently without waste"
search_vector = get_embedding_vector(search_query)

results = search_client.search(
    None, top=5, vector_queries=[VectorizedQuery(vector=search_vector, k_nearest_neighbors=50, fields="embedding")]
)

render_product_results(results)
```

![[Pasted image 20260328155548.png]]

This time the results better match the search intent (the first returned result is a smart planter with built-in water reservoir)!

But as I mentioned at the beginning of this section, this doesn't mean we can choose vector search without analysis. For example, consider this situation:

```python
search_query = "100 foot hose that wont break"
search_vector = get_embedding_vector(search_query)

results = search_client.search(
    None, top=5, vector_queries=[VectorizedQuery(vector=search_vector, k_nearest_neighbors=50, fields="embedding")]
)

render_product_results(results)
```

Our search query is `100 foot hose that wont break`, but you can see that the data item containing the keyword `100-foot` only ranks third.

![[Pasted image 20260328155930.png]]

So we can say that you need to analyze the specific use case when choosing between Keyword Search and Vector Search, selecting the most appropriate one, just like the comparison in the following diagram:

![[Pasted image 20260328160257.png|436]]

By comparison, Keyword Search is more suitable for the following scenarios:
- **Scenarios requiring precise matching**: such as specific terms, phrases, or names. Additionally, vectors lack semantic awareness of numerical values, so 100, 50, and 20 are treated as ordinary numbers without semantic differentiation
- **Scenarios requiring high precision**: legal documents or technical manuals
- **Scenarios using structured data storage**
- **Scenarios where performance is a concern**

To understand these two search modes more deeply, let's try studying their underlying algorithms!

### Underlying Algorithm Research

#### BM25

![[Pasted image 20260328161539.png]]

Azure AI Search employs the `BM25` algorithm, which is widely used in various full-text search applications. It has the following characteristics:

1. **Inverse Document Frequency (IDF)** — Inverse Document Frequency

Measures the rarity of a word across the entire document collection. The rarer the word, the stronger its discriminability/importance, and the larger the IDF value. Simply put: rarer words can more precisely locate relevant documents.

2. **Term Frequency Saturation** — TF Saturation

Addresses the linear growth defect of traditional "Term Frequency (TF)". It means that when a word appears in a document more than a certain threshold, its contribution to document relevance gradually slows down and tends toward saturation, no longer increasing infinitely with the number of occurrences. Traditional TF believes "the more times a word appears, the more relevant the document," but in reality, excessive word occurrences might be keyword stuffing and meaningless.

3. **Document Length Normalization** — Document Length Normalization

Eliminates the interference of document length differences on term frequency, applying "fairness correction" to term frequencies in long and short documents, avoiding the problem that "long documents naturally can accommodate more words and thus get higher relevance scores."

#### HNSW

For vector search, Azure AI Search uses the HNSW (Hierarchical Navigable Small World) algorithm. Currently, mainstream vector databases or vector storage services basically adopt this algorithm.

The full name of HNSW is Hierarchical Navigable Small World. To understand it, we first need to understand the NSW (Navigable Small World) algorithm.

**NSW (Navigable Small World)**

Imagine you have a book divided into 1,000 document fragments, each fragment is vectorized and stored in a vector database. NSW constructs a graph data structure where each node is a fragment, and edges connect semantically similar nodes. In this example, all data is represented as a graph containing 1,000 nodes, and subsequent searches operate based on this graph.

How does NSW process a search query?

1- **Vectorize the query**: Use the same embedding model as the documents to create a compatible embedding vector
2- **Select a search starting node**: Randomly select a node from the graph to start
3- **Search**: Start from the starting node, check all connected neighbor nodes, and move to the node most similar to the query
4- **Iterate repeatedly**: Continue moving to closer neighbors until no neighbor node is more similar than the current node

Obviously, this is a greedy algorithm.

![[Pasted image 20260211181535.png]]

For example, in the above example, node 1 is the starting point, the query is the orange node, and the entire search process is:
1 -> 2 -> 3 -> 8 -> 10 -> 9

Although NSW's greedy algorithm laid the foundation, it has its own limitations:
- **Flat structure**: Single-layer structure, might get stuck in local optima
- **Recall rate**: Might miss true nearest neighbors
- **Scalability**: Performance decreases as data grows

To solve these problems, we need HNSW. But before that, we need to look at another concept: Skip List

**Skip List**

Skip List is an optimization of Linked List. Although linked lists perform well in implementing LIFO and FIFO data structures (such as stacks and queues), a major disadvantage is that the time complexity for random access is linear. Skip List aims to solve this problem by introducing additional layers, reducing the time complexity of random access to `O(log n)`, like this:

![[Pasted image 20260211205318.png]]

Schematic of skip list structure. Higher levels contain fewer elements, lower levels contain more elements, and the bottom layer is the original linked list containing all elements.

When searching, suppose our search target is element i. Start from the highest level, and once we find an element greater than `i`, we backtrack to the previous node and move to the next level. This process continues until we find the element we're looking for.

This approach can significantly improve performance.

**HNSW = NSW + Skip List**

HNSW builds on NSW, borrowing from Skip List's idea to stretch NSW across multiple levels. The difference is that Skip List is linear, while each layer of HNSW is a graph!

During search, HNSW also starts from the topmost sparse layer. At this layer, you can move through the graph, effectively avoiding local suboptimal nodes that might trap the search in NSW. At each layer, the algorithm progressively optimizes the path, using connections from the previous layer as entry points.

As a metaphor, you can think of it as finding information in a large book: you first check the table of contents (top layer) to find the chapter you need. Once you find the correct chapter, you flip to the relevant section (middle layer). Finally, you focus on the exact page containing the answer (bottom layer).

This multi-layer navigation approach allows HNSW to avoid getting stuck in local optima and enables "zooming" from a global perspective to a local perspective—reliably finding true nearest neighbors. Therefore, HNSW can provide higher recall and accuracy in complex or high-dimensional search spaces!

I spent a lot of time using NotebookLM to create an infographic to express the meaning of HNSW. Keep it handy!

![[Pasted image 20260211092426.png|480]]

### Hybrid Search + RRF

From the analysis above, we can see that the most effective approach is Hybrid Search, which integrates Keyword Search and Vector Search.

For results obtained from both searches, we need to merge them together to form a new ranking. Azure AI Search uses the RRF (Reciprocal Rank Fusion) algorithm. Its core idea is simple yet powerful: the higher a document ranks across different lists, the higher its final score. Its advantage is that it doesn't need to normalize scores from different queries—it calculates directly based on "ranking."

![[RRF-2.png]]

In Azure AI Search, you can achieve Hybrid Search with RRF fusion simply by specifying both `search_query` and `vector_queries` fields:

```python
search_query = "100 foot hose that won't break"
search_vector = get_embedding_vector(search_query)

results = search_client.search(
    search_query,
    top=5,
    vector_queries=[VectorizedQuery(vector=search_vector, k_nearest_neighbors=50, fields="embedding")],
)

render_product_results(results)
```

Let's check the results:

![[Pasted image 20260328212602.png]]

You can see that the `Expandable Hose 100-foot` item's ranking has indeed climbed to second place (it was third in pure vector search). But there's still room for improvement. Let's see what other methods are available.

### Hybrid Search + Reranking

In RAG systems, after the retrieval step completes, relevant document fragments can be read from the vector database based on similarity. The relevance ranking of these document fragments has a significant impact on the final generation results. How do we solve the problem of inaccurate retrieval document ranking? Like the situation we saw above. The answer is: Rerank!

As the name suggests, Rerank performs another semantic analysis on the retrieved results after retrieval, then reorders the documents.

The principle behind Rerank is that it uses a different transformer model architecture: `Cross-Encoder`. The model architecture for the normal retrieval stage is called `Bi-Encoder`.

![[Pasted image 20260328221310.png]]

Bi-Encoder independently processes query and document separately, converting them into vectors of the same dimension. Vectorization of document materials happens offline; vectorization of the query happens during the retrieval process. This approach makes retrieval performance excellent and responses fast.

In comparison, Cross-Encoder processes query and document simultaneously, treating each other as context and passing them together to the transformer. Friends familiar with the attention mechanism will immediately understand the trick here. Because query and document are concatenated together as a whole to calculate attention weights, the accuracy is naturally higher! Of course, doing this has high computational costs, so it's not suitable for large-scale online retrieval processing!

In Azure AI Search, you just need to set the `query_type` field to `semantic` to enable the rerank feature!

```python
search_query = "100 foot hose that won't break"
search_vector = get_embedding_vector(search_query)

results = search_client.search(
    search_query,
    top=5,
    vector_queries=[VectorizedQuery(vector=search_vector, k_nearest_neighbors=50, fields="embedding")],
    query_type="semantic",
    semantic_configuration_name="products-semantic-config",
)

render_product_results(results, show_reranker=True)
```


![[Pasted image 20260328221528.png]]

Now we can see that the final ranking is very reasonable!
