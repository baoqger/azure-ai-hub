---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - FinOps
title: Cost Strategy for Deploying and Hosting Fine-tuned Models on Microsoft Foundry
---
### Background

In my previous article, I introduced how to improve the accuracy of Agent tool calling through fine-tuning LLMs. One important question we need to address is how to balance cost, performance, and accuracy.

For performance and accuracy, we can draw conclusions from theoretical analysis and also verify them through the before-and-after comparison in my demo.

The cost issue is more complex and more realistic. We need to analyze Azure AI service's pricing logic and then find a strategy that meets our needs.

### Cost Analysis

![[Pasted image 20260317150547.png]]

The image above shows the cost changes after deploying the fine-tuned model to the Microsoft Foundry platform (December 18th).

Let's analyze the cost composition. According to official documentation, the cost of training and deploying fine-tuned models on Azure mainly comes from two aspects: `training costs` and `deployment costs`.

Training costs are calculated based on the formula: `number of training data tokens × training epochs × cost per token`.

Deployment costs are billed by hours and online inference token count, with specific costs depending on the base model type and computing resource configuration type, which will be explained in detail below.

### Cost Calculation

![[Pasted image 20260317152421.png]]

The image above shows some key parameters in my model fine-tuning task, including those related to cost calculation:

- training token billed (number of training data tokens): 6,183,000 (~6M)
- number of epochs (training epochs): 3
- base model: gpt-4.1-mini
- training type: Global, a relatively affordable configuration that doesn't guarantee training data is in the same region as the Foundry resources used. It's suitable for situations with lower compliance and security requirements, thereby accelerating model development speed.

According to Azure documentation hints, we can see the pricing for gpt-4.1-mini as follows:

![[Pasted image 20260317152254.png]]

With this information and the calculation formula above, we can get the cost of this model fine-tuning task:

`6M × 3 × ($5/1M) = $90`

And deployment cost is: `$40/day + actual inference token cost`

This calculation matches perfectly with my cost management screenshot above.

### Deployment Strategy

For model training costs, Azure adopts token-based billing because it's very transparent and predictable.

For model deployment costs, there are two possible strategies: low fixed deployment cost + high inference token cost, or high fixed cost + low inference token cost. Currently, Azure adopts the latter: high fixed deployment cost + low inference token cost.

These two approaches themselves aren't inherently good or bad - the key is choosing the right scenario, as shown in the comparison below:

![[Pasted image 20260317162955.png]]

If your online inference traffic is predictably high, Azure's current strategy is very suitable - once token usage exceeds a certain threshold, costs become very advantageous; if your online inference traffic fluctuates significantly, the low fixed deployment cost strategy might be more suitable for you.

Additionally, the current strategy has another benefit: these fine-tuned models remain continuously online, just like other base models on Azure, ensuring the same SLA metrics.