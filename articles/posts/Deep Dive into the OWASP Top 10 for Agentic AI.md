---
date: 2026-09-27
authors:
  - chris-bao
categories:
  - Security
title: Deep Dive into the OWASP Top 10 for Agentic AI
---
## Background

Today I want to share a very interesting topic: the `security risks of Agentic AI`. In this area, there is a well-known organization called `OWASP (Open Worldwide Application Security Project)`. In the internet era, OWASP published the widely adopted security guidance `OWASP Top 10 for Web Applications`. In the Agentic AI era, that framework is clearly no longer enough. So in 2026, OWASP officially published the `OWASP Top 10 for Agentic Applications`. In this article, I want to walk through the ten most common and representative security risks in Agentic AI one by one.

## How the Attack Surface Changes

Agentic AI systems can make autonomous decisions and call external tools. Because of that, their security risks are far more complex than those of traditional web applications. In security terms, this means the `attack surface` becomes broader and more dynamic.

`Attack surface` refers to all the entry points and weaknesses an attacker can use to break into a network or system. You can think of it as all the doors and windows of a house: the more doors and windows there are, the more possible entry points an intruder may find.

- `Broader attack surface`: Agentic AI can access many more types of components, such as tools, memory systems, credentials, external data sources, and other AI agents.
- `More dynamic attack surface`: The components an Agentic AI system interacts with are not fixed. They can change in real time depending on context and task.

![[Pasted image 20260702162128.png]]

Next, let's examine these risks one by one.

### Agent Goal Hijack

![[Pasted image 20260702220109.png]]

AI agents usually define their roles and high-level behavioral rules through system prompts. If an attacker tampers with the system prompt and changes the agent's behavior, the impact is much greater than manipulating a single model response, because it affects every later decision the agent makes.

What makes this even more concerning is that the attack is becoming more covert. Attackers can embed malicious instructions inside documents, emails, or even the vector database of a RAG system.

Possible defenses include filtering `prompt injection`, such as the Azure Foundry Content Safety capability I mentioned in a previous article. Another useful approach is to separate data from instructions and strictly limit what tools the agent is allowed to use.

### Tool Misuse and Exploitation

![[Pasted image 20260702222116.png]]

Tool use is one of the most important capabilities of an agent. The problem here is not necessarily that the tool itself is vulnerable. The risk comes from the agent calling the tool at the wrong time or in the wrong way.

For example, a customer service agent may call the backend system of an e-commerce platform. It makes sense to expose an order lookup API to that agent. But if the refund API is also exposed, that creates risk. The refund interface may be legitimate and necessary in the e-commerce system, so the tool itself is not the issue. The real problem is that it should not be available to the agent, otherwise an attacker may abuse the agent to trigger unauthorized refunds or transfers.

Here is another example. A personal assistant agent may have two tools: database read access and email sending. Each tool may be legitimate on its own. But once the agent chains them together, it may read data from the database and then exfiltrate it through email.

Defenses include enforcing the `principle of least privilege` at the tool level, exposing only the functionality required for the task. You can also insert `risk assessment` middleware between the agent's decision layer and execution layer, so security policy can constrain behavior before a tool call is actually made. When reusing existing system credentials, it is also a good idea to raise the security bar by shortening token lifetimes and reducing token reuse risk.

### Identity and Privilege Abuse

![[Pasted image 20260702222127.png]]

This risk reflects a major limitation in today's AI agent landscape: traditional identity and authorization protocols such as OAuth 2.0 are no longer sufficient for Agentic AI systems.

The classic `Bearer Token` model essentially means: `whoever holds this token gets the corresponding permissions`. That is often acceptable for traditional software with predictable trust boundaries. But in Agentic AI systems, an agent may delegate tasks to downstream agents, and different agents naturally should not have the same permissions. If we simply reuse existing identity and security credentials, privilege abuse becomes very likely.

For example, a financial services agent may already have high privileges. Besides financial functions, it may also be `incorrectly` granted access to HR and legal services. At first glance, this may not look dangerous if the agent itself cannot directly read or write data. But if it delegates data operations to a database agent, even a low-privilege database agent may indirectly expose HR and legal data because it inherits excessive upstream authority.

The most fundamental defense is to build AI-native authorization protocols. Before such protocols become mature, at minimum we should strictly limit token scope and lifetime.

### Agentic Supply Chain Vulnerabilities

![[Pasted image 20260702222142.png]]

From a software supply chain perspective, dependencies in traditional software are mostly determined during the build phase, so the scope is relatively controllable. For agents, however, external tools can be selected dynamically at runtime, which naturally creates much higher risk.

One attack pattern is to place malicious instructions inside the description of an MCP tool.

Possible defenses include extending `SBOMs (Software Bill of Materials)` into `AIBOMs (AI Bill of Materials)` to manage the provenance of tools and dependencies. We can also use hashes, encryption, and digital signatures to verify critical information such as tool definitions. At the same time, organizations should maintain a tool hygiene process: once a tool is found to be risky, it should be removed from the available toolset as soon as possible. In other words, an agent's toolset should no longer be treated as a fixed list.

### Unexpected Code Execution

![[Pasted image 20260702222151.png]]

Many agents today are given code execution capability in order to become more powerful. Once an agent can generate and execute code, it effectively gains access to an almost unlimited toolset: if a capability is not already available as a built-in tool, the agent may try to create it on the fly through code.

But that same capability brings significant security risk. In this sense, the problem is not fundamentally different from malicious code execution in traditional software.

Sandboxing and permission control remain among the most effective defenses.

### Memory and Context Poisoning

![[Pasted image 20260702222200.png]]

Because large language models are stateless by nature, agents often need their own memory systems. These memory systems become part of the agent's context window. Once an attacker injects malicious content into that memory, the effect may persist for a long time.

One defense is to design `security-aware context engineering`. Context design is not only about improving accuracy and token efficiency. It also needs to take security risk into account. Memory systems should also be isolated across different users, tasks, and sessions.

### Insecure Inter-Agent Communication

![[Pasted image 20260702222209.png]]

This risk highlights the security challenges of multi-agent systems. It has something in common with classic distributed system risks, but it is not exactly the same. In A2A communication, agents are not just calling APIs. They may also exchange context, instructions, and other higher-risk information.

Possible solutions include adopting stricter security protocols such as mTLS, combined with cryptographic validation to verify communication content and integrity.

### Cascading Failures

![[Pasted image 20260702222223.png]]

Compared with traditional software systems, Agentic AI requires us to pay closer attention to how security problems `propagate` through the system and create `cascading effects`.

The good news is that we can learn from existing `SRE` and `fault tolerance` practices. At the core, they address the same question: when one component fails, how do we keep the rest of the system working?

### Human-Agent Trust Exploitation

![[Pasted image 20260702222232.png]]

This risk comes from excessive human trust in agents.

For example, an agent may prompt the user to open a preview interface. The user may trust the suggestion, while the action behind the scenes actually triggers something dangerous.

### Rogue Agents

![[Pasted image 20260702222240.png]]

This risk describes an almost science-fiction-style concern: the threat does not come from an external attacker, but from the agent's own evolving capabilities eventually becoming uncontrollable.

For this type of threat, continuous monitoring is still necessary.

## Summary

There are no perfectly clear boundaries between these risks. As we have seen above, the problems they describe are closely related. In the real world, an attack rarely exploits just one weakness. More often, it takes advantage of multiple security gaps at the same time.
