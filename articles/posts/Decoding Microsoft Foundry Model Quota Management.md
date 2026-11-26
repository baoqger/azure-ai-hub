---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - FinOps
title: Decoding Microsoft Foundry Model Quota Management
---
## Background

Microsoft Foundry provides many different large language models for us to use, which is very convenient. But there is one limitation that is often ignored: `quota`.

In this article, I will share what I learned about the model quota mechanism in Foundry. After reading this post, you can understand how quota is calculated and how to troubleshoot related issues when model deployment fails.

![[Decoding_AI_Model_Quota_Management.png]]
## Model Quota

##### Quota Unit

Because large language models are usually billed by token usage, model quota is also managed based on tokens. In Foundry, quota is commonly represented by `Tokens Per Minute (TPM)`, which means the number of tokens that can be processed per minute.

##### Quota Scope

In Foundry, model quota is not calculated by tenant. Instead, it is calculated based on the following four dimensions: `subscription`, `region`, `model`, and `deployment type`.

- Subscription: This is easy to understand. An Azure Subscription is the unit used to manage and bill cloud resources.
- Region: This represents the physical location of the datacenter.
- Model: The different models available in Foundry.
- Deployment type: This represents how Azure deploys the model. It directly affects performance and cost after the model is deployed. Typical deployment types include `Standard`, `GlobalStandard`, `Provisioned`, and so on.

The quota scope of a model is determined by these four dimensions together. For example, under my subscription, I want to deploy the gpt-4.1 model in the eastus2 region with the GlobalStandard deployment type. Suppose I have two Foundry Projects: `project1` and `project2`. If I deploy one gpt-4.1 model in each project, these two deployments share the same quota.

Similarly, if I deploy a gpt-4.1 model in the `eastasia` region, its quota is counted separately. In the same way, if I deploy the gpt-5.1 model in the `eastus2` region, its quota is also counted separately.

##### Quota Tier

Foundry defines a `quota tier` for each user subscription. This tier directly determines the upper limit of the quota. There are 7 tiers in total: from Tier1 to Tier6, plus a Free Tier.

You can use the following script to check your quota tier:

```python
import requests
import json
from azure.identity import DefaultAzureCredential

subscriptionId = "{YOUR-SUBSCRIPTION-ID}"
api_version = "2025-10-01-preview"
base_url = "https://management.azure.com"

token_credential = DefaultAzureCredential()
token = token_credential.get_token('https://management.azure.com/.default')
headers = {
    'Authorization': 'Bearer ' + token.token,
    'Content-Type': 'application/json'
}

list_url = (
    f"{base_url}/subscriptions/{subscriptionId}"
    f"/providers/Microsoft.CognitiveServices/quotaTiers"
    f"?api-version={api_version}"
)

response = requests.get(list_url, headers=headers)
print(json.dumps(response.json(), indent=2))
```

For example, I am using a personal account, so my subscription is in the Free Tier. This is the most basic tier. Because of that, the quota is relatively low, and some models cannot be used at all. We can prove this with the following Azure CLI command:

```shell
az cognitiveservices usage list --location eastus2 --query "[?contains(name.value, 'OpenAI')].{Quota:name.value, Used:currentValue, Limit:limit}" -o table
```

The following script shows the Foundry quota usage in the `eastus2` region:

```powershell
$targets = @(
  "OpenAI.GlobalStandard.gpt-5-mini",
  "OpenAI.GlobalStandard.o4-mini",
  "OpenAI.GlobalStandard.text-embedding-3-small",
  "OpenAI.GlobalStandard.gpt4.1",
  "OpenAI.GlobalStandard.gpt4.1-mini",
  "OpenAI.GlobalStandard.gpt-5",
  "OpenAI.GlobalStandard.gpt-5-pro",
  "OpenAI.GlobalStandard.gpt-5.1",
  "OpenAI.GlobalStandard.gpt-5.4",
  "OpenAI.GlobalStandard.gpt-5.5"
)

az cognitiveservices usage list --location eastus2 -o json |
ConvertFrom-Json |
Where-Object { $targets -contains $_.name.value } |
Select-Object `
  @{Name="Quota";Expression={$_.name.value}},
  @{Name="Used";Expression={$_.currentValue}},
  @{Name="Limit";Expression={$_.limit}},
  @{Name="Available";Expression={$_.limit - $_.currentValue}},
  @{Name="Status";Expression={
    if ($_.limit -eq 0) { "Not supported / no quota" }
    elseif ($_.currentValue -ge $_.limit) { "Supported but fully used" }
    else { "Supported with available quota" }
  }} |
