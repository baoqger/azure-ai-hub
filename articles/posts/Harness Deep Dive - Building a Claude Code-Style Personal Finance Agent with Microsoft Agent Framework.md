---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - Agent
title: Harness Deep Dive - Building a Claude Code-Style Personal Finance Agent with Microsoft Agent Framework
---
## Background

In this article, I want to share what I learned about `agent harness` by building a `CLI`-style stock-investment agent inspired by `Claude Code`, and use that project to break down the value and role of an `agent harness`.

This article uses the `harness` module in the `Microsoft Agent Framework`, but the harness techniques and concepts we cover are not limited to that framework. Our focus is on understanding what a `harness` means, what it does, and where it fits. With that understanding, you will not be locked into any single framework.

![[Anatomy_of_AI_Agent_Harness.png]]
## What Is an Agent Harness?

Why do we need an `agent harness` in the first place?

If your agent simply connects to a few external tools, completes one operation based on the user's question, lets the LLM process the result, and returns it to the user, then honestly, a `harness` does not matter much for that kind of simple scenario.

But if you are building an agent that needs to compete with top-tier agents such as `Claude Code` and `GitHub Copilot CLI`, you should ask yourself: does your agent support the following capabilities?

- **Context window management**: compress and summarize conversation history to improve token efficiency and agent behavior accuracy.
- **Plan and execute dual modes**: switch between two modes based on task complexity. For complex tasks, plan first, allow human review, then execute; for simple tasks, execute directly.
- **Multi-step task decomposition**: break a complex task and plan into smaller, manageable subtasks.
- **Todo task loop**: place decomposed subtasks into a `ToDo List` and loop through them one by one.
- **File-based long-term memory**: persist important information to files within a `session`-based memory system so context-window management does not cause memory loss; support exporting and importing `session` memory to lay the foundation for long-running tasks.
- **File read/write**: record agent output in files.
- **Shell**: as the gateway to the underlying operating system, shell access gives an agent open-ended capability—any task a human can accomplish by running programs, an agent can attempt as well.
- **Skill**: provide domain how-tos and load them progressively on demand to improve efficiency.
- **Web search**: supplement knowledge through web search, which is essential for deep-research agents and therefore a core harness capability.
- **Code generation and execution**: calculation-heavy tasks are not ideal for LLMs, so generating and executing code—relying on deterministic computation—is another must-have harness capability for powerful agents.
- **Background concurrent tasks**: for very complex work, running multiple background subagents without blocking the user is also important.
- **Human approval**: powerful agent capabilities require human approval to keep the system safe and stable.

If you use powerful agents like `Claude Code` and `GitHub Copilot CLI` regularly, you have probably experienced most of the capabilities above in one way or another. They all fall under the `harness` umbrella. In the sections below, let's walk through them one by one and make them less mysterious.

## Case Study

Here we use the `Microsoft Agent Framework` to build a `personal finance` agent that helps users with portfolio analysis, market research, stock lookup, and risk and valuation analysis. This case study uses personal finance as the demo scenario, but the harness capabilities shown here apply to any domain.

##### Harness in Microsoft Agent Framework

`Microsoft Agent Framework` is Microsoft's unified agent development framework, consolidating the earlier `Semantic Kernel` and `AutoGen` frameworks. It is the direction Microsoft will continue investing in, so it is worth paying attention to.

For `harness` design, `Agent Framework` takes a very developer-friendly approach. It provides a factory function:

```python
create_harness_agent()
```

In the simplest case, you only need two parameters:

- `client`: the client used to communicate with the LLM. Common options include `OpenAIChatCompletionClient` and `FoundryChatClient`. The latter is how you talk to models on Foundry, and it is the one we use in this article.
- `agent_instructions`: the agent's system instructions.

That's right—unless you have special requirements, this alone gives you an `agent harness`, because other capabilities are enabled by default. If you want to turn off a specific `harness` capability, pass the corresponding parameter to `create_harness_agent`. The naming convention is `disable_<harness_feature>`, for example `disable_todo`, `disable_mode`, `disable_file_memory`, `disable_compaction`, and so on.

Smart design, right?

##### Textual Terminal Host

To run the agent, we need to provide a `host` that handles interaction between the agent and the user. For this, `Agent Framework` offers a library called `console`, which provides a text user interface (TUI) similar to `Claude Code` and `GitHub Copilot CLI`.

![[Pasted image 20260811093209.png]]

Great—on top of this foundation, we can demo various `harness` capabilities.

## Demo

##### Mode Switching

By default, a `harness agent` runs in `plan` mode. In our early demos, the questions were relatively simple, so there was no need for `plan` mode. You can switch to `execute` mode with the `/mode execute` command:

![[Pasted image 20260811093701.png]]

As shown below:

![[Pasted image 20260811093743.png]]

##### Web Search

We provided this `harness` with a custom tool function that hardcodes stock data for several companies. Questions such as "What is the current price of a given stock?" trigger that tool:

![[Pasted image 20260811094129.png]]

For questions that require external information—such as a company's latest financial news—you need web search instead, as shown below:

![[Pasted image 20260811094502.png]]

How web search is executed depends on the LLM client you choose. In our case, we use `FoundryChatClient`, which automatically uses Bing Search.

##### Session Memory

For valuable information, we want to persist it to files. That requires `File I/O`. For example, I asked the agent to add several stocks to my watchlist file:

![[Pasted image 20260811095857.png]]

The corresponding file appears under the current session directory:

![[Pasted image 20260811100153.png]]

##### Session Memory Export and Import

As mentioned above, you can export and import session memory with the `session-export` and `session-import` commands:

