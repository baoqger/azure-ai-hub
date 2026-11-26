---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - LLM Fine Tuning
title: Balancing Accuracy, Cost, and Performance - Model Fine-Tuning Practices Based on the Microsoft Foundry Platform
---
### Background 

The agent calls tools to obtain external data or complete certain tasks; this is the most common working mode for the agent.

This mode generally handles simple problems that can be solved with a single (or a few) tool calls quite stably!

However, when the user's inquiries become more complex, can the agent still plan effective tool calls? Can the plans it formulates be executed stably? If not, what improvement solutions are available? Among these solutions, what are the characteristics of the Fine-Tune Model solution? Today, this article will break down the entire issue.

### Introduction

This case fictionalizes a retail brand named **Zava**. This brand offers a customer service AI agent driven by a **Retail MCP server**, which exposes various tools to the outside (such as product search, user inquiries, order details, returns, exchanges, and data updates).

![[Pasted image 20251215205407.png]]

This agent does not use a particularly complex design model; it is driven by the MCP service. However, the system instructions for this agent are indeed very detailed, consisting of nearly 1,800 words. The system instructions summarize various business processes for customer support, such as order inquiries, returns and exchanges, etc. These define the policies for the agent's behavior.

This approach of utilizing advanced large models and finely designed system instructions is the most commonly adopted solution for agents operating in current production environments. This point can be validated by a paper titled 'Measuring Agents in Production' published by UC Berkeley, Stanford, IBM, and others. 

In our agent, it utilizes the `gpt-4.1-mini` large model. For the details of the system prompt, please refer to this Github repo. 

Now, let's take a look at the behavior of this agent. 

### Success Case

First, let's demonstrate that the customer support agent can correctly handle **simple tool calls**. For example, a request like the following:

> 'Can you show me all your products?'

will be interpreted as a correct MCP tool call, producing the expected result.

The agent typically responds as follows:

1. Understands the request as an intention to browse products.
2. Calls the appropriate MCP tool (for example, `list_products`), **without any parameters**.
3. Returns a friendly, paginated list of products to the user."

![[Pasted image 20251215210209.png]]


### Failure Case

Now, let's look at a more realistic and complex business scenario.

A returning customer wants to **update their address** after moving:

> 'Hi, I want to update my address.'

According to the strategies outlined in the agent's system instructions, the expected behavior of the agent should be:

1. Authenticate the user
    - Ask for their email, or
    - Ask for their first name, last name, and ZIP code
2. Call `find_user_id_by_name_zip` or `find_user_id_by_email` to return the user_id
3. Immediately use the returned `user_id` to call `get_user_details`
4. Display the current address and ask the user to confirm the new address
5. Use the correct `user_id` and new address to call `update_address`
6. Confirm that the update has been completed

However, the actual behavior was as follows, and in this conversation, we found that the agent's behavior was **not correct**.

![[Pasted image 20251215211314.png]]

By reviewing the printed conversation logs, we can observe the following pattern:

1. The user requests to update their address.
    
2. The agent correctly asks for identity information (name + ZIP code).
    
3. The user responds, for example: 'My name is Noah Brown and ZIP is 80279.'
    
4. The agent calls the tool: `find_user_id_by_name_zip`, which returns a valid user_id: noah_brown_6181. This is the correct behavior!
    
5. Subsequently, when the user says, 'Can you show me my current details first?' the agent calls the tool: `get_user_details`, with the parameter { "user_id": "noah_brown_80279" }.  But the user is not found!

There were two issues in the agent's behavior above: 

- parameter propagation issue: the model did not use the recently returned `user_id` (noah_brown_6181) but instead generated a `user_id` value (noah_brown_80279). The agent confused the user's name and ZIP code, generating a fake user ID. This is a well-known hallucination problem with large models!
- continuous tool calling issue: After obtaining the `user_id`, the agent should proactively call the `get_user_details` method to retrieve the user's detailed information, which can reduce the interaction burden on the user. This requirement was written into the agent's system instructions, but the agent did not comply.

Next, let's take a look at the potential solutions. What is the benefit of model fine tuning? 

### Solutions

![[Pasted image 20260316112647.png]]

There should be three potential feasible solutions here. Let's evaluate these three solutions from the perspectives of accuracy, performance, and cost. 

However, before that, let us establish a basic consensus. Generally speaking, the more advanced a large model is and the more parameters it has, the higher its inference cost will be, and the longer the inference latency will be. 

Based on this consensus, let's review these three solutions:  

Bigger Model + Longer Prompt: We can certainly use a more advanced large model and write the system instructions in more detail. This can indeed solve the accuracy issue, but according to the consensus above, both the cost and inference latency will increase!
Advanced Agentic Design Pattern: The agentic design pattern like iterative self-reflection loops can indeed allow agents to correct errors and ultimately arrive at the correct answer through multiple iterations. However, this will definitely extend the response time, and for users performing ad-hoc searches, excessive latency is unacceptable.
Fine Tuning:  Fine-tuning can be achieved by preparing a dataset to train a relatively basic large model. This way, during the inference phase, it can enhance the accuracy of the agent without increasing costs and latency. This is its greatest value and is definitely worth trying!

