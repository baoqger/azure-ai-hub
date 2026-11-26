---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - RAG
title: Beyond Text-Based Search -  Building a Multimodal RAG System with Azure AI Search
---

### Background

In my previous two articles, I shared with you how to build an enterprise-level RAG system using Azure Blob Storage and Azure AI Search, as well as how to leverage Azure AI Search's advanced algorithms to upgrade our system from naive RAG to advanced RAG.

Up until now, our searches have been text-based. However, in real-world scenarios, media beyond text—such as images, tables, audio, or video—can contain valuable information. So in this article, let's explore how to build a multimodal RAG system based on Azure AI Search.

### AI Enrichment & Skillsets

Before developing a multimodal RAG system, we need to first understand two important concepts in Azure AI Search: `AI enrichment` and `skillsets`.

- **AI Enrichment**: In the Azure AI Search pipeline, AI enrichment refers to using various Foundry Tools' AI services or custom AI tools to transform originally unsearchable content into searchable content.
- **Skillsets**: The AI enrichment process is built upon skills (note: this is just a naming coincidence—the "skill" here is not the same as agent skills in the broad sense, but the concept is similar, which is the utilization of tools). Each AI processing operation on original content is encapsulated within a skill, and one or multiple skills form a skillset.

#### Foundry Tools

In the current context, Foundry Tools refers to the AI or ML services provided by Azure. These services actually existed before the GenAI revolution.

![[Pasted image 20260330135716.png]]

They include various intelligent services on Azure, ranging from document processing, speech, to images, and more. Additionally, you can notice that Azure AI Search itself is also one of them.

Later, let's take a look at which Foundry Tools are used in today's demo.

#### Skills

Within the Azure AI Search scope, skills can be divided into three categories:

- **Built-in skill**: These built-in skills are simply calls and wrappers to the Foundry Tools mentioned above.
- **Custom skill**: These custom skills allow you to write your own logic.
- **Utility skill**: These functional skills rely entirely on Azure AI Search's capabilities. If you don't quite understand what this means right now, don't worry—we'll analyze it in detail in the demo section later.

After understanding these two concepts above, let's see how to build a multimodal RAG system.

### Creating a Multimodal RAG Index

![[unnamed (3).png]]

In my previous articles, I introduced how to use Azure Blob Storage as a data source and then implement a pipeline based on Azure AI Search's integrated indexer. At that time, I covered text file scenarios. Today, we'll build upon this basic method but extend it to image files.

Now, let me break down the details of this pipeline step by step.

### Data Source

