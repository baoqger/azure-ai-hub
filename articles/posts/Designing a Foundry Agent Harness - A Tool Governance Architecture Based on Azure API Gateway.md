---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - Agent
title: Designing a Foundry Agent Harness - A Tool Governance Architecture Based on Azure API Gateway
---
#apim #security

## Background

In this article, I want to share what I learned about a very popular topic: `harness engineering`. This is a broad topic with many moving parts, so instead of trying to cover everything at once, I will focus on one important area first: how to govern `tool` calls made by AI agents.

This post uses `Azure API Gateway` to manage an agent's toolset, and explores why this architecture brings significant value to an agent's `harness`.

At the same time, I will also walk through Azure Foundry's `connection` capability and show why using `connection` to integrate external tools is a smart design.

If you are also interested in these two topics, let's continue in the following sections.

![[Governing_AI_Agents_with_Gateways.png]]
## Harness Engineering

Compared with the more familiar `prompt engineering` and `context engineering`, `harness engineering` is a broader concept. A common definition in the technical community is:

```plain
Agent = Model + Harness
```

In other words, for an agent, almost everything beyond the model itself can be considered part of the `harness`. So naturally, it includes what we usually call `prompt` and `context` engineering, but it also includes other critical agent capabilities, such as the `toolset` that this article focuses on.

We also need to upgrade the way we think about an agent's `toolset`: tools are not just `function calls`; they are also the agent's `perception system` and `execution system`:

- `Eyes`: read files, inspect logs, use search engines, query databases
- `Hands`: write code, call APIs, run commands, submit tasks
- `Sensors`: test results, error messages, monitoring signals
- `Actuators`: trigger actions in external systems

These capabilities allow an agent to truly `observe the environment` and `operate on the environment`. That is why tool design and governance sit at the center of `harness` engineering. A well-designed tool should have at least the following characteristics:

- Clear input: explicit parameters and a stable schema
- Efficient, concise output: this is where tool management overlaps with `context` engineering. When a tool returns too much data, we should not push everything directly into the context window. Instead, we should extract the key information first and return only what the model really needs.
- Permission control: which tools require approval, which commands are prohibited, and which network requests are not allowed

For a locally running monolithic agent, these harness capabilities can be implemented directly inside the agent framework. But for an agent running in a distributed network environment, we need a more deliberate architecture to carry these responsibilities.

So in the next section, let's look at the value of managing Foundry Agent tools with `Azure API Gateway` from a `harness` perspective.

## Architecture Design

In this article, we will build a purchase-order agent. This agent completes its task by calling two tools: a `product catalog service` and an `order service`.

From a pure implementation point of view, the agent could call these two services directly. But here, we place both services behind `API Gateway` so that we can achieve stronger tool harness capabilities. I will break down the reasoning step by step below.

![[Pasted image 20260625084642.png]]

The architecture contains the following core components:

- `Foundry Agent` and `Foundry Model` services: deploy a GPT model on the Foundry platform, then use the Foundry Agent service to create two `prompt agents`. Foundry Agent currently supports two types of agents: `prompt agents` and `host agents`. The former are simpler and fully managed by Azure. The latter are more flexible, allowing you to choose your own agent framework and deploy it in containers. I shared the difference in a previous article.
- `API Management` service: create an API Gateway to manage the agent's external tools.
- `Logic App`: create an Azure Logic App that exposes an HTTP endpoint for the agent to call.
- `REST API` service: create a REST API that follows the OpenAPI standard for agent invocation.
- `Azure Monitor`: deploy `Application Insights` and `Log Analytics` so we can observe how the agent interacts with tools.

##### Deploy Foundry Model

Here is the GPT model that we deployed:

![[Pasted image 20260625090839.png]]

##### Create a Logic App Instance: Order Service

Next, we create the tools required by the purchase-order agent. In this example, the `order service` is implemented with Logic App.

![[Pasted image 20260625091729.png]]

As shown above, this Logic App implements an order service and exposes an HTTP endpoint. The logic is simple: if the quantity of a product in the order is less than or equal to 5, the request succeeds; otherwise, it fails.

Logic App is not the focus of this article, so for more details, you can refer to the official documentation or one of my previous posts.

##### Create a REST API: Product Catalog Service

For the REST API of the product catalog service, we use APIM's mock capability:

- Create an API instance
- Configure mock information for that API instance so it can simulate a REST API response

It looks like this:

![[Pasted image 20260625094856.png]]

##### API Gateway Service

Next, we also bring the Logic App under unified Gateway management.

To do that, we first create a `backend` instance called `orderworkflow-backend` to encapsulate the Logic App order-service endpoint:

![[Pasted image 20260625095149.png]]

Then we create an `api` instance that forwards incoming requests to that `backend`:

![[Pasted image 20260625095423.png]]

With this setup, the Gateway exposes two APIs externally: `Place Order API` and `Product Catalog API`. Together, they form the toolset for our purchase-order agent.

##### Agent Tool Harness Based on Gateway

From the perspective of a traditional cloud application, the role of a Gateway here is very familiar. It acts as a unified `control plane` for downstream services, centralizing security policies, hiding backend complexity, standardizing monitoring and auditing, providing rate limiting, and exposing stable tool interfaces in a consistent way.

But from the perspective of an AI agent, Gateway shows even more value as part of the tool harness:

- `Autonomous behavior control`: An agent can make its own decisions about when and how to call tools. It may repeatedly call the same tool, branch into unexpected paths, or even fall into retry loops. Gateway policies can be used to constrain these behaviors.
- `Prompt injection defense through tool input and output`: The output from downstream tools can easily become an entry point for malicious prompt injection. An AI Gateway can sanitize, constrain, or filter tool responses before they flow back into the model context.
- `Context control`: As mentioned above, tool outputs should be filtered appropriately before being sent to the model. This is a key part of context governance, and the Gateway layer is a natural place to implement it.
- `Permission management`: Authorization for tool invocation also belongs here. API Gateway can apply different permission policies to different downstream tools.