### Fine Tuning Model on Microsoft Foundry

![[Pasted image 20260316113113.png]]

Fine-tuning a model on the Microsoft Foundry platform generally requires the following key steps:

1. **Decide Fine-Tuning Goals**: Improve the accuracy of the agent in multi-turn tool calls and the accuracy of parameter passing.
    
2. **Choose Base Model**: In this case, we use `gpt-4.1-mini`.
    
3. **Choose Fine-Tuning Method**: Start by trying the most common method, SFT (Supervised Fine-Tuning). If there is an opportunity later, I will share how to perform model fine-tuning based on reinforcement learning.
    
4. **Generate Training Data**: Since our goal is to enhance the accuracy of the agent's tool calls, the training data for SFT should consist of multi-turn dialogues formed by user questions and tool call chains that meet user needs.
    
5. **Run Model Evaluation**: Only by quantifying the model can we evaluate the effectiveness of the fine-tuning. Therefore, we need to first evaluate the original model, gpt-4.1-mini, and then conduct another round of evaluation after obtaining the fine-tuned model.

We already confirmed step 1, 2 and 3. So, next step, let's take a look at how to Generate Training Data.

### Synthetic Data & Knowledge Distillation

Manually preparing a dataset is a very time-consuming and labor-intensive task, typically a thankless job. Additionally, it often faces some issues:

- Scarcity of real data
- High costs
- Data privacy and compliance

![[Pasted image 20260106152748.png]]

Fortunately, Microsoft Foundry provides a Synthetic Data tool that makes this process easier. 

Conceptually, synthetic data can be divided into two methods: `Knowledge Distillation` and `Self Improvement`. The differences between them can be referenced in the image below.

![[Pasted image 20260316115416.png]]

In our case, we use `Knowledge Distillation`. And the Teacher Model is `gpt-4.1`, while the student Model is `gpt-4.1-mini`

My Synthetic Data job on Microsoft Foundry goes as following: 

![[Pasted image 20260316122309.png]]

you can see, finally it produces two datasets: `training` and `validation` in JSONL format. The details about running the Synthetic Data job is out of the scope of this article, in the future, I will explain it in detail, please subscribe my channels. All right? 


### Evaluation

As mentioned earlier, before fine-tuning, we need to evaluate the performance of the currently used base model. The evaluation data is the validation dataset generated in the previous step.

Another key point is that evaluating the model requires some metrics, right? For this, the Foundry platform provides 36 built-in metrics, but here we choose to develop custom metrics. Specifically, these metrics will assess whether the tool call functions are correct and whether the parameters of the tool functions are accurate, with each item scoring 0.5 points.

In the code level, the process can be done with 4 steps: 

Step1: Define Customized Evaluator

```
def grade_tool_calls(

    actual_tool_calls: Optional[List[Dict[str, Any]]],

    expected_tool_calls: Optional[List[Dict[str, Any]]],

    *, partial_weight: float = 0.5

) -> float:

    if not actual_tool_calls and not expected_tool_calls:

        return PASS

    if (not actual_tool_calls) != (not expected_tool_calls):

        return 0.0

  

    actual = actual_tool_calls or []

    expected = expected_tool_calls or []

  

    unused = list(range(len(actual)))

    exact = name_only = 0

  

    # pass 1: exact matches

    for e in expected:

        hit = next((i for i in unused if _sim(actual[i], e) == 1.0), None)

        if hit is not None:

            exact += 1

            unused.remove(hit)

  

    # pass 2: name-only matches

    for e in expected:

        hit = next((i for i in unused if _sim(actual[i], e) == 0.5), None)

        if hit is not None:

            name_only += 1

            unused.remove(hit)

  

    soft_tp = exact + partial_weight * name_only

    precision = soft_tp / len(actual) if actual else 1.0

    recall    = soft_tp / len(expected) if expected else 1.0

    f1 = 0.0 if (precision + recall) == 0 else (2 * precision * recall / (precision + recall))

    return round(f1, 6)
```

