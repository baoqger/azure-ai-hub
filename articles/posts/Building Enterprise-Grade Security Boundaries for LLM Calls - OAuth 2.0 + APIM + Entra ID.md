---
date: 2026-10-26
authors:
  - chris-bao
categories:
  - Security
title: Building Enterprise-Grade Security Boundaries for LLM Calls - OAuth 2.0 + APIM + Entra ID
---
## Background

In my previous articles, I shared how to deploy large language models on Azure Foundry and call them successfully. However, there is a more important question that we often overlook: `security` and `access control`. In this article, I want to share what I learned about using `Azure API Management` and `Entra ID` to add `OAuth 2.0`-level authorization to your GenAI application or Agent.

After reading this post, you can understand how to put an authorization boundary in front of an LLM endpoint instead of exposing it directly.

![[Secure_AI_Architecture_Flow_Diagram.png]]

## Architecture Design

![[Pasted image 20260622114200.png]]

This architecture includes the following core components:

- `Foundry` service: used to deploy the GPT model and expose the inference endpoint.
- `API Management` service: wraps the model inference endpoint behind an API Gateway, then applies token validation policies to enforce OAuth-based access control. We will break down the policy details in the following sections.
- `Entra ID` service: on Azure, Entra ID is the core platform for `identity` and `authorization`, and it supports different OAuth 2.0 flows end to end.

##### LLM Deployment

Deploy a `gpt-4o-mini` model in Foundry:

![[Pasted image 20260622123607.png]]

##### App Registration with Entra ID

Before we go deeper, let's quickly review OAuth 2.0 (shortened to OAuth in the rest of this article). The core purpose of OAuth is to let one application get limited access to another application's data or API without sharing the user's password.

Here is a simple way to think about it:

- The user's password is like the key to their house.
- An OAuth access token is like a temporary visitor pass.
- That visitor pass can be restricted to open only certain doors, perform only certain operations, and remain valid only for a limited period of time.

So instead of handing your Microsoft or Google password directly to an application, you sign in on the Microsoft or Google side, and they issue a token to the application. After that, the application can use the token to access the authorized resource.

An OAuth flow usually involves four roles:

- `Resource Owner`: the user.
- `Client`: the application requesting access. In this article, it is the `Python script running in a Jupyter Notebook`.
- `Authorization Server`: the identity provider that issues the token. In this article, it is `Microsoft Entra ID`.
- `Resource Server`: the API being called. In this article, it is `Azure API Management`.

If an application wants to use OAuth for access control, it first needs to be registered with the `Authorization Server`, which then assigns it a `client_id`.

We can complete app registration with the following Azure CLI command:

```shell
az ad app create --display-name access-control-app --is-fallback-public-client true
```

![[Pasted image 20260622124735.png]]

There is one important parameter here: `is-fallback-public-client`. This tells us that we are registering a `public client`. So what is a `public client`? In app registration, besides the `client_id` that identifies the application, we often also have a `client_secret`, which works like the application's own password.

Depending on whether the runtime environment can safely store a `client_secret`, applications can be roughly divided into two categories:

- `confidential client`: can securely store a secret, such as a traditional server-side web application.
- `public client`: cannot safely store a secret, such as a browser-only web app, a native iOS or Android app, or a CLI application. In this article, the Notebook script is similar to a CLI scenario, so it also belongs to the `public client` category.

![[Pasted image 20260609211820.png]]

Different application types use different OAuth authorization flows. In this article, we will use the `Device Code` flow. Let's examine that in the demo section later. If you want more OAuth background, you can also revisit my previous related articles.

##### OAuth Validation Policy in APIM

First, create a `backend` instance to proxy the GPT model inference endpoint:

![[Pasted image 20260622131244.png]]

Next, create an `api` instance. This is where we enforce OAuth validation. After the validation succeeds, the request is forwarded to the `backend` instance above:

![[Pasted image 20260622131503.png]]

The policy configuration looks like this:

![[Pasted image 20260622131608.png]]

The core validation logic is implemented by the `validate-azure-ad-token` node. As we can see, it mainly performs two checks:

- `tenant id`: in this context, the tenant can be mapped to the OAuth `issuer`, which is the token issuer. Since this demo is based on my Azure subscription, the tenant here is the default tenant associated with that subscription.
- `client-application-ids`: this contains the client ID of the application we just registered.

So the policy ultimately validates two things: the token must be issued by the expected tenant or issuer, and it must be issued to the expected client.

Let's verify that with a demo.

## Demo

##### Device Code Flow

![[Pasted image 20260609211955.png]]

Before the demo, let's briefly explain what `Device Code` means. In the scenario above, our client is a Notebook script. In the OAuth model, that makes it a `Public Client`, which cannot safely store a `client_secret`. Because of that, the OAuth `Device Code` flow is a better fit.

