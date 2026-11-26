---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - FinOps
title: Microsoft Foundry Quota Tier Hands-on Test - Free Tier vs Tier 3 Gap Is Larger Than I Expected
---
## Background

In a previous article, I shared some notes about the `quota` of large model resources on Microsoft Foundry.

That article was more about the conceptual side. In this post, I will use my own Azure accounts to do a hands-on comparison and see what the differences between different Quota Tiers really look like.

![[Cloud_Quota_Tier_Comparison.png]]
## How To Check The Quota Tier Of Your Current Subscription

As I mentioned before, large model resources on Foundry are divided into different Quota Tiers: `Free Tier`, and `Tier 1` through `Tier 6`. So there are seven levels in total.

We can use the following script to check which tier your subscription belongs to:

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

I usually use two Azure Subscriptions. One is my personal account. After I became a Microsoft Certified Trainer (MCT), I got 150 USD of monthly credit. The other one is my employee account from my current company. Because it has a Visual Studio Enterprise subscription, it also gets 150 USD of monthly credit. The company's production products run in a separate subscription, so they are not related to my employee account.

At first, I assumed that since both accounts were credit-based, the model `quota` on Foundry should be similar. I checked it with a try-it-and-see mindset, and the result surprised me quite a bit.

My personal account is, as expected, `Free Tier`. But my enterprise employee account is actually `Tier 3`.

Next, we can use the following Azure CLI command to check the OpenAI resource quota for a subscription in a specific region:

```shell
az login --tenant my-tenant-id
az cognitiveservices usage list --location eastus2 --query "[?contains(name.value, 'OpenAI')].{Quota:name.value, Used:currentValue, Limit:limit}" -o table
```

With this command, we can see the model resources available on Foundry for that subscription.

In the following section, let's compare `Free Tier` and `Tier 3` directly. Let me put the conclusion first: the gap is very obvious.

## Free Tier vs Tier 3

### Free Tier

The restrictions of `Free Tier` are quite strict. For example, it does not even include `gpt-5`, which has been available for more than a year. I can only see `gpt-5-mini`. This creates a very real limitation for some development scenarios. Because `gpt-5-mini` does not support `shell`, when I wanted to build an `agent harness` that requires shell access, I could not really move forward with it.

Also, even for the models that are available, the `quota` is very limited.