Step2: Upload the evaluation dataset to Foundry
```
token_provider = get_bearer_token_provider(

    DefaultAzureCredential(),

    "https://cognitiveservices.azure.com/.default"

)

  

client = AzureOpenAI(

    azure_endpoint=f"https://{resource_name}.openai.azure.com",

    azure_ad_token_provider=token_provider,

    api_version="2025-04-01-preview"

)

  

# Upload file

print(f"Uploading {eval_file.name}...")

with eval_file.open("rb") as f:

    eval_file = client.files.create(file=f, purpose="evals")
```
Step3: Create an evaluation with custom Python grader.
```
    # Read the Python grader

    with open(python_grader_path) as f:

        python_grader = f.read()

  

    # Create the evaluation

    evaluation = client.evals.create(

        name=f"Tool Calling Evaluation - {datetime.now().strftime('%Y%m%d_%H%M%S')}",

        data_source_config={

            "type": "custom",

            "item_schema": {

                "type": "object",

                "properties": {

                    "messages": {"type": "array"},

                    "tools": {"type": "array"},

                    "expected_output": {"type": "object"},

                },

                "required": ["messages", "tools"],

            },

            "include_sample_schema": True,

        },

        testing_criteria=[

            {

                "type": "python",

                "name": "Tool Use Evaluator",

                "source": python_grader,

                "pass_threshold": pass_threshold,

            }

        ],

    )
```
Step4: Create evaluation runs for each model using the same evaluation dataset with sampling parameters.

```
    for model in models_to_evaluate:

        print(f"📊 Creating evaluation run for: {model}")

  

        # Create data source with sampling parameters

        data_source = {

            "type": "completions",

            "model": model,

            "source": {"type": "file_id", "id": eval_file_id},

            "input_messages": {

                "item_reference": "item.messages",

                "type": "item_reference",

            },

            "sampling_params": {

                "tools": tools

            },

        }

  

        eval_run = client.evals.runs.create(

            name=model,

            eval_id=evaluation_id,

            data_source=data_source,

        )

  

        eval_runs.append(eval_run)

        print(f"   ✅ Run ID: {eval_run.id}")

  

    print(f"\n📋 Evaluation runs created:")
```

![[Pasted image 20260316123652.png]]

In this round of evaluation, in addition to gpt-4.1-mini, I also evaluated gpt-4.1-nano. It can be noted that their scores are 57% and 38%, respectively. The nano version of the model is somewhat weaker, which is understandable. Here, please remember the number 57%; our expectation is that the model after fine-tuning should score higher than this!

### Fine Tune

We have finally arrived at the fine-tuning job. In fact, this part is relatively straightforward and can be easily implemented by calling the Azure SDK. Basically, it has the following two steps in the code level: 

Step1: Upload the training and validation dataset
```
# Create client

token_provider = get_bearer_token_provider(

    DefaultAzureCredential(),

    "https://cognitiveservices.azure.com/.default"

)

  

client = AzureOpenAI(

    azure_endpoint=f"https://{resource_name}.openai.azure.com",

    azure_ad_token_provider=token_provider,

    api_version="2025-04-01-preview"

)

  

# Upload train file

with Path("data/sft_train.jsonl").open("rb") as f:

    train_file = client.files.create(file=f, purpose="fine-tune")

print(f"Train File ID: {train_file.id}")

  

# Upload validation file

with Path("data/sft_test.jsonl").open("rb") as f:

    valid_file = client.files.create(file=f, purpose="fine-tune")

print(f"Valid File ID: {valid_file.id}")
```
Step2: create SFT fine-tune job

```
# Create fine-tuning job

response = client.fine_tuning.jobs.create(

    training_file=train_file.id,

    validation_file=valid_file.id,

    model="gpt-4.1-mini",

    suffix="zava1-retail-sft-1",

    extra_body={"trainingType": "GlobalStandard"}

)

  

print(f"Job ID: {response.id}")

print(f"Status: {response.status}")
```

![[Pasted image 20260316124333.png]]

you can see some critical hyperparameter like Batch Size, Learning rate and number of epochs. This fine tune job runs roughly 2 hours based on my cloud resource setting. 

![[Pasted image 20260316124608.png]]

The general training metrics of machine learning, such as `loss` and `token accuracy`, can indicate whether the training is proceeding as expected. Next comes the exciting part: let's see how the newly fine-tuned model performs in the evaluation.

![[Pasted image 20260316124850.png]]


Did you see that? The score has risen to 87%! Bingo!

### Deploy and Test

Microsoft Foundry supports very easy deployment of fine-tuned models. Of course, there are many issues to consider, such as which deployment strategy is more reasonable from a cost perspective. I will analyze these in the next article, so I will skip it for now.

After completing the deployment, we can replace the agent's model with it and test the failure case that encountered an error earlier.

![[Pasted image 20260316125441.png]]


We can see that the fine-tuned model has helped us achieve our goals: first, the parameters for tool calls are no longer resulting in errors; second, it is now capable of making consecutive tool calls, which proves that the agent's planning ability has become more accurate.


### Summary

In this article, we analyzed how to conduct the fine-tuning of models on the Microsoft Foundry platform. Furthermore, and more importantly, we identified reasonable application scenarios for this technical solution of model fine-tuning, demonstrating its comprehensive value in terms of cost, performance, and accuracy.