In other words, the gateway is not only doing API management. It is also taking on part of the responsibility of Agent Harness.

##### Foundry Connection

Now that both the tools and the model are ready, the next step is to create the Foundry Agent. In a previous article, I shared how to create a `prompt agent` on the Foundry platform, and the overall process is not complicated.

However, because today's purchase-order agent needs to call external tools, we first need to introduce an important capability: `Foundry Connection`. It mainly serves two purposes:

- `Manage tool endpoints`: each tool has its own access endpoint. If the agent manages all of these directly, things can quickly become messy. By handing them over to `connection`, these details become transparent to the agent.
- `Manage authentication information`: each tool usually has authentication data such as an API key. Storing that information in `connection` reduces the risk of exposing sensitive credentials to the agent.

For example, we can create a connection for `Place Order API` with the following Bicep file:

```yaml
resource placeOrderAPIConnection 'Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview' = {
  name: 'PlaceOrderAPI'
  parent: aiFoundry
  properties: {
    category: 'CustomKeys'
    authType: 'CustomKeys'
    target: '${apimService.properties.gatewayUrl}/${placeOrderAPIPath}'
    isSharedToAll: true
    credentials: {
      keys: {
        'api-key': apimSubscription.listSecrets().primaryKey
      }
    }
  }
}
```

The `target` field above points to the `Place Order API` endpoint exposed by the Gateway, and `credentials` contains the subscription key provided by APIM for authentication.

Using the same approach, we can create `connection` resources for other tools as well:

![[Pasted image 20260625153653.png]]

Then, when we create the agent, we can directly use the `connection` as part of the tool authentication configuration, as shown below:

```python
import json

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
project_client = AIProjectClient(endpoint=foundry_project_endpoint, credential=credential)
openai_client = project_client.get_openai_client()

prompt_content = "List the available smartphones in the catalog and place an order for one of each for me and my 10 friends."

# Load OpenAPI specifications
with open("./product-catalog-openapi.json", "r") as f:
    openapi_product_catalog = json.loads(
        f.read().replace(
            "https://replace-me.local/catalogservice",
            f"{apim_resource_gateway_url}/catalogservice",
        )
    )

with open("./place-order-openapi.json", "r") as f:
    openapi_place_order = json.loads(
        f.read().replace(
            "https://replace-me.local/orderservice",
            f"{apim_resource_gateway_url}/orderservice",
        )
    )

# Initialize agent OpenAPI tools using dictionary-based definitions
product_catalog_tool = {
    "type": "openapi",
    "openapi": {
        "name": "get_product_catalog",
        "description": "Retrieve the list of products available in the catalog",
        "spec": openapi_product_catalog,
        "auth": {
            "type": "project_connection",
            "security_scheme": {
                "project_connection_id": project_client.connections.get("ProductCatalogAPI").id
            },
        },
    },
}

place_order_tool = {
    "type": "openapi",
    "openapi": {
        "name": "place_order",
        "description": "Place a product order",
        "spec": openapi_place_order,
        "auth": {
            "type": "project_connection",
            "security_scheme": {
                "project_connection_id": project_client.connections.get("PlaceOrderAPI").id
            },
        },
    },
}

# Create agent with chained context managers
orders_agent = project_client.agents.create_version(
    agent_name="my-orders-agent",
    definition=PromptAgentDefinition(
        model=str(models_config[0].get("name")),
        instructions="You are a helpful sales assistant that helps users order products. Recover from errors if any and place multiple orders if needed.",
        tools=[product_catalog_tool, place_order_tool],
    ),
    description="You are a helpful sales assistant.",
)

utils.print_ok(
    f"Created agent (id: {orders_agent.id}, name: {orders_agent.name}, version: {orders_agent.version})"
)

conversation_id = openai_client.conversations.create().id
utils.print_ok(f"Created conversation, ID: {conversation_id}")

print(f"\n🗨️ User: {prompt_content}")
response = openai_client.responses.create(
    input=[{"role": "user", "content": prompt_content}],
    conversation=conversation_id,
    extra_body={"agent_reference": {"name": orders_agent.name, "type": "agent_reference"}},
)

print(f"\n🗨️ Agent: {response.output_text}")

# print("\nCleaning up...")
# project_client.agents.delete_version(agent_name=orders_agent.name, agent_version=orders_agent.version)
# utils.print_ok("Agent deleted")
```

In this process, the following configuration adds `Place Order API` into the agent's toolset. As you can see, its `auth` section directly uses the `connection` we created earlier, so there is no need to embed credentials explicitly:

```python
place_order_tool = {
    "type": "openapi",
    "openapi": {
        "name": "place_order",
        "description": "Place a product order",
        "spec": openapi_place_order,
        "auth": {
            "type": "project_connection",
            "security_scheme": {
                "project_connection_id": project_client.connections.get("PlaceOrderAPI").id
            },
        },
    },
}
```

## Demo

Now, let's take a look at how the agent actually works:

![[Pasted image 20260625162005.png]]

## Summary

The most important takeaway from this article is the value of a classic architecture pattern like API Gateway for AI Agent tool harness. Because of space limits, I only focused on the overall design in this post. In future articles, I will continue to share how we can use Gateway policies to truly harness tool behavior in practice.

---

I am Chris Bao, a Microsoft Certified Trainer focused on the Azure AI platform. I specialize in Azure AI services and agent development, and I provide training and consulting services for both enterprises and individuals.

For collaboration, please contact: baoqger@gmail.com