The `Device Flow` is designed for applications and devices that cannot easily complete a normal browser redirect flow. It is especially useful for `CLI tools`, terminal applications, scripts, Jupyter notebooks, smart TVs, gaming consoles, and IoT devices.

![[Pasted image 20260609212004.png]]

The idea of `Device Flow` is to move the interactive sign-in step to another device that has a browser available. In our scenario, that means completing the sign-in on the device where Jupyter is running.

1. The client sends a request to the authorization server to start a sign-in flow.
2. The authorization server returns:
   - a `device_code`
   - a shorter `user_code`
   - a `verification URL`
   - a polling interval
3. The user opens the verification URL in a browser on another device.
4. The user enters the `user_code`, signs in, and grants consent.
5. The client keeps polling the token endpoint using the `device_code`.
6. After the user completes the sign-in, the authorization server returns the token to the client.

#### Implementing Device Code Flow with MSAL

Here we use Microsoft's MSAL library to implement the `Device Code` flow, obtain a token, and decode its content:

```python
import base64
import json

import msal

app = msal.PublicClientApplication(
    client_id,
    authority="https://login.microsoftonline.com/" + tenant_id,
)

flow = app.initiate_device_flow(scopes=["User.Read"])

if "user_code" not in flow:
    raise ValueError(
        "Fail to create device flow. Err: %s" % json.dumps(flow, indent=4)
    )

print(flow["message"])

result = app.acquire_token_by_device_flow(flow)

if "access_token" in result:
    access_token = result["access_token"]

    # Calling graph using the access token
    header, payload, signature = access_token.split(".")

    def pad(b):
        return b + "=" * (-len(b) % 4)

    print("Decoded JWT Header and Payload:")
    print(
        json.dumps(
            json.loads(base64.urlsafe_b64decode(pad(header)).decode("utf-8")),
            indent=4,
        )
    )
    print(
        json.dumps(
            json.loads(base64.urlsafe_b64decode(pad(payload)).decode("utf-8")),
            indent=4,
        )
    )
else:
    print(result.get("error"))
    print(result.get("error_description"))
    print(result.get("correlation_id"))  # You may need this when reporting a bug
```

As explained in the previous section, this script first gives you a URL. You only need to open the URL in a browser and enter the generated device code:

![[Pasted image 20260622133746.png|372]]

Next, the user completes authorization so that the `access-controlling-app` application can access the protected resource or API.

![[Pasted image 20260622133905.png|371]]

The returned token is in JWT format and contains a lot of information. Here we only focus on a few key fields:

```plain
"iss": "https://sts.windows.net/xxxxxxxx-ff46-4747-b46a-a84ca8e98fa0/",
"app_displayname": "access-controlling-app",
"appid": "34e82664-380a-4455-aff6-16de6096e022"
```

The `iss` field shows that the token issuer matches my tenant ID. The `appid` and `app_displayname` fields show which application the token was issued to.

Then we use this token to call the endpoint exposed by the API Gateway:

```python
url = f"{apim_resource_gateway_url}/{inference_api_path}/openai/deployments/{models_config[0]['name']}/chat/completions?api-version={inference_api_version}"

messages = {
    "messages": [
        {"role": "system", "content": "You are a sarcastic unhelpful assistant."},
        {"role": "user", "content": "Can you tell me the time, please?"},
    ]
}

response = requests.post(
    url,
    headers={"api-key": api_key, "Authorization": "Bearer " + access_token},
    json=messages,
)

utils.print_response_code(response)

if response.status_code == 200:
    data = json.loads(response.text)
    print(f"💬 {data.get('choices')[0].get('message').get('content')}")
else:
    print(response.text)
```

We can get a successful response like this:

```plain
Response status: 200 - OK 💬 Oh sure, let me just check my crystal ball. But really, isn’t it about time you looked at a clock?
```

For comparison, if we use a default Entra ID user token instead:

```python
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential

credential = DefaultAzureCredential()
token = credential.get_token("https://management.azure.com/.default").token
```

the validation fails:

```plain
Response status: 401 - Unauthorized { "statusCode": 401, "message": "Invalid Azure AD JWT" }
```

This comparison highlights an important point: not every Entra ID token can access a protected LLM API. Only an access token that satisfies the APIM policy checks, is issued by the correct tenant, and is issued to the correct client can pass gateway validation.

## Summary

In this article, I shared a practical way to protect LLM calls with OAuth 2.0 by combining `APIM` and `Entra ID`. The key idea is simple: do not expose your model endpoint directly. Instead, put it behind an authorization boundary and validate whether the incoming token was issued by the correct tenant and for the correct client.

This approach is especially useful when you want to move GenAI applications or Agents into a more production-ready environment. Great, right? In future articles, I may also share more patterns around securing Agent and LLM workloads on Azure.
