---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - Document Intelligence
title: Azure Content Understanding Hands-On - Understand Documents, Images, Audio, and Video in One Go
---
## Background

In my previous articles, I shared how to build RAG systems, and during that journey we discussed many retrieval techniques. But if we look at the problem from a higher level, there is still one important piece missing: `data acquisition`.

In the real world, your data is very likely buried in all kinds of legacy files. Being able to uncover and extract that data is extremely important.

Besides the text and images we usually focus on, audio and video files are also rich data sources. Extracting useful information from these files is a very challenging task.

In this article, let's take a look at how we can use the AI capabilities of Azure Content Understanding to extract rich and structured data.

## Challenges in Document Intelligence

First, we have to admit that compared with natural language processing, semantic understanding of documents is much more complex. The reason is that the meaning inside a document is not only in the text itself, but also in the document layout (`layout`), document structure (`structure`), tables (`table`), and more.

On Azure, there has long been a service called `Azure Document Intelligence`, and this service mainly relies on OCR technology and deep learning algorithms.

The problem with OCR is that it tends to lose semi-structured information in documents and tables. We call them semi-structured because the information itself has structure, but that valuable structure is expressed through document layout (`layout`) or document appearance (`appearance`).

The main purpose of traditional OCR is to convert pixels into text. It cannot reliably tell you, "this piece of text is the value of the invoice number field" or "that block belongs to a certain row in a table." That kind of grouping comes from semantic understanding based on layout. For humans, this is easy. OCR cannot really do it. It may read "Invoice" and "12345", but it still cannot recognize them as one logical field.

To solve this problem, Azure Document Intelligence provides many prebuilt layout models for different business and everyday scenarios, such as invoices, tax forms, medical documents, financial forms, and so on. These are standard templates used in certain industries, so by using the corresponding prebuilt layout models, you can perform content extraction.

But this approach still has many limitations. For example, if you have a custom non-standard table, then the prebuilt model is no longer enough, right? In that case, you can use Azure Document Intelligence to train your own model. Of course, this requires manual labeling work, and those labels become the training dataset for your model. It looks like this:

![[Pasted image 20260408173817.png|697]]

If you need to process a large number of documents with inconsistent formats, the limitations of Azure Document Intelligence become very obvious. From this perspective, its scalability is quite limited.

## Document Intelligence Based on Multimodal LLMs

Theoretically speaking, there are two main approaches to document intelligence (`Document Intelligence`):

- A modular pipeline approach based on OCR
- An end-to-end approach based on multimodal LLMs

The `Azure Document Intelligence` service we discussed above belongs to the first approach. By late 2025, Azure officially introduced `Azure Content Understanding`, which represents a new path enabled by the innovation of GenAI. This new solution fully leverages the power of multimodal LLMs, overcomes the bottlenecks of the older approach, and is especially suitable for scenarios involving `non-standard documents` and `complex document layouts`.

![[Pasted image 20260409101855.png]]

The theory and applications of multimodal LLMs will be one of my key focus areas in the next stage of my learning journey. I will not expand on that part too much in this article, but I will definitely share more in future posts, so stay tuned.

Next, let's break down the architecture of `Azure Content Understanding`.

## Azure Content Understanding Architecture

![[Pasted image 20260409102836.png]]

As we can see, the main modules in this architecture include:

- Input sources: it supports not only documents, but also images, audio, and video
- Analyzer: this is the core of the entire architecture, and depending on the scenario and document type, it can be divided into the following modules:
	- Content extraction
	- Segmentation
	- Field extraction
	- Postprocessing
- Foundation models: powered by the models available in Foundry
- Structured output: the model can organize its understanding of the content into structured formats such as markdown and JSON. This is very valuable for downstream processing. For example, in a RAG system, structured information usually gives the LLM a more accurate understanding than unstructured information for the same content

It is clear that the analyzer is the most important component here. Azure Content Understanding provides several built-in analyzers, and they are quite powerful, as we will see in the following demo. Of course, you can also train your own analyzers for specialized scenarios. I will share more about that in future articles.

Now, let's take a look at what it can do.

## Azure Content Understanding Demo

First, because it relies on the large model capabilities provided through Foundry, we need to create a Foundry resource: `content-understanding-chris`

![[Pasted image 20260409105807.png]]

Azure Content Understanding also provides a dedicated Studio application so that users can manage and use these resources. The next step is to go to Studio and create a connection to the Foundry resource:

![[Pasted image 20260409110916.png]]

This will automatically deploy several required large models in the Foundry project:

![[Pasted image 20260409111208.png]]
Next, let's use the Azure SDK `azure.ai.contentunderstanding` to experience the capabilities of Content Understanding.

#### Document Intelligence

As you can see, we used the built-in standard analyzer `prebuilt-documentSearch` to read an invoice into a markdown file.
```python
import os

from dotenv import load_dotenv
from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.ai.contentunderstanding.models import (
    AnalysisResult,
    DocumentContent,
)
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from IPython.display import display, Markdown, Latex

load_dotenv()

endpoint = os.environ["AZURE_AI_ENDPOINT"]
key = os.getenv("AZURE_AI_API_KEY")
credential = AzureKeyCredential(key) if key else DefaultAzureCredential()

client = ContentUnderstandingClient(endpoint=endpoint, credential=credential)

file_path = "sample_files/sample_invoice.pdf"

with open(file_path, "rb") as f:
    file_bytes = f.read()

print(f"Analyzing {file_path} with prebuilt-documentSearch...")

poller = client.begin_analyze_binary(
    analyzer_id="prebuilt-documentSearch",
    binary_input=file_bytes,
)
result: AnalysisResult = poller.result()

print("\nMarkdown Content:")
print("=" * 50)

content = result.contents[0]
display(Markdown(content.markdown))
print("=" * 50)
```

