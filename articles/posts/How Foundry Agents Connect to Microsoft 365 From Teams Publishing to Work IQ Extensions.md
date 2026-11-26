---
date: 2026-10-27
authors:
  - chris-bao
categories:
  - Agent
title: How Foundry Agents Connect to Microsoft 365 From Teams Publishing to Work IQ Extensions
---
## Background

In previous articles, I believe many of you have already seen the value and convenience of Microsoft Foundry Agent Service when it comes to hosting Foundry Agents. With this serverless approach, developers do not need to deploy the agent themselves, and they also do not need to manage the underlying infrastructure.

More importantly, the capabilities of Microsoft Foundry Agent Service go beyond hosting. It can also help you quickly publish a finished Foundry Agent to different channels. For example, letting users access your Foundry Agent directly in Teams is a very practical scenario. In this article, I will share how to complete exactly that.

## Build a Foundry Agent

Let's first build a simple Foundry Agent. This agent can answer employee questions based on uploaded company policy documents, and the idea is not complicated. In Microsoft Foundry Agent Service, this kind of agent is called a prompt agent, and it can be described with the following YAML:

```yaml
metadata:
  logo: Avatar_Default.svg
  description: ""
  modified_at: "1776825465"
  microsoft.voice-live.enabled: "false"
object: agent.version
id: enterprise-knowledge-agent:4
name: enterprise-knowledge-agent
version: "4"
description: ""
created_at: 1776825466
definition:
  kind: prompt
  model: gpt-4.1
  instructions: |2-
    You are an Enterprise Knowledge Assistant for Contoso Corporation.

    Your role:
    - Answer questions about company policies and procedures
    - Provide accurate information from uploaded documents
    - Be professional, helpful, and concise
    - If you don't know the answer, say so and suggest who to contact

    Always cite your sources when referencing specific policies.
  tools:
    - type: file_search
      vector_store_ids:
        - vs_Q9GfoktTrsXTrPUPKEzczpAt
status: active
instance_identity:
  principal_id: a904a1bf-2dc4-46f3-9705-1730a69c890e
  client_id: a904a1bf-2dc4-46f3-9705-1730a69c890e
blueprint:
  principal_id: c8109e69-944f-44e3-b237-ca6fd7eea767
  client_id: c8109e69-944f-44e3-b237-ca6fd7eea767
blueprint_reference:
  type: ManagedAgentIdentityBlueprint
  blueprint_id: enterprise-knowledge-agent-90cee
```

Next, let's see how to publish it into Teams.

### Publish a Foundry Agent to Microsoft 365/Teams

This publishing flow is already integrated into Microsoft Foundry Agent Service, as shown below:

![[Pasted image 20260423094430.png]]

Here you need to fill in several settings, and the most important one is `Azure Bot Service`. Microsoft Foundry Agent Service uses this Azure service to connect your agent with Microsoft 365. I will not expand on the internal mechanism of `Azure Bot Service` in this article, but I can share that separately in a future post.

The following screenshot shows the created `Azure Bot Service`:

![[Pasted image 20260422132925.png]]

The remaining settings are fairly straightforward and not too complex. After the publishing process succeeds, you will see a notification like this:

![[Pasted image 20260422113737.png]]

![[Pasted image 20260422113554.png]]

### Use the Foundry Agent in Microsoft 365/Teams

Now let's look at how to use it inside Teams.

In Teams, it appears as an extension app, and you can find it under `Manage your apps`:

![[Pasted image 20260422113652.png]]

After that, you can directly interact with the Foundry Agent.

![[Pasted image 20260422114226.png]]
## A More Powerful Microsoft 365 Agent

The publishing approach above solves the distribution problem for Foundry Agents quite well, but its capabilities are still relatively basic. If you want to build a more powerful Microsoft 365 Agent, I think there are two directions worth exploring:

- `Work IQ`: `Work IQ` is an important part of Microsoft's AI strategy. It allows a Foundry Agent to access data from the Microsoft 365 ecosystem, including emails, meetings, and documents. From an implementation perspective, `Work IQ` itself is an `MCP` service. You can download and run it with `npx @microsoft/workiq-mcp-server`, and then build a more powerful Microsoft 365 Agent based on this `MCP` tool.
- `M365 Agents Toolkit`: Publishing a Foundry Agent directly from Microsoft Foundry Agent Service is a very direct solution. However, when you need more customization, for example if you do not want to use the default `Entra ID` single sign-on flow, or if you want to add custom middleware to message processing, then `M365 Agents Toolkit` gives you much more flexibility. Technically speaking, you would build a standalone application based on `M365 Agents Toolkit`, and that application acts as a proxy layer between the Foundry Agent and Microsoft 365 apps.

Both directions are worth exploring further. If there is interest, I can continue with separate articles to share practical usage and integration experience around `Work IQ`, `MCP`, and `M365 Agents Toolkit`.

If your goal is simply to connect a Foundry Agent to Teams as quickly as possible, the built-in publishing capability in Microsoft Foundry Agent Service is already efficient enough. But if you need deeper integration with the Microsoft 365 ecosystem, then bringing in `Work IQ` or `M365 Agents Toolkit` is a better next step.