![[Pasted image 20260811104629.png]]

##### Plan First, Then Execute

For more complex tasks—such as asking the agent to review the current watchlist and then recommend a few stocks—you need to `plan` first and then `execute`:

![[Pasted image 20260811103240.png]]

The screenshot above shows the plan the agent produced.

##### ToDo List

Complex tasks like the one above are broken into multiple steps and managed through a `ToDo List`. You can inspect current task progress and status with the `/todos` command:

![[Pasted image 20260811103928.png]]

##### File Access Permissions

By default, the `harness` grants read/write access to session memory files. If your agent also needs to read or write other files, you can use the `file_access_store` parameter to specify which directory is accessible.

File read and write operations also require authorization. You can configure permissions based on your needs, for example:

```python
auto_approval_rules=[FileAccessProvider.read_only_tools_auto_approval_rule]
```

With this setting, read operations skip the manual approval step. In the task below, the agent reads my `portfolio.csv` file without requiring human review:

![[Pasted image 20260811105445.png]]

By contrast, a write operation still requires human approval:

![[Pasted image 20260811105927.png]]

##### Skill

`Agent skill` provides a way to progressively load domain best practices. In this case, we configured two skills for the finance agent: `valuation` and `risk-scoring`, covering valuation theory and risk-control best practices respectively.

For example, when I asked the agent to value a company, it first loaded the `valuation` skill on demand and then performed the analysis based on that skill's content:

![[Pasted image 20260811110640.png]]

##### Shell

As mentioned at the beginning, shell access is a double-edged sword. On one hand, it unlocks enormous capability; on the other, it introduces significant security risk.

`Agent Framework` mitigates shell access risk in two ways:

- **Confined working directory**: every command is re-anchored to a fixed directory and cannot escape it.
- **Deny-list policy**: obviously destructive commands are blocked before execution.

You can configure this as shown below:

```python
_VAULT_DIR = _WORKING_DIR / "confirmations"

LocalShellTool(
    mode="persistent",
    workdir=str(_VAULT_DIR),
    confine_workdir=True,
    policy=ShellPolicy(
        denylist=[
            r"\brm\s+-rf\b",
            r"\bsudo\b",
            r":\(\)\s*\{",  # fork-bomb shape
            r"\bmkfs\b",
            r">\s*/dev/sd",
        ],
    ),
    timeout=15,
)
```

With this configuration in place, I asked the agent to clean up files in that directory, and it solved the task using shell commands:

![[Pasted image 20260811110956.png]]

##### Code Generation and Execution

For tasks that require mathematical computation, we should dynamically generate and execute code. For example, the task below asks the agent to calculate the total value of my investment portfolio.

`agent-framework` uses the `pydantic-monty` Python interpreter for this. Pass it to the factory function as a `context_provider`:

```python
agent = create_harness_agent(
    context_providers=[MontyCodeActProvider(approval_mode="always_require")],
)
```

![[Pasted image 20260811113205.png]]

##### Background Tasks

`Agent Framework` supports handing multiple tasks to background subagents concurrently and then aggregating the results.

In this case study, we wrapped the web-search-based stock research workflow into a subagent:

```python
def _build_research_agent(client: FoundryChatClient) -> Any:
    """Build the lean, web-search-only chat agent used for per-ticker research."""
    return Agent(
        client=client,
        name="TickerResearchAgent",
        description="Searches the web for recent news and commentary about a single stock ticker.",
        tools=[client.get_web_search_tool()],
        instructions=(
            "You research a single stock ticker. Use the web search tool to find the most recent, "
            "relevant news and commentary, then return a short, factual summary (3-4 bullet points) "
            "with no preamble."
        ),
    )
```

Then pass it to the factory function as a `background agent`:

```python
research_agent = _build_research_agent(client)

agent = create_harness_agent(
    background_agents=[research_agent],
)
```

This lets the agent search multiple tickers in parallel and produce a summary analysis:

![[Pasted image 20260811115119.png]]

## Summary

By this point, you should have a clearer picture of what an agent harness actually is. It is not a single feature module, but a full runtime environment built around the LLM. If we think of an agent as Model + Harness, the model handles understanding and reasoning, while the harness makes the agent able to plan, remember, call tools, and execute safely.

In this article, we used a Claude Code–style personal finance agent to turn harness capabilities that often sound abstract into demos you can actually run and observe:

- Task orchestration: mode switching, plan-then-execute, ToDo List, background subagents — this layer answers how complex tasks are broken down, executed, and kept from blocking the user.
- Memory and persistence: Session Memory and its export/import — this layer answers how information survives across turns and across sessions.
- Tools and capabilities: web search, Skill, code generation and execution, Shell — this layer answers how the agent gets external information, domain knowledge, deterministic computation, and system-level operations.
- Safety and governance: file access permissions, human approval, Shell confinement and deny-list — this layer answers how stronger capabilities are paired with stronger boundaries and safety controls.

The value of Microsoft Agent Framework is that it packages these capabilities by default through `create_harness_agent()`. You do not have to assemble everything from scratch. Provide a `client` and `agent_instructions`, and you get a fully featured harness agent. When you need to trim capabilities, use `disable_<feature>` to turn them off selectively. That “batteries included, disable as needed” design lowers the barrier to building a top-tier agent experience.

One final point: this article uses personal finance as the demo scenario, but harness capabilities are domain-agnostic. Whether you are building a coding assistant, an ops agent, a research agent, or an enterprise knowledge assistant, the same capability stack applies. Once you understand what a harness is and where its boundaries lie, you are not locked into any one framework — knowing which capabilities you need matters more than memorizing a specific API surface.
