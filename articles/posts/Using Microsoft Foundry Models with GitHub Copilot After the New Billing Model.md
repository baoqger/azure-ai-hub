---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - FinOps
title: Using Microsoft Foundry Models with GitHub Copilot After the New Billing Model
---
#github #githubcopilot

## Background

If you are familiar with GitHub Copilot, you may already know that Copilot introduced a new billing model in early June 2026. Based on community feedback, many users have seen their token-related costs increase significantly.

In this article, I will share what I learned about integrating GitHub Copilot with a large language model deployed on Microsoft Foundry. I will walk through two integration options: GitHub Copilot CLI and the GitHub Copilot extension in VS Code.

![[Cloud_AI_Billing_Integration_Guide.png]]
## Why I Started Looking Into This

I have been using the Copilot Pro subscription, which costs 10 USD per month. It is the most basic paid plan.

Actually, Copilot is not the coding agent I use in my work environment. My company uses Cursor. However, I have always paid close attention to the development of GitHub Copilot, because I think GitHub has a strong ecosystem advantage. From a technical perspective, Copilot can integrate deeply with GitHub's own infrastructure and extend its value across the entire software development lifecycle.

This is also part of GitHub Copilot's business strategy when competing with products such as Claude Code and Codex. Instead of only competing in the coding agent terminal space, GitHub can rely on its broader developer platform. Of course, this is another topic. After I study it more deeply, I will share my thoughts with you.

Back to the billing model. Previously, Copilot used a model called `premium requests`. Simply speaking, it charged based on requests. Any interaction with Copilot counted as a request. In the early stage of coding agents, many people were still doing vibe coding and using these tools almost like an intelligent search engine. Under that usage pattern, request-based billing was still reasonable.

But now, vibe coding is fading away, and more advanced AI-assisted programming patterns and agentic workflows are emerging. On the surface, two interactions may both look like one request, but their complexity and token consumption can be completely different. That is why a new billing model becomes necessary.

Under the new billing model, one `AI Credit = 0.01$`. For example, my Copilot Pro subscription includes `1000 Credit` as the `base` part. In addition, GitHub Copilot also provides some `flex` credits. For the Pro plan, that is `500 Credit`, so my current total quota is `1500 Credit`.

![[Pasted image 20260716093744.png]]

Of course, these are only the surface-level calculations. The real cost still depends on token consumption and the pricing of the selected model.

As mentioned above, I am not currently using Copilot for my main work development tasks. I mainly use it for personal projects and experiments with new methods. Even so, I can clearly feel that the current Pro plan is no longer enough for me.

At the same time, I have almost 300 USD of Azure Credit every month. Why not make use of it?

So I decided to deploy a large language model on Foundry using my Azure subscription, and then connect it to GitHub Copilot. Great, right?

## Setup

##### Deploy A Model On Foundry

First, let's deploy a `gpt-5.1-mini` model on Foundry. I am only using it as an example here. You can choose a more suitable coding model based on your own needs.

![[Pasted image 20260716100134.png]]

When integrating it with GitHub Copilot later, authentication is required, so we need the API key information for this deployment.

##### GitHub Copilot CLI Integration

The `Copilot CLI` integration is very straightforward. We only need to set the following environment variables.

```powershell
$ResourceName = "chris-copilot-resource"
$DeploymentName = "gpt-5-mini"
$ApiKey = "your-api-key"

$env:COPILOT_PROVIDER_BASE_URL = "https://$ResourceName.openai.azure.com/openai/deployments/$DeploymentName"
$env:COPILOT_PROVIDER_TYPE = "azure"
$env:COPILOT_PROVIDER_API_KEY = $ApiKey
$env:COPILOT_MODEL = $DeploymentName
```

Then we can start Copilot. From the interface, we can see that it is already using the `gpt-5-mini` model.

![[Pasted image 20260716100905.png]]

##### VS Code GitHub Copilot Extension Integration

Integrating a custom model into GitHub Copilot in VS Code is a little more complicated. We need to use the `Foundry Toolkit` VS Code extension.

![[Pasted image 20260716101344.png]]

This extension exposes many Foundry capabilities directly inside the VS Code environment. It helps developers manage various Foundry resources directly from the IDE, including model deployments. In this article, we only use it to integrate a model. In future articles, I will share more about how to use it for additional development workflows, so please stay tuned.

For example, as shown below, I can see the model I just deployed.

![[Pasted image 20260716101644.png]]

Next, from the Model button in the Chat window, we can open the window for adding models. Through the Foundry Toolkit, we can see the models available on Foundry. Select the model, click "Add Models", and then choose "Azure" to indicate that this model comes from the Azure cloud platform.

We can also see that other platforms are supported by default, such as Google, OpenAI, and Anthropic. For platforms that are not included in the default list, we can extend the integration through a Custom Endpoint.

![[Pasted image 20260716102554.png]]

After that, we can start using it.

![[Pasted image 20260716102824.png|230]]

---

I am Chris Bao, a Microsoft Certified Trainer focusing on the Azure AI platform. I specialize in Azure AI services and agent development, and I provide training and consulting services for enterprises and individual learners.

For collaboration, please contact: baoqger@gmail.com
