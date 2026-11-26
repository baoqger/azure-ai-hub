---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - MCP
title: Agentic Workflows for Azure - A Practical Guide with GitHub Copilot CLI and Azure MCP Server
---
## Background

In this article, I want to share an agentic workflow I have been exploring recently. It combines GitHub Copilot CLI with Azure MCP Server to help us work more efficiently on development and operations tasks in Azure. Whether you are a software engineer or a DevOps engineer, I believe you can get practical value from this workflow and the AI tools behind it.

![[Pasted image 20260527160819.png]]
## Azure MCP Server

Azure MCP Server exposes a rich set of capabilities through the standard MCP protocol. One interesting design choice is that it organizes tools by namespace, and each namespace then contains a set of function-level tools underneath it.

The screenshot below shows the namespace-level tools. As you can see, they already cover a wide range of Azure services.
![[Pasted image 20260527100010.png]]

Let's take `azure-mcp-storage` as an example and see what the function-level tools look like under that namespace:

![[Pasted image 20260527100426.png]]

Based on these tools, we can build several typical agentic workflows:

- Learning Azure: explore and learn Azure services with the help of official Azure documentation.
- Design and development: support solution design and implementation based on the actual context of your project.
- Deployment: deploy your project to the cloud.
- Troubleshooting in Azure: if your project runs into issues on Azure, Azure MCP Server can also help with investigation and troubleshooting.

In the Demo section below, I will walk through a couple of simple examples.

## GitHub Copilot CLI

Software engineers and DevOps engineers usually have a strong preference for working in the Shell. CLI tools provide a highly efficient environment and significantly reduce the cost of switching between different tools and interfaces.

GitHub Copilot has also introduced its own CLI:

```shell
npm install -g @github/copilot
```

After you run the `login` command and sign in with your Copilot account, you can start this agentic workflow.

![[Pasted image 20260527105720.png]]

## Add Azure MCP Server

When you integrate Azure MCP Server into GitHub Copilot CLI, you do not need to preinstall the MCP service locally. Inside the Copilot interactive environment, run the `/mcp add` command and configure it as shown below:

![[Pasted image 20260527110014.png]]

Choose `STDIO` as the local inter-process communication mode, then start the MCP service directly with:

```shell
npx -y @azure/mcp@latest server start
```

## Authenticate Azure MCP Server

Azure MCP Server uses the user's Entra ID for authentication. During startup, it checks multiple credential sources in order, including environment variables, VS Code, Azure CLI, and AZD CLI. In my case, I use Azure CLI. By logging in with the following command, Azure CLI caches a valid token locally:

```shell
az login --tenant <your-tenant-id>
```

Next, explicitly tell Azure MCP Server to read credentials from the Azure CLI cache:

```powershell
$env:AZURE_TOKEN_CREDENTIALS = "AzureCliCredential"
```

After that, Azure MCP Server should connect successfully.
![[Pasted image 20260527143027.png]]

For example, I can ask it to list all my resource groups:

![[Pasted image 20260527143537.png]]

## Demo

Next, let's look at two typical scenarios.

### Learn Azure Services from an Application Context

For example, suppose I have a .NET web application. I can ask Copilot what Azure services would be appropriate if I want to deploy it to Azure. Copilot first scans the local files, then uses MCP to retrieve the relevant documentation, and finally gives me a practical solution I can use as a reference:

![[Pasted image 20260527143725.png]]

![[Pasted image 20260527143730.png]]

![[Pasted image 20260527143742.png]]

### Create Azure Resources

Remembering all Azure CLI commands can be painful. Now we can express the intent directly and let MCP handle the execution for us. The example below shows the result when I ask Copilot to help me create an Azure Blob Storage account:

![[Pasted image 20260527143952.png]]

## Summary

If you already prefer doing development or operations work from the command line, combining GitHub Copilot CLI with Azure MCP Server feels like a very natural upgrade. On one side, you keep the speed and focus of the CLI experience. On the other side, you bring Azure documentation lookup, resource operations, and troubleshooting into the same workflow. Smart design, right?
