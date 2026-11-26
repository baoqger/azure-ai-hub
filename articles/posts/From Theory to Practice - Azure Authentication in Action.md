---
date: 2026-10-26
authors:
  - chris-bao
categories:
  - Security
title: From Theory to Practice - Azure Authentication in Action
---

*Learn how theoretical knowledge of Entra ID and RBAC becomes the solution to practical authentication challenges in Azure AI implementations*

## Introduction

In the world of cloud architecture, there's often a gap between understanding theoretical concepts and applying them to solve real-world problems. This blog explores that journey through the lens of Azure authentication, showing how fundamental identity and access management concepts directly inform practical solutions for AI workloads.

## The Theoretical Foundation

Before diving into implementation, let's establish the core concepts that form the foundation of Azure's authentication and authorization model.

### Understanding the Authentication vs. Authorization Distinction

**Entra ID** handles authentication and identity management - it answers "who are you?" This is about verifying identities and establishing trust.

**IAM (Identity and Access Management)** handles authorization and access control through RBAC - it answers "what can you do?" This is about granting permissions and controlling resource access.

### The Power of Managed Identities

Managed identities represent a crucial innovation in cloud security. They are workload identities that eliminate the need for developers to manage credentials manually. Think of them as "digital passports" for your cloud resources - automatically created, automatically managed, and automatically rotating.

There are two key identity types:
- **Human identities**: Users, groups
- **Machine identities**: Devices, workloads (applications, service principals, managed identities)

A managed identity is essentially an identity assigned to Azure compute resources or app hosting platforms. It's particularly powerful because it removes the need to store and manage connection strings, keys, or certificates in application code.

### RBAC: The Authorization Framework

Azure Role-Based Access Control (RBAC) provides the mechanism for controlling resource access through role assignments. Every role assignment consists of three critical elements:

1. **Security Principal**: Who gets access (user, group, service principal, managed identity)
2. **Role Definition**: What they can do (list of permissible actions)
3. **Scope**: Where it applies (management group, subscription, resource group, or specific resource)

The beauty of RBAC lies in its simplicity yet power - you attach a role definition to a security principal at a specific scope to grant access.

## The Real-World Challenge

Now, let's see how these theoretical concepts play out in practice. Consider a typical scenario: implementing agentic retrieval using Azure AI Search.

### The Setup

You're building an AI-powered search system that needs to:
1. Create a search index in Azure AI Search
2. Upload documents to make them searchable
3. Configure knowledge sources and knowledge bases
4. Use agentic retrieval to fetch intelligent results

For the detailed process, you can refer to this official document: https://learn.microsoft.com/en-us/azure/search/search-get-started-agentic-retrieval?tabs=windows&pivots=python
### The Problem Strikes

Everything seems to be going smoothly until you hit a critical error:

```
Message: Could not complete model action. The service failed to authenticate to the model endpoint.
```

This is a classic authentication failure - your Azure AI Search service needs to access models in Azure AI Foundry, but it doesn't have the proper credentials or permissions.

## The Theory-to-Practice Solution

Here's where the theoretical concepts directly inform the practical solution:

### Step 1: Apply Managed Identity Concepts

Following the managed identity theory, you create a system-assigned managed identity for your Azure AI Search service. Remember the theory: a system-assigned managed identity is a Microsoft Entra ID security principal that's automatically created and linked to your Azure resource.

![[Pasted image 20260320163201.png]]
### Step 2: Implement RBAC Role Assignment

Now apply the RBAC framework. You need to assign a role that allows your search service to access the AI models. The solution involves:

1. **Security Principal**: The managed identity you just created for your search service
2. **Role Definition**: "Cognitive Services User" role (provides necessary permissions)
3. **Scope**: Your Microsoft Foundry resource (the specific resource containing the models)

This is exactly what the RBAC theory describes - attaching a role definition to a security principal at a particular scope for the purpose of granting access.

### The Practical Implementation

In the Azure portal, this translates to:
1. Navigate to your Microsoft Foundry resource
2. Access the IAM (Access Control) page
3. Add a role assignment
4. Select "Cognitive Services User" role
5. Choose your search service's managed identity as the member

![[Pasted image 20260320163455.png]]

My AI Search service is named "rag-time" and the Foundry project is "chris-rag-time", I'm essentially adding the "rag-time" managed identity as a Cognitive Services User to the "chris-rag-time" Foundry resource.

After this setting, the authentication error is fixed! 