Format-Table -AutoSize
```

The output looks like this:

```plain
Quota                                      Used    Limit   Available   Status
-----                                      ----    -----   ---------   ------
OpenAI.GlobalStandard.gpt-5-mini          0       500     500         Supported with available quota
OpenAI.GlobalStandard.o4-mini             0       100     100         Supported with available quota
OpenAI.GlobalStandard.text-embedding-3-small 0    1000    1000        Supported with available quota
OpenAI.GlobalStandard.gpt4.1              525     525     0           Supported but fully used
OpenAI.GlobalStandard.gpt4.1-mini         2500    2500    0           Supported but fully used
OpenAI.GlobalStandard.gpt-5               0       0       0           Not supported / no quota
OpenAI.GlobalStandard.gpt-5-pro           0       0       0           Not supported / no quota
```

From this result, we can see that some newer high-end models are not supported under this subscription.

Next, let's examine how quota is allocated for models that are supported.

## Deployment Quota vs Shared Quota

First, deploying a model in a Foundry project is called a `Deployment`. For this model deployment, you can define its quota. This is called Deployment Quota.

In addition, based on the quota calculation method described above, the overall quota bucket is called Shared Quota.

![[Pasted image 20260715143804.png]]

For example, in the gpt-4.1 deployment shown above, the deployment quota is `50K TPM`, while the total quota is `525K TPM`. This means you can still continue deploying this model in the same region.

## Releasing Quota

When the Shared Quota of a model reaches the upper limit, you cannot continue deploying that model. Of course, you can switch to another region, or deploy a different model in the same region.

But this also means that once a resource is no longer needed, we should release it in time to avoid wasting quota.

For example, the following command:

```shell
az cognitiveservices usage list --location eastus2 `
   --query "[?name.value=='OpenAI.GlobalStandard.gpt4.1'].{Quota:name.value, Used:currentValue, Limit:limit}" `
   -o table
```

can read the usage status of the gpt-4.1 model in the eastus2 region:

```plain
Quota                         Used    Limit
----------------------------  ------  -------
OpenAI.GlobalStandard.gpt4.1  525.0   525.0
```

We can see that it has reached the upper limit.

More specifically, the following two projects each deployed one gpt-4.1 model and used up all the quota.

First, let's look at the `chris-rag-time-resource` project:

```shell
az cognitiveservices account deployment show `
  --resource-group rg-chris-rag-time `
  --name chris-rag-time-resource `
  --deployment-name gpt-4.1 `
  --query "{Deployment:name, Model:properties.model.name, Version:properties.model.version, SKU:sku.name, Capacity:sku.capacity}" `
  -o table
```

We can see that it consumes 50K TPM of quota.

```plain
Deployment    Model    Version     SKU             Capacity
------------  -------  ----------  --------------  ----------
gpt-4.1       gpt-4.1  2025-04-14  GlobalStandard  50
```

Next, let's look at another project, `content-understanding-chris`:

```shell
az cognitiveservices account deployment show `
  --resource-group doc-intelligence-chris `
  --name content-understanding-chris `
  --deployment-name gpt-4.1 `
  --query "{Deployment:name, Model:properties.model.name, Version:properties.model.version, SKU:sku.name, Capacity:sku.capacity}" `
  -o table
```

It consumes all the remaining quota, which is 475K TPM.

```plain
Deployment    Model    Version     SKU             Capacity
------------  -------  ----------  --------------  ----------
gpt-4.1       gpt-4.1  2025-04-14  GlobalStandard  475
```

At this point, we need to delete resources to release the corresponding quota.

Here we need to pay attention to one thing: when deleting resources on Azure, there are two operations: `soft delete` and `hard delete`. After `soft delete` deletes a resource, Azure still keeps it for a period of time to protect you from accidental operations. `hard delete`, on the other hand, truly removes the resource completely. This design is similar to the recycle bin mechanism in Windows. Smart design, right?

For model quota, before `hard delete`, the quota is not released. Although you may no longer see the corresponding project, the quota is still there.

So, by running the following two commands:

```shell
az cognitiveservices account delete --resource-group doc-intelligence-chris --name content-understanding-chris
az cognitiveservices account purge --resource-group doc-intelligence-chris --name content-understanding-chris --location eastus2
```

we can fully release the quota. After that, we check the status again, and the result is:

```plain
Quota                         Used    Limit
----------------------------  ------  -------
OpenAI.GlobalStandard.gpt4.1  50.0    525.0
```
