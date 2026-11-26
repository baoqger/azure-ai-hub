---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - Multimodality
title: Image Generation in Practice - Building a Reusable Claude Skill on Microsoft Foundry
---
#azure #azureai #skill #aigc

## Background

In this article, let's step into a new area: `AI-based image generation`. This technology has broad potential in fields such as `media`, `education`, and `marketing`. I will first share what I learned about the image generation models available on Microsoft Foundry, then build a simple image generation script around one of them. As a next step, I will package that script into a reusable Claude Skill so it can be used more conveniently in daily work.

## Image Generation Models on Microsoft Foundry

![[Pasted image 20260417150217.png]]

Microsoft Foundry provides several image generation models, including GPT-family offerings such as `gpt-image-1.5`. However, that model requires a separate approval process and is only available to users with an Azure enterprise account. For most individual developers, that is not very convenient, so here I chose `Flux.2-pro`.

![[Pasted image 20260417151003.png]]

This model does not have extra access restrictions, and regular developers can deploy it quite easily.

![[Pasted image 20260417151106.png]]

Next, let's see how to generate images with this model.

## Image Generation Demo

How can we call the `Flux.2-pro` model deployed on Microsoft Foundry? After some research, I found that the legacy Foundry UI (yes, the old UI, not the new one) still contains some very useful reference information.

![[Pasted image 20260417152052.png]]

It provides the following shell example. You can generate an image by sending a request directly to the endpoint:

```shell
curl -X POST "https://your-service-resource.services.ai.azure.com/providers/blackforestlabs/v1/flux-2-pro?api-version=preview" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AZURE_API_KEY" \
  -d '{
    "prompt": "A photograph of a red fox in an autumn forest",
    "width": 1024,
    "height": 1024,
    "n": 1,
    "model": "FLUX.2-pro"
  }' \
  | jq -r '.data[0].b64_json' \
  | base64 --decode > generated_image.png
```

Based on that example, I wrote a simple Python application that achieves the same result.

```python
import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
subscription_key = os.environ["AZURE_OPENAI_API_KEY"]
model = os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"]

# Your Foundry resource endpoint (same as curl)
ENDPOINT = endpoint

# The curl used: Authorization: Bearer $AZURE_API_KEY
AZURE_API_KEY = subscription_key

payload = {
    "prompt": "A photograph of a red fox in an autumn forest",
    "width": 1024,
    "height": 1024,
    "n": 1,
    "model": model,
}

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AZURE_API_KEY}",
}

resp = requests.post(ENDPOINT, headers=headers, json=payload, timeout=180)
resp.raise_for_status()

data = resp.json()
b64_img = data["data"][0]["b64_json"]  # same jq path: .data[0].b64_json
img_bytes = base64.b64decode(b64_img)

out_path = "generated_image.png"
with open(out_path, "wb") as f:
    f.write(img_bytes)

print(f"Saved: {out_path}")
```

There are two key points in the code above. First, it uses an API key for authentication. Second, the `payload` object defines the desired image output, such as the text prompt and the image size through `width` and `height`. With the request above, I can generate a lovely fox image like the one below.

![[Pasted image 20260417152931.png]]

With that initial experiment working, the next step was to package it as a Claude Skill. That way, whenever I need image generation, I can simply ask an agent in Claude Code to handle it for me. In the following section, let's see how I made that improvement.

## Packaging It as a Claude Skill

````markdown
---
name: azure-image-generator
description: Generate images with Azure OpenAI or Azure AI Foundry by calling the local Python helper in this skill. Use when the user asks to generate an image from a prompt, create cover art, render a concept image, or save a prompt as a descriptively named PNG with Azure image generation.
---

# Azure Image Generator

## Use This Skill When

- The user asks to generate an image from a text prompt.
- The user mentions Azure OpenAI, Azure AI Foundry, or Azure-based image generation.
- The task needs a local PNG output file, especially one whose filename should match the prompt content.

## Required Setup

The script reads environment variables from `.env` via `python-dotenv`.

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT_NAME`

The endpoint value must be the full POST URL for the image generation request, not only the resource root.

## First-Run Dependency Setup

Before first use, ensure the Python dependencies for this skill are installed:

```bash
python -m pip install -r ".claude/skills/azure-image-generator/requirements.txt"
```

Do not run dependency installation on every invocation.

Only install dependencies when:

- The user asks to set up or install the skill.
- The environment is new or likely missing packages.
- The script fails because `requests` or `python-dotenv` is not available.

If the environment is already prepared, skip installation and run the helper directly.

## Prompt Handling Rule

Do not pass the raw prompt directly on the shell command line.

Always:

1. Write the prompt exactly as provided to a UTF-8 text file.
2. Pass the file path to the script with `--prompt-file`.

This avoids escaping bugs with quotes, backticks, ampersands, pipes, dollar signs, newlines, and non-ASCII text.

## Output Filename Rule

Choose the output filename before running the helper.

- If the user already gave a filename or path, use it as provided.
- Otherwise, derive a short filename from the prompt content.
- Use lowercase kebab-case such as `red-fox-autumn-forest.png`.
- Keep the name concise and descriptive, usually 3 to 6 words.
- Remove unsafe filesystem characters and avoid punctuation other than hyphens.
- Always end the filename with `.png`.
- If the prompt is too vague to name well, fall back to `generated-image.png`.

## Workflow

1. If the user did not provide a prompt, ask for it.
2. If this looks like a first run or the environment is not prepared, install dependencies from `requirements.txt`. Otherwise skip this step.
3. Choose an output path. If the user gave one, use it. Otherwise infer a descriptive PNG filename from the prompt, such as `red-fox-autumn-forest.png`.
4. Save both the prompt file and generated image in the same folder as the script unless the user explicitly requests another path.
5. Write the prompt verbatim to a UTF-8 text file in the script folder such as `image-prompt.txt`.
6. Run the helper script:

```bash
python ".claude/skills/azure-image-generator/scripts/generate_image.py" --prompt-file "image-prompt.txt" --output "red-fox-autumn-forest.png"
```

7. If needed, pass optional size overrides:

```bash
python ".claude/skills/azure-image-generator/scripts/generate_image.py" --prompt-file "image-prompt.txt" --output "red-fox-autumn-forest.png" --width 1024 --height 1024
```

8. Report the saved output path and any API errors clearly.

## Notes

- Preserve the prompt text exactly. Do not rewrite it unless the user asked for prompt improvement.
- If the prompt spans multiple lines, keep the line breaks in the prompt file.
- Do not rely on the helper's generic default filename when the prompt is specific enough to name the image.
- The helper resolves relative `--prompt-file` and `--output` paths from its own `scripts` folder.
- The helper returns a single image file based on the first item in `data[0].b64_json`.

## Additional Reference

- See [README.md](README.md) for setup details and CLI usage.
````

This Claude Skill introduces a few improvements over the original script. First, the generated image filename is no longer hardcoded. Instead, it is derived from the content of the `prompt`, which makes the output file more descriptive. Second, the `prompt` is no longer passed directly through the shell command. It is first stored in a file and then read by the script, which helps avoid bugs caused by special characters in the prompt. After my own testing and validation, this Claude Skill can produce stable output.

Now it is time to start your own creative journey with this Skill.

---

I am Chris Bao, a Microsoft-certified trainer focused on the Azure AI platform. I specialize in Azure AI services and agent development, and I provide training and consulting services for both enterprises and individual learners.  
For collaboration, please contact: baoqger@gmail.com