```plain
Quota                                               Used    Limit
--------------------------------------------------  ------  -------
OpenAI.ProvisionedManaged                           0.0     0.0
OpenAI.GlobalProvisionedManaged                     0.0     0.0
OpenAI.FineTuned.Deployments                        0.0     10.0
OpenAI.S0.AccountCount                              0.0     30.0
OpenAI.Standard.whisper                             0.0     3.0
OpenAI.DataZoneProvisionedManaged                   0.0     0.0
OpenAI.Standard.gpt-35-turbo                        0.0     0.0
OpenAI.Standard.gpt-35-turbo-finetune               0.0     0.0
OpenAI.Standard.gpt-35-turbo-1106-finetune          0.0     0.0
OpenAI.Standard.gpt-35-turbo-0125-finetune          0.0     0.0
OpenAI.GlobalBatch.gpt-35-turbo                     0.0     0.0
OpenAI.Standard.gpt-4                               0.0     0.0
OpenAI.Standard.gpt-4-turbo                         0.0     0.0
OpenAI.GlobalStandard.gpt-4-turbo-2024-0409         0.0     0.0
OpenAI.Standard.gpt-4o-finetune                     0.0     0.0
OpenAI.GlobalStandard.gpt-4o-finetune               0.0     0.0
OpenAI.DataZoneStandard.gpt-4o-finetune             0.0     0.0
OpenAI.GlobalStandard.gpt-4o-mini-finetune          0.0     0.0
OpenAI.DataZoneStandard.gpt-4o-mini-finetune        0.0     0.0
OpenAI.GlobalBatch.gpt-4                            0.0     0.0
OpenAI.GlobalBatch.gpt-4-turbo                      0.0     0.0
OpenAI.GlobalBatch.gpt-4o                           0.0     0.0
OpenAI.GlobalBatch.gpt-4o-mini                      0.0     0.0
OpenAI.Provisioned.gpt-4o-audio-preview             0.0     0.0
OpenAI.Standard.gpt-4o                              0.0     0.0
OpenAI.Standard.gpt-4o-mini                         0.0     0.0
OpenAI.GlobalStandard.gpt-4o                        50.0    50.0
OpenAI.GlobalStandard.gpt-4o-mini                   100.0   100.0
OpenAI.GlobalStandard.gpt-4o-realtime-preview       0.0     0.0
OpenAI.GlobalStandard.gpt-4o-mini-realtime-preview  0.0     0.0
OpenAI.GlobalStandard.gpt-4o-audio-preview          0.0     0.0
OpenAI.GlobalStandard.gpt-4o-mini-audio-preview     0.0     0.0
OpenAI.DataZoneStandard.gpt-4o                      0.0     0.0
OpenAI.DataZoneStandard.gpt-4o-mini                 0.0     0.0
OpenAI.DataZoneBatch.gpt-4o                         0.0     0.0
OpenAI.DataZoneBatch.gpt-4o-mini                    0.0     0.0
OpenAI.GlobalStandard.gpt-4o-transcribe             0.0     400.0
OpenAI.DataZoneStandard.gpt-4o-transcribe           0.0     400.0
OpenAI.GlobalStandard.gpt-4o-mini-transcribe        0.0     50.0
OpenAI.GlobalStandard.gpt-4o-mini-tts               0.0     50.0
OpenAI.Standard.text-embedding-ada-002              0.0     350.0
OpenAI.GlobalStandard.text-embedding-ada-002        0.0     0.0
OpenAI.DataZoneStandard.text-embedding-ada-002      0.0     0.0
OpenAI.Standard.text-embedding-3-small              0.0     350.0
OpenAI.Standard.text-embedding-3-large              0.0     350.0
OpenAI.GlobalStandard.text-embedding-3-small        0.0     1000.0
OpenAI.GlobalStandard.text-embedding-3-large        500.0   750.0
OpenAI.DataZoneStandard.text-embedding-3-small      0.0     1000.0
OpenAI.DataZoneStandard.text-embedding-3-large      0.0     0.0
OpenAI.Standard.o1                                  0.0     0.0
OpenAI.GlobalStandard.o1                            0.0     0.0
OpenAI.GlobalStandard.o1-mini                       0.0     0.0
OpenAI.DataZoneStandard.o1                          0.0     0.0
OpenAI.GlobalStandard.o3-mini                       0.0     0.0
OpenAI.GlobalStandard.o3                            0.0     0.0
OpenAI.GlobalBatch.o3                               0.0     0.0
OpenAI.DataZoneBatch.o3                             0.0     0.0
OpenAI.GlobalBatch.o3-mini                          0.0     0.0
OpenAI.DataZoneBatch.o3-mini                        0.0     0.0
OpenAI.DataZoneStandard.o3                          0.0     0.0
OpenAI.DataZoneStandard.o3-mini                     0.0     0.0
OpenAI.GlobalStandard.ModelRouter                   0.0     10.0
OpenAI.DataZoneStandard.ModelRouter                 0.0     10.0
OpenAI.GlobalStandard.ModelRouter-finetune          0.0     10.0
OpenAI.GlobalStandard.codex-mini                    0.0     0.0
OpenAI.Standard.sora                                0.0     60.0
OpenAI.GlobalStandard.sora                          0.0     60.0
OpenAI.GlobalStandard.sora-2                        0.0     0.0
OpenAI.GlobalStandard.o4-mini                       0.0     100.0
OpenAI.Standard.o4-mini                             0.0     0.0
OpenAI.GlobalStandard.o4-mini-finetune              0.0     500.0
OpenAI.DataZoneStandard.o4-mini-finetune            0.0     500.0
OpenAI.DeveloperTier.o4-mini-finetune               0.0     250.0
OpenAI.Standard.o4-mini-finetune                    0.0     500.0
OpenAI.GlobalBatch.o4-mini                          0.0     0.0
OpenAI.DataZoneBatch.o4-mini                        0.0     0.0
OpenAI.DataZoneStandard.o4-mini                     0.0     0.0
OpenAI.GlobalStandard.gpt4.1                        287.0   525.0
OpenAI.Standard.gpt4.1                              0.0     0.0
OpenAI.DataZoneStandard.gpt4.1                      0.0     0.0
OpenAI.GlobalStandard.gpt4.1-finetune               0.0     250.0
OpenAI.DeveloperTier.gpt4.1-finetune                0.0     250.0
OpenAI.GlobalStandard.gpt4.1-mini-finetune          0.0     500.0
OpenAI.DataZoneStandard.gpt4.1-mini-finetune        0.0     500.0
OpenAI.DeveloperTier.gpt4.1-mini-finetune           0.0     500.0
OpenAI.GlobalStandard.gpt4.1-nano-finetune          0.0     500.0
OpenAI.DataZoneStandard.gpt4.1-nano-finetune        0.0     500.0
OpenAI.DeveloperTier.gpt4.1-nano-finetune           0.0     500.0
OpenAI.GlobalStandard.gpt4.1-mini                   0.0     2500.0
OpenAI.Standard.gpt4.1-mini                         0.0     0.0
OpenAI.GlobalBatch.gpt-4.1-mini                     0.0     90.0
OpenAI.DataZoneStandard.gpt4.1-mini                 0.0     0.0
OpenAI.GlobalStandard.gpt4.1-nano                   0.0     0.0
OpenAI.DataZoneStandard.gpt4.1-nano                 0.0     0.0
OpenAI.GlobalBatch.gpt-4.1                          0.0     90.0
OpenAI.DataZoneBatch.gpt-4.1                        0.0     90.0
OpenAI.GlobalBatch.gpt-4.1-nano                     0.0     90.0
OpenAI.DataZoneBatch.gpt-4.1-mini                   0.0     90.0
OpenAI.DataZoneBatch.gpt-4.1-nano                   0.0     90.0
OpenAI.GlobalStandard.gpt-image-1                   0.0     0.0
OpenAI.GlobalStandard.gpt-image-1-mini              0.0     0.0
OpenAI.GlobalStandard.gpt-5                         0.0     0.0
OpenAI.GlobalStandard.gpt-5-chat                    0.0     0.0
OpenAI.GlobalStandard.gpt-5-mini                    250.0   500.0
OpenAI.GlobalStandard.gpt-5-nano                    0.0     0.0
OpenAI.DataZoneStandard.gpt-5                       0.0     0.0
OpenAI.DataZoneStandard.gpt-5-mini                  0.0     0.0
OpenAI.DataZoneStandard.gpt-5-nano                  0.0     0.0
OpenAI.GlobalStandard.gpt-5-pro                     0.0     0.0
OpenAI.GlobalBatch.gpt-5                            0.0     0.0
OpenAI.DataZoneBatch.gpt-5                          0.0     0.0
OpenAI.GlobalStandard.gpt-audio                     0.0     0.0
OpenAI.GlobalStandard.gpt-realtime                  0.0     0.0
OpenAI.GlobalStandard.gpt-5-codex                   0.0     0.0
OpenAI.GlobalStandard.gpt-audio-mini                0.0     30.0
OpenAI.GlobalStandard.gpt-realtime-mini             0.0     40.0
OpenAI.GlobalStandard.gpt-4o-transcribe-diarize     0.0     400.0
OpenAI.Standard.gpt-5.1                             0.0     0.0
OpenAI.GlobalStandard.gpt-5.1                       0.0     0.0
OpenAI.DataZoneStandard.gpt-5.1                     0.0     0.0
OpenAI.GlobalBatch.gpt-5.1                          0.0     0.0
OpenAI.DataZoneBatch.gpt-5.1                        0.0     0.0
OpenAI.GlobalStandard.gpt-5.1-chat                  0.0     0.0
OpenAI.GlobalStandard.gpt-5.1-codex                 0.0     0.0
OpenAI.GlobalStandard.gpt-5.1-codex-mini            0.0     0.0
OpenAI.GlobalStandard.gpt-5.1-codex-max             0.0     0.0
OpenAI.GlobalStandard.gpt-5.2                       0.0     0.0
OpenAI.DataZoneStandard.gpt-5.2                     0.0     0.0
OpenAI.GlobalStandard.gpt-5.2-chat                  0.0     0.0
OpenAI.GlobalStandard.gpt-image-1.5                 0.0     0.0
OpenAI.DataZoneStandard.gpt-image-1.5               0.0     0.0
OpenAI.GlobalStandard.gpt-5.2-codex                 0.0     0.0
OpenAI.GlobalStandard.gpt-audio-1.5                 0.0     0.0
OpenAI.GlobalStandard.gpt-realtime-1.5              0.0     0.0
OpenAI.DataZoneStandard.gpt-realtime-1.5            0.0     0.0
OpenAI.GlobalStandard.gpt-5.3-codex                 0.0     0.0
OpenAI.DataZoneStandard.gpt-5.3-codex               0.0     0.0
OpenAI.GlobalStandard.gpt-5.4                       0.0     0.0
OpenAI.DataZoneStandard.gpt-5.4                     0.0     0.0
OpenAI.GlobalBatch.gpt-5.4                          0.0     0.0
OpenAI.DataZoneBatch.gpt-5.4                        0.0     0.0
OpenAI.GlobalStandard.gpt-5.3-chat                  0.0     0.0
OpenAI.GlobalStandard.gpt-5.4-pro                   0.0     0.0
OpenAI.GlobalStandard.gpt-5.4-mini                  0.0     0.0
OpenAI.GlobalBatch.gpt-5.4-mini                     0.0     0.0
OpenAI.DataZoneBatch.gpt-5.4-mini                   0.0     0.0
OpenAI.DataZoneStandard.gpt-5.4-mini                0.0     0.0
OpenAI.GlobalStandard.gpt-5.4-nano                  0.0     0.0
OpenAI.DataZoneStandard.gpt-5.4-nano                0.0     0.0
OpenAI.GlobalStandard.gpt-image-2                   0.0     0.0
OpenAI.GlobalStandard.gpt-5.5                       0.0     0.0
OpenAI.DataZoneStandard.gpt-5.5                     0.0     0.0
OpenAI.GlobalStandard.gpt-chat-latest               0.0     0.0
OpenAI.GlobalStandard.gpt-realtime-translate        0.0     0.0
OpenAI.GlobalStandard.gpt-realtime-whisper          0.0     0.0
OpenAI.GlobalStandard.gpt-realtime-2                0.0     0.0
OpenAI.DataZoneStandard.gpt-realtime-2              0.0     0.0
OpenAI.GlobalStandard.gpt-5.6-luna                  0.0     0.0
OpenAI.GlobalStandard.gpt-5.6-terra                 0.0     0.0
OpenAI.GlobalStandard.gpt-5.6-sol                   0.0     0.0
OpenAI.DataZoneStandard.gpt-5.6-sol                 0.0     0.0
OpenAI.GlobalStandard.gpt-realtime-2.1-mini         0.0     0.0
OpenAI.GlobalStandard.gpt-realtime-2.1              0.0     0.0
OpenAI.DataZoneStandard.gpt-realtime-2.1            0.0     0.0
OpenAI.DataZoneStandard.gpt-5.6-luna                0.0     0.0
OpenAI.DataZoneStandard.gpt-5.6-terra               0.0     0.0
OpenAI.GlobalStandard.gpt-live-transcribe           0.0     0.0
OpenAI.GlobalStandard.gpt-transcribe                0.0     0.0
```