The output is shown below. It is a very good structured result, and it preserves the table semantics from the original invoice file really well.

![[Pasted image 20260409112414.png]]

#### Image Intelligence

Next, let's ask it to analyze the image below.

![[pieChart.jpg]]

For images, there is also a built-in standard analyzer called `prebuilt-imageSearch`.

```python
print("\n" + "=" * 60)
print("IMAGE ANALYSIS FROM URL")
print("=" * 60)

file_path = "sample_files/pieChart.jpg"

with open(file_path, "rb") as f:
    file_bytes = f.read()

poller = client.begin_analyze_binary(
    analyzer_id="prebuilt-imageSearch",
    binary_input=file_bytes,
)

result = poller.result()

content = result.contents[0]
print("Markdown:")
display(Markdown(content.markdown))

summary = content.fields.get("Summary") if content.fields else None
if summary and hasattr(summary, "value"):
    print(f"Summary: {summary.value}")
```

As you can see, its understanding of this image is already quite accurate.

```
Summary: The image is a 3D pie chart divided into four segments representing different ranges of hours. The segments are labeled with their respective percentages: 1-39 hours at 6.7%, 40-50 hours at 18.9%, 50-60 hours at 36.6%, and 60+ hours at 37.8%. The largest segment is 60+ hours, followed closely by 50-60 hours.
```
#### Audio Intelligence

Next comes intelligent analysis for audio files. Here we have a call center recording, and we can process it with the `prebuilt-audioSearch` analyzer:

```python
print("\n" + "=" * 60)
print("AUDIO ANALYSIS FROM URL")
print("=" * 60)

file_path = "sample_files/callCenterRecording.mp3"

with open(file_path, "rb") as f:
    file_bytes = f.read()

poller = client.begin_analyze_binary(
    analyzer_id="prebuilt-audioSearch",
    binary_input=file_bytes,
)

result = poller.result()
audio_content = cast(AudioVisualContent, result.contents[0])

print("Markdown:")
display(Markdown(audio_content.markdown))

summary = audio_content.fields.get("Summary") if audio_content.fields else None
if summary and hasattr(summary, "value"):
    print(f"Summary: {summary.value}")
```

It extracted the full conversation transcript, identified different speakers, and reconstructed the whole dialogue in text form.

![[Pasted image 20260409114715.png]]
It also generated an overall summary:
```
Summary: The conversation is a customer service interaction where Maria Smith contacts Contoso to inquire about her current point balance. The agent, John Doe, verifies her identity by asking for her date of birth and then informs her that she has 599 points. Maria confirms she does not need further information and ends the call politely.
```

If you use online meeting software regularly, you have probably already used the feature that generates meeting summaries from audio recordings. Based on the service above, we can absolutely build something similar by ourselves. I will share more about that in future articles.

#### Video Intelligence

Finally, let's see how to analyze video content. Here I used `prebuilt-videoSearch` to analyze a short Azure AI promotional video:

![[FlightSimulator (2).gif]]

The sample code is shown below:

```python
print("\n" + "=" * 60)
print("VIDEO ANALYSIS FROM URL")
print("=" * 60)

file_path = "sample_files/FlightSimulator.mp4"

with open(file_path, "rb") as f:
    file_bytes = f.read()

poller = client.begin_analyze_binary(
    analyzer_id="prebuilt-videoSearch",
    binary_input=file_bytes,
)

result = poller.result()
segment_index = 1

for media in result.contents:
    video_content = cast(AudioVisualContent, media)

    print(f"\n--- Segment {segment_index} ---")
    print("Markdown:")
    display(Markdown(video_content.markdown))

    summary = video_content.fields.get("Summary") if video_content.fields else None
    if summary and hasattr(summary, "value"):
        print(f"Summary: {summary.value}")

    print(
        f"Start: {video_content.start_time_ms} ms, End: {video_content.end_time_ms} ms"
    )
    print(f"Frame size: {video_content.width} x {video_content.height}")

    print("---------------------")
    segment_index += 1
```

It also successfully extracted the corresponding content.
![[Pasted image 20260409133030.png]]

Its summary of the video content is also very accurate:

```
Summary: The video opens with a scenic aerial view of an island, transitioning to a collaboration logo between Flight Simulator and Microsoft Azure AI. It then cuts to an interview setting where a man discusses the importance of high-quality data for neural text-to-speech (TTS) technology. Visuals of audio waveforms and data centers emphasize the scale and technology behind the TTS model, which is built on 3,000 hours of data to capture nuanced, natural human voices. The scene shifts to expansive data center facilities and then to vibrant, realistic flight simulation footage showing planes flying over landscapes and approaching airports. The segment concludes with ground crew directing an Airbus plane, highlighting the integration of advanced AI voice technology in realistic flight simulation environments.
```