The data source is a PDF file containing various images: [Accelerating-Sustainability-with-AI-2025.pdf](https://github.com/Azure-Samples/azure-search-sample-data/blob/main/sustainable-ai-pdf/Accelerating-Sustainability-with-AI-2025.pdf)

Based on this PDF file, let's create an Azure Blob Storage container: `multimodal`

![[Pasted image 20260330142502.png]]

In addition to this container serving as the data source, for a multimodal RAG system, we also need to create another container: `multimodal-images-extracted`. This container is specifically used to store image files extracted from the original PDF documents. These extracted images can serve as grounded sources in the RAG system we'll develop later.

![[Pasted image 20260330142826.png]]

#### Multimodal Search

Let's start with `import data`

![[Pasted image 20260330144010.png]]

Select `Azure Blob Storage` as the data source

![[Pasted image 20260330144221.png]]

Unlike last time, this time we'll use `Multimodal RAG`

![[Pasted image 20260330144236.png]]

Next, let's enter the specific pipeline setup process. First, select the blob container: `multimodal` as our data source.
Additionally, we need to choose to use managed identity for authentication. If you're unclear about this part, you can refer to my previous articles.

![[Pasted image 20260330144329.png]]

Next, we need to define the method for extracting images from the data source. There are two options available here. We can choose `Default`, which relies entirely on Azure AI Search's capabilities and doesn't require other Foundry Tools.

Based on the introduction about skills above, you can probably deduce that this method actually corresponds to a `utility skill`: `document extraction skill`. We can verify this later!

![[Pasted image 20260330144444.png]]

The next step is the most complex part of this pipeline: defining embeddings. Here, we adopted a two-step approach:
Step 1: Image verbalization (image semantic representation); Step 2: Text vectorization (text vectorization).

Image verbalization—image semantic representation—involves using a large language model to summarize the content of an image, resulting in descriptive text. Here, we used the `gpt-4.1` model deployed on Foundry!

![[Pasted image 20260330144721.png]]

The following text vectorization step involves vectorizing the original text from the data source and the descriptive text generated from the images mentioned above. Here, we adopted the `text-embedding-3-large` model!

With these two steps, we can search through all information in the data source!

![[Pasted image 20260330144831.png]]

Next, we need to specify the other container for storing images parsed from the data source. Remember we created two Azure Blob containers? This is where we use the other one: `multimodal-images-extracted`!

![[Pasted image 20260330144934.png]]

In the final settings, we need to pay attention to the field mapping for search documents.

![[Pasted image 20260330145056.png]]

These field mappings and configurations are actually based on the `shaper` `utility skill`!

![[Pasted image 20260330145128.png]]

### Skillsets Review

After the Index is created, before conducting the actual search demo, let's take a look at which skills this pipeline uses. We'll unveil the mystery of skills through this practical case!

![[Pasted image 20260330151940.png]]

You can see that the process above generated a skillset containing 6 skills. Specifically, as follows:

```
{
  "skills": [
    {
      "@odata.type": "#Microsoft.Skills.Util.DocumentExtractionSkill",
      "name": "#1",
      "context": "/document",
      "parsingMode": "default",
      "dataToExtract": "contentAndMetadata",
      "inputs": [{ "name": "file_data", "source": "/document/file_data" }],
      "outputs": [
        { "name": "content", "targetName": "extracted_content" },
        { "name": "normalized_images", "targetName": "normalized_images" }
      ],
      "configuration": {
        "imageAction": "generateNormalizedImages",
        "normalizedImageMaxWidth": 2000,
        "normalizedImageMaxHeight": 2000
      }
    },
    {
      "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
      "name": "#2",
      "context": "/document",
      "defaultLanguageCode": "en",
      "textSplitMode": "pages",
      "maximumPageLength": 2000,
      "pageOverlapLength": 200,
      "maximumPagesToTake": 0,
      "unit": "characters",
      "inputs": [{ "name": "text", "source": "/document/extracted_content" }],
      "outputs": [{ "name": "textItems", "targetName": "pages" }]
    },
    {
      "@odata.type": "#Microsoft.Skills.Custom.ChatCompletionSkill",
      "name": "#3",
      "context": "/document/normalized_images/*",
      "uri": "<OPENAI_ENDPOINT>/deployments/<MODEL_NAME>/chat/completions?api-version=<API_VERSION>",
      "httpMethod": "POST",
      "timeout": "PT30S",
      "batchSize": 1,
      "inputs": [
        { "name": "systemMessage", "source": "<IMAGE_VERBALIZATION_PROMPT>" },
        { "name": "userMessage", "source": "'Please describe this image.'" },
        { "name": "image", "source": "/document/normalized_images/*/data" }
      ],
      "outputs": [{ "name": "response", "targetName": "verbalizedImage" }]
    },
    {
      "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
      "name": "#4",
      "context": "/document/pages/*",
      "resourceUri": "<OPENAI_ENDPOINT>",
      "deploymentId": "text-embedding-3-large",
      "dimensions": 3072,
      "modelName": "text-embedding-3-large",
      "inputs": [{ "name": "text", "source": "/document/pages/*" }],
      "outputs": [{ "name": "embedding", "targetName": "text_vector" }]
    },
    {
      "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
      "name": "#5",
      "context": "/document/normalized_images/*",
      "resourceUri": "<OPENAI_ENDPOINT>",
      "deploymentId": "text-embedding-3-large",
      "dimensions": 3072,
      "modelName": "text-embedding-3-large",
      "inputs": [{ "name": "text", "source": "/document/normalized_images/*/verbalizedImage" }],
      "outputs": [{ "name": "embedding", "targetName": "verbalizedImage_vector" }]
    },
    {
      "@odata.type": "#Microsoft.Skills.Util.ShaperSkill",
      "name": "#6",
      "context": "/document/normalized_images/*",
      "inputs": [
        { "name": "normalized_images", "source": "/document/normalized_images/*" },
        { "name": "imagePath", "source": "'<CONTAINER_NAME>/'+$(/document/normalized_images/*/imagePath)" },
        {
          "name": "locationMetadata",
          "sourceContext": "/document/normalized_images/*",
          "inputs": [
            { "name": "pageNumber", "source": "/document/normalized_images/*/pageNumber" },
            { "name": "boundingPolygons", "source": "/document/normalized_images/*/boundingPolygon" }
          ]
        }
      ],
      "outputs": [{ "name": "output", "targetName": "new_normalized_images" }]
    }
  ]
}
```

The main functions of these skills are as follows:
- `Microsoft.Skills.Util.DocumentExtractionSkill`: Extract images
- `Microsoft.Skills.Text.SplitSkill`: Document chunking
- `Microsoft.Skills.Custom.ChatCompletionSkill`: Leverage large language model's chat completion capability to implement image verbalization (image semantic representation)
- `Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill`: Leverage embedding model's capability to implement text vectorization
- `Microsoft.Skills.Util.ShaperSkill`: Document field mapping

### Extracted Images Review

Remember the other Azure Blob container we created? After completing the indexing work above, it contains more than 20 images.

![[Pasted image 20260330153626.png]]

As you can see, the extracted images are very clear!

![[Pasted image 20260330153814.png|464]]

### Demo Time

Let's search for `energy`, and you can see that the search results include two image results.

![[Pasted image 20260330154806.png]]

The specific return results are as follows:

```
    {
      "@search.score": 0.5991279,
      "content_id": "563eb8d21242_aHR0cHM6Ly9jaHJpc2FpbGFiLmJsb2IuY29yZS53aW5kb3dzLm5ldC9tdWx0aW1vZGFsL0FjY2VsZXJhdGluZy1TdXN0YWluYWJpbGl0eS13aXRoLUFJLTIwMjUucGRm0_normalized_images_21",
      "text_document_id": null,
      "document_title": "Accelerating-Sustainability-with-AI-2025.pdf",
      "image_document_id": "aHR0cHM6Ly9jaHJpc2FpbGFiLmJsb2IuY29yZS53aW5kb3dzLm5ldC9tdWx0aW1vZGFsL0FjY2VsZXJhdGluZy1TdXN0YWluYWJpbGl0eS13aXRoLUFJLTIwMjUucGRm0",
      "content_text": "The image shows an array of solar panels in the foreground with a wind turbine in the background. The scene represents the use of renewable energy sources, specifically solar and wind power. The sky is visibly clear with some clouds, suggesting a setting suitable for both solar and wind energy generation.",
      "content_path": "multimodal-images-extracted/aHR0cHM6Ly9jaHJpc2FpbGFiLmJsb2IuY29yZS53aW5kb3dzLm5ldC9tdWx0aW1vZGFsL0FjY2VsZXJhdGluZy1TdXN0YWluYWJpbGl0eS13aXRoLUFJLTIwMjUucGRm0/normalized_images_21.jpg"
    },
    {
      "@search.score": 0.5969818,
      "content_id": "563eb8d21242_aHR0cHM6Ly9jaHJpc2FpbGFiLmJsb2IuY29yZS53aW5kb3dzLm5ldC9tdWx0aW1vZGFsL0FjY2VsZXJhdGluZy1TdXN0YWluYWJpbGl0eS13aXRoLUFJLTIwMjUucGRm0_normalized_images_1",
      "text_document_id": null,
      "document_title": "Accelerating-Sustainability-with-AI-2025.pdf",
      "image_document_id": "aHR0cHM6Ly9jaHJpc2FpbGFiLmJsb2IuY29yZS53aW5kb3dzLm5ldC9tdWx0aW1vZGFsL0FjY2VsZXJhdGluZy1TdXN0YWluYWJpbGl0eS13aXRoLUFJLTIwMjUucGRm0",
      "content_text": "The image shows wind turbines and solar panels, illustrating the use of renewable energy sources. The wind turbines are in the background, producing electricity from wind, while the solar panels in the foreground capture solar energy. This combination represents a hybrid approach to sustainable power generation.",
      "content_path": "multimodal-images-extracted/aHR0cHM6Ly9jaHJpc2FpbGFiLmJsb2IuY29yZS53aW5kb3dzLm5ldC9tdWx0aW1vZGFsL0FjY2VsZXJhdGluZy1TdXN0YWluYWJpbGl0eS13aXRoLUFJLTIwMjUucGRm0/normalized_images_1.jpg"
    },
```

You can see these are the two images: `normalized_images_21.jpg`: solar panels and `normalized_images_1.jpg`: wind turbines.

Completely accurate!