### Tier 3

In contrast, the experience of `Tier 3` is much more generous. It not only includes the latest `gpt-5.6` model family, but also includes more advanced multimodal models, such as `gpt-image-2`.

```plain
Quota                                               Used    Limit
--------------------------------------------------  ------  -------
OpenAI.ProvisionedManaged                           0.0     150.0
OpenAI.GlobalProvisionedManaged                     0.0     300.0
OpenAI.FineTuned.Deployments                        0.0     10.0
OpenAI.S0.AccountCount                              0.0     30.0
OpenAI.Standard.whisper                             0.0     3.0
OpenAI.DataZoneProvisionedManaged                   0.0     150.0
OpenAI.Standard.gpt-35-turbo                        0.0     0.0
OpenAI.Standard.gpt-35-turbo-finetune               0.0     0.0
OpenAI.Standard.gpt-35-turbo-1106-finetune          0.0     0.0
OpenAI.Standard.gpt-35-turbo-0125-finetune          0.0     0.0
OpenAI.GlobalBatch.gpt-35-turbo                     0.0     0.0
OpenAI.Standard.gpt-4                               0.0     0.0
OpenAI.Standard.gpt-4-turbo                         0.0     0.0
OpenAI.GlobalStandard.gpt-4-turbo-2024-0409         0.0     1200.0
OpenAI.Standard.gpt-4o-finetune                     0.0     0.0
OpenAI.GlobalStandard.gpt-4o-finetune               0.0     0.0
OpenAI.DataZoneStandard.gpt-4o-finetune             0.0     0.0
OpenAI.GlobalStandard.gpt-4o-mini-finetune          0.0     0.0
OpenAI.DataZoneStandard.gpt-4o-mini-finetune        0.0     0.0
OpenAI.GlobalBatch.gpt-4                            0.0     0.0
OpenAI.GlobalBatch.gpt-4-turbo                      0.0     0.0
OpenAI.GlobalBatch.gpt-4o                           0.0     0.0
OpenAI.GlobalBatch.gpt-4o-mini                      0.0     0.0
OpenAI.Provisioned.gpt-4o-audio-preview             0.0     0.0
OpenAI.Standard.gpt-4o                              0.0     0.0
OpenAI.Standard.gpt-4o-mini                         0.0     0.0
OpenAI.GlobalStandard.gpt-4o                        0.0     7000.0
OpenAI.GlobalStandard.gpt-4o-mini                   10.0    99000.0
OpenAI.GlobalStandard.gpt-4o-realtime-preview       0.0     6.0
OpenAI.GlobalStandard.gpt-4o-mini-realtime-preview  0.0     6.0
OpenAI.GlobalStandard.gpt-4o-audio-preview          0.0     30000.0
OpenAI.GlobalStandard.gpt-4o-mini-audio-preview     0.0     30000.0
OpenAI.DataZoneStandard.gpt-4o                      0.0     3000.0
OpenAI.DataZoneStandard.gpt-4o-mini                 0.0     7000.0
OpenAI.DataZoneBatch.gpt-4o                         0.0     0.0
OpenAI.DataZoneBatch.gpt-4o-mini                    0.0     0.0
OpenAI.GlobalStandard.gpt-4o-transcribe             0.0     400.0
OpenAI.DataZoneStandard.gpt-4o-transcribe           0.0     400.0
OpenAI.GlobalStandard.gpt-4o-mini-transcribe        0.0     600.0
OpenAI.GlobalStandard.gpt-4o-mini-tts               0.0     600.0
OpenAI.Standard.text-embedding-ada-002              0.0     350.0
OpenAI.GlobalStandard.text-embedding-ada-002        0.0     4000.0
OpenAI.DataZoneStandard.text-embedding-ada-002      0.0     4000.0
OpenAI.Standard.text-embedding-3-small              0.0     350.0
OpenAI.Standard.text-embedding-3-large              0.0     350.0
OpenAI.GlobalStandard.text-embedding-3-small        0.0     4000.0
OpenAI.GlobalStandard.text-embedding-3-large        2000.0  12000.0
OpenAI.DataZoneStandard.text-embedding-3-small      0.0     4000.0
OpenAI.DataZoneStandard.text-embedding-3-large      0.0     4000.0
OpenAI.Standard.o1                                  0.0     0.0
OpenAI.GlobalStandard.o1                            0.0     2000.0
OpenAI.GlobalStandard.o1-mini                       0.0     2000.0
OpenAI.DataZoneStandard.o1                          0.0     450.0
OpenAI.GlobalStandard.o3-mini                       0.0     2000.0
OpenAI.GlobalStandard.o3                            0.0     4000.0
OpenAI.GlobalBatch.o3                               0.0     0.0
OpenAI.DataZoneBatch.o3                             0.0     0.0
OpenAI.GlobalBatch.o3-mini                          0.0     0.0
OpenAI.DataZoneBatch.o3-mini                        0.0     0.0
OpenAI.DataZoneStandard.o3                          0.0     1000.0
OpenAI.DataZoneStandard.o3-mini                     0.0     900.0
OpenAI.GlobalStandard.ModelRouter                   0.0     4000.0
OpenAI.DataZoneStandard.ModelRouter                 0.0     1000.0
OpenAI.GlobalStandard.ModelRouter-finetune          0.0     600.0
OpenAI.GlobalStandard.codex-mini                    0.0     4000.0
OpenAI.Standard.sora                                0.0     60.0
OpenAI.GlobalStandard.sora                          0.0     60.0
OpenAI.GlobalStandard.sora-2                        0.0     30.0
OpenAI.GlobalStandard.o4-mini                       0.0     4000.0
OpenAI.Standard.o4-mini                             0.0     0.0
OpenAI.GlobalStandard.o4-mini-finetune              0.0     500.0
OpenAI.DataZoneStandard.o4-mini-finetune            0.0     500.0
OpenAI.DeveloperTier.o4-mini-finetune               0.0     250.0
OpenAI.Standard.o4-mini-finetune                    0.0     500.0
OpenAI.GlobalBatch.o4-mini                          0.0     0.0
OpenAI.DataZoneBatch.o4-mini                        0.0     0.0
OpenAI.DataZoneStandard.o4-mini                     0.0     1000.0
OpenAI.GlobalStandard.gpt4.1                        9000.0  27000.0
OpenAI.Standard.gpt4.1                              0.0     0.0
OpenAI.DataZoneStandard.gpt4.1                      0.0     3000.0
OpenAI.GlobalStandard.gpt4.1-finetune               0.0     250.0
OpenAI.DeveloperTier.gpt4.1-finetune                0.0     250.0
OpenAI.GlobalStandard.gpt4.1-mini-finetune          0.0     500.0
OpenAI.DataZoneStandard.gpt4.1-mini-finetune        0.0     500.0
OpenAI.DeveloperTier.gpt4.1-mini-finetune           0.0     500.0
OpenAI.GlobalStandard.gpt4.1-nano-finetune          0.0     500.0
OpenAI.DataZoneStandard.gpt4.1-nano-finetune        0.0     500.0
OpenAI.DeveloperTier.gpt4.1-nano-finetune           0.0     500.0
OpenAI.GlobalStandard.gpt4.1-mini                   0.0     46000.0
OpenAI.Standard.gpt4.1-mini                         0.0     0.0
OpenAI.GlobalBatch.gpt-4.1-mini                     0.0     90.0
OpenAI.DataZoneStandard.gpt4.1-mini                 0.0     16000.0
OpenAI.GlobalStandard.gpt4.1-nano                   0.0     46000.0
OpenAI.DataZoneStandard.gpt4.1-nano                 0.0     16000.0
OpenAI.GlobalBatch.gpt-4.1                          0.0     90.0
OpenAI.DataZoneBatch.gpt-4.1                        0.0     90.0
OpenAI.GlobalBatch.gpt-4.1-nano                     0.0     90.0
OpenAI.DataZoneBatch.gpt-4.1-mini                   0.0     90.0
OpenAI.DataZoneBatch.gpt-4.1-nano                   0.0     90.0
OpenAI.GlobalStandard.gpt-image-1                   0.0     10.0
OpenAI.GlobalStandard.gpt-image-1-mini              0.0     18.0
OpenAI.GlobalStandard.gpt-5                         0.0     9000.0
OpenAI.GlobalStandard.gpt-5-chat                    0.0     3000.0
OpenAI.GlobalStandard.gpt-5-mini                    0.0     4000.0
OpenAI.GlobalStandard.gpt-5-nano                    0.0     46000.0
OpenAI.DataZoneStandard.gpt-5                       0.0     3000.0
OpenAI.DataZoneStandard.gpt-5-mini                  0.0     1000.0
OpenAI.DataZoneStandard.gpt-5-nano                  0.0     16000.0
OpenAI.GlobalStandard.gpt-5-pro                     0.0     700.0
OpenAI.GlobalBatch.gpt-5                            0.0     0.0
OpenAI.DataZoneBatch.gpt-5                          0.0     0.0
OpenAI.GlobalStandard.gpt-audio                     0.0     30000.0
OpenAI.GlobalStandard.gpt-realtime                  0.0     10.0
OpenAI.GlobalStandard.gpt-5-codex                   0.0     4000.0
OpenAI.GlobalStandard.gpt-audio-mini                0.0     20.0
OpenAI.GlobalStandard.gpt-realtime-mini             0.0     20.0
OpenAI.GlobalStandard.gpt-4o-transcribe-diarize     0.0     400.0
OpenAI.Standard.gpt-5.1                             0.0     1000.0
OpenAI.GlobalStandard.gpt-5.1                       0.0     9000.0
OpenAI.DataZoneStandard.gpt-5.1                     0.0     3000.0
OpenAI.GlobalBatch.gpt-5.1                          0.0     0.0
OpenAI.DataZoneBatch.gpt-5.1                        0.0     0.0
OpenAI.GlobalStandard.gpt-5.1-chat                  0.0     3000.0
OpenAI.GlobalStandard.gpt-5.1-codex                 0.0     4000.0
OpenAI.GlobalStandard.gpt-5.1-codex-mini            0.0     4000.0
OpenAI.GlobalStandard.gpt-5.1-codex-max             0.0     4000.0
OpenAI.GlobalStandard.gpt-5.2                       0.0     9000.0
OpenAI.DataZoneStandard.gpt-5.2                     0.0     3000.0
OpenAI.GlobalStandard.gpt-5.2-chat                  0.0     3000.0
OpenAI.GlobalStandard.gpt-image-1.5                 0.0     30.0
OpenAI.DataZoneStandard.gpt-image-1.5               0.0     10.0
OpenAI.GlobalStandard.gpt-5.2-codex                 0.0     4000.0
OpenAI.GlobalStandard.gpt-audio-1.5                 0.0     30000.0
OpenAI.GlobalStandard.gpt-realtime-1.5              0.0     10.0
OpenAI.DataZoneStandard.gpt-realtime-1.5            0.0     10.0
OpenAI.GlobalStandard.gpt-5.3-codex                 0.0     9000.0
OpenAI.DataZoneStandard.gpt-5.3-codex               0.0     3000.0
OpenAI.GlobalStandard.gpt-5.4                       0.0     4000.0
OpenAI.DataZoneStandard.gpt-5.4                     0.0     1000.0
OpenAI.GlobalBatch.gpt-5.4                          0.0     0.0
OpenAI.DataZoneBatch.gpt-5.4                        0.0     0.0
OpenAI.GlobalStandard.gpt-5.3-chat                  0.0     3000.0
OpenAI.GlobalStandard.gpt-5.4-pro                   0.0     700.0
OpenAI.GlobalStandard.gpt-5.4-mini                  0.0     4000.0
OpenAI.GlobalBatch.gpt-5.4-mini                     0.0     0.0
OpenAI.DataZoneBatch.gpt-5.4-mini                   0.0     0.0
OpenAI.DataZoneStandard.gpt-5.4-mini                0.0     0.0
OpenAI.GlobalStandard.gpt-5.4-nano                  0.0     46000.0
OpenAI.DataZoneStandard.gpt-5.4-nano                0.0     16000.0
OpenAI.GlobalStandard.gpt-image-2                   0.0     6.0
OpenAI.GlobalStandard.gpt-5.5                       0.0     4000.0
OpenAI.DataZoneStandard.gpt-5.5                     0.0     1333.0
OpenAI.GlobalStandard.gpt-chat-latest               0.0     3000.0
OpenAI.GlobalStandard.gpt-realtime-translate        0.0     10.0
OpenAI.GlobalStandard.gpt-realtime-whisper          0.0     10.0
OpenAI.GlobalStandard.gpt-realtime-2                0.0     10.0
OpenAI.DataZoneStandard.gpt-realtime-2              0.0     10.0
OpenAI.GlobalStandard.gpt-5.6-luna                  0.0     4000.0
OpenAI.GlobalStandard.gpt-5.6-terra                 0.0     4000.0
OpenAI.GlobalStandard.gpt-5.6-sol                   0.0     4000.0
OpenAI.DataZoneStandard.gpt-5.6-sol                 0.0     1333.0
OpenAI.GlobalStandard.gpt-realtime-2.1-mini         0.0     10.0
OpenAI.GlobalStandard.gpt-realtime-2.1              0.0     10.0
OpenAI.DataZoneStandard.gpt-realtime-2.1            0.0     10.0
OpenAI.DataZoneStandard.gpt-5.6-luna                0.0     1333.0
OpenAI.DataZoneStandard.gpt-5.6-terra               0.0     1333.0
OpenAI.GlobalStandard.gpt-live-transcribe           0.0     10.0
OpenAI.GlobalStandard.gpt-transcribe                0.0     10.0
```

## Summary

From this comparison, we can see that the Foundry Quota Tier is not just an abstract concept. It directly affects which models can be deployed in a subscription, which deployment forms are available, and what the actual quota limits look like.

For daily learning, lightweight testing, or simple demos, `Free Tier` may still cover some scenarios. But if you want to build more complete Agent applications, run multimodal experiments, or use newer model families, the gap between `Tier 3` and `Free Tier` becomes very clear.

Great, right? Sometimes two subscriptions may look similar from the credit perspective, but the real development experience can be very different once we check the quota tier behind them.

---

I am Chris Bao, a Microsoft Certified Trainer focusing on the Azure AI platform. I specialize in Azure AI services and Agent development, and I provide training and consulting services for both enterprises and individuals.

For collaboration, please contact: baoqger@gmail.com
