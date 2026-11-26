---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - RAG
title: Implementing Agentic RAG on Azure From Hand-Coded Code to Ready-to-Use Solutions
---
## Background

In previous articles, I shared various techniques for developing RAG based on Azure AI Search, whether it was Naive RAG, Advanced RAG, or multimodal RAG. The pipelines of these RAG systems were all linear, expecting satisfactory results from a single retrieval-generation pass. However, this expectation is actually quite unrealistic.

In the real world, users' questions can be quite complex, and single retrieval-generation might not yield good results. At this point, we need to advance to agentic RAG.

In today's article, we'll combine all the previous modules to build an Agentic RAG. During this process, we'll use Azure AI Search as well as Microsoft Foundry Agent Service.

You'll find that the logic of Agentic RAG is quite complex, and building one from scratch requires a lot of effort and time! Therefore, in the next step, let's see how we can use Azure AI Search's agentic retrieval capability to implement a ready-to-use Agentic RAG solution! Let's get started!

## What is Agentic RAG?

![[Pasted image 20260508214949.png]]

Compared to linear RAG systems, Agentic RAG systems take a step further by adding Agent intelligence to the RAG system. This allows AI to not only act during the query phase but also fully utilize Agent capabilities such as planning, reflection, tool calling, orchestration, and more, enabling RAG to answer more complex questions!

Agentic RAG is based on the basic RAG retrieval + generation pattern, adding various Agent capabilities: planning, orchestration, tool calling, and so on. Therefore, Agentic RAG doesn't have a fixed pattern because Agents themselves are variable, but the three core technologies are:

- **Autonomous evaluation**

Utilizing the concept of LLM-as-a-judge, embedding powerful evaluation capabilities to provide the basis for iterative optimization.

- **Iterative improvement**

Through self-optimization loop mechanisms, identifying and correcting deficiencies in generated answers.

- **Tool calling**

Large language models autonomously determine which tools to call and what actions to take to improve the overall quality of answers. This is particularly critical when handling complex or ambiguous queries.

Next, let's see how to build an Agentic RAG architecture using Azure AI Search and Foundry Agent Service!

## Agentic RAG Architecture

![[images/Pasted image 20260407160447.png]]

From a high-level perspective, the flow is as follows:

1. A user asks a question.
2. The system first retrieves relevant information from an internal private knowledge base and generates an initial answer based on the retrieval results. Here, various advanced algorithms from Azure AI Search can be used, such as query rewriting, hybrid search, and reranking.
3. Then, through a separate evaluation step, it determines whether this answer is sufficiently relevant and truly based on retrieved evidence. This uses the LLM-as-a-judge strategy.
4. If the answer quality is good enough, the process ends and the answer is returned to the user.
5. If the answer quality is not good enough, the system enters a "reflection" phase. It analyzes the problems with the previous answer, examines the evidence used at the time, and the feedback provided by the evaluation.
6. Based on this reflection, the system decides on the next action. This action could be:
   - Re-search the internal private knowledge base with a more appropriate query
   - Search the web for missing public information
   - Stop directly if it determines that continuing to search won't help improve the answer
7. After executing this action, the system regenerates the answer combining the new evidence.
8. Then evaluate the quality of this new answer again.
9. This cycle continues until the answer reaches preset quality standards or reaches the maximum number of iterations.

The key point of this design is that the model doesn't just "generate answers" but also "judges whether answers are good" and actively takes corrective actions when deficiencies are found. This is why it's called "agentic." It can not only answer questions but also identify defects in its own answers, decide how to remedy them next, obtain more information, and try again.

Let's look at code fragments for key steps below.

#### Query Rewrite + Hybrid Search

``` python
async def rewrite_query(app_state: AppState, question: str, message_history: List[ChatCompletionMessageParam]) -> QueryRewriteAction:
    query_messages = prompty.prepare(
        query_rewrite_prompt, {"user_query": question, "past_messages": message_history}
    )
    result = await app_state.openai_client.beta.chat.completions.parse(
        messages=query_messages,
        response_format=SearchSources,
        model=app_state.query_rewriter_deployment,
        temperature=0
    )
    if parsed := result.choices[0].message.parsed:
        return QueryRewriteAction(
            query=question, message_history=message_history, rewritten_query=parsed.search_query
        )

    return QueryRewriteAction(
        query=question, message_history=message_history, rewritten_query=None
    )

@step
async def index_search(app_state: AppState, question: str, message_history: List[ChatCompletionMessageParam]) -> IndexSearchAction:
    query = await rewrite_query(app_state, question, message_history)
    response = await app_state.search_client.search(
        search_text=query,
        vector_queries=[VectorizableTextQuery(text=query, k_nearest_neighbors=50, fields="embedding")],
        query_type="semantic",
        semantic_configuration_name="default",
        top=10,
        select=["content", "id", "sourcepage"]
    )
    results = [Document(content=result["content"], id=result["id"], score=result["@search.reranker_score"], title=result["sourcepage"]) async for result in response]
    filtered_results = await filter_documents(results)
    return IndexSearchAction(
        query=question,
        rewritten_query=query.rewritten_query,
        documents=filtered_results.filtered_documents,
    )
```

#### Generate Answer

``` python
async def generate_answer(app_state: AppState, question: str, answer_sources: AnswerSources, previous_answer: Optional[str] = None, previous_answer_reflection: Optional[str] = None, previous_answer_evaluations: Optional[List[EvaluatorResponse]] = None ) -> AnswerAction:
    messages = prompty.prepare(
        answer_prompt,
        {
            "user_query": question,
            "context": answer_sources.create_context(),
            "previous_answer_reflection": previous_answer_reflection,
            "previous_answer": previous_answer,
            "previous_answer_evaluations": previous_answer_evaluations
        }
    )

    stream: AsyncStream[ChatCompletionChunk] = await app_state.openai_client.chat.completions.create(
        messages=messages,
        stream=True,
        model=app_state.answer_generator_deployment,
        temperature=0.3
    )

    answer_text = ""
    msg: Optional[cl.Message] = None if not running_in_cl() else cl.Message("")
    async for part in stream:
        if part.choices and (token := part.choices[0].delta.content or ""):
            answer_text += token
            if msg:
                await msg.stream_token(token)

    result = AnswerAction(
        question_text=question,
        answer_text=answer_text,
        answer_sources=answer_sources,
    )
```

#### LLM-as-a-Judge Effect Evaluation

Here we use two key indicators: `groundedness` and `relevance`.

``` python
async def evaluate_answer(app_state: AppState, answer: AnswerAction, previous_reflection: Optional[ReflectionAction] = None) -> EvaluationAction:
    evaluator_context = answer.answer_sources.create_context()
    if previous_reflection:
        evaluator_context += f"\n\nPrevious Answer: {previous_reflection.answer_text}\n\nPrevious Answer Incorrect Reason: {previous_reflection.answer_reflection}"

    def eval_groundedness() -> Dict[str, Any]:
        return app_state.groundedness_evaluator(
            **{
                "query": answer.question_text,
                "context": evaluator_context,
                "response": answer.answer_text
            }
        )

    def eval_relevance() -> Dict[str, Any]:
        return app_state.relevance_evaluator(
            **{
                "query": answer.question_text,
                "response": answer.answer_text
            }
        )

    results = await asyncio.gather(async_eval_groundedness(), async_eval_relevance())
    groundedness_result = results[0]
    relevance_result = results[1]

    results = [
        EvaluatorResponse(
            type="relevance",
            score=relevance_result['relevance'],
            explanation=relevance_result['relevance_reason']
        ),
        EvaluatorResponse(
            type="groundedness",
            score=groundedness_result['groundedness'],
            explanation=groundedness_result['groundedness_reason']
        )
    ]

    return EvaluationAction(
        evaluations=results,
        answer=answer
    )
```

#### Reflect on Answer

Here we send the current answer, current retrieval question, and retrieved information as prompts to the large language model. The model will evaluate and determine the next action: `stop`, `index_query`, or `web_query`.

``` python
async def reflect_answer(app_state: AppState, action_list: ActionList) -> ReflectionAction:
    last_answer_action = action_list.get_last_answer()
    last_query = action_list.get_last_query()
    last_evaluation = action_list.get_last_evaluation()
    assert last_answer_action != None
    assert last_query != None
    assert last_evaluation != None
    reflect_messages = prompty.prepare(
        reflect_prompt,
        {
            "previous_answer": last_answer_action.answer_text,
            "previous_sources": last_answer_action.answer_sources.create_context(),
            "previous_query": last_query,
            "previous_answer_evlauation": "\n".join(f"{evaluation.type}: {evaluation.score}, {evaluation.explanation}" for evaluation in last_evaluation.evaluations)
        }
    )
    result: ChatCompletion = await app_state.openai_client.chat.completions.create(
        messages=reflect_messages,
        tools=[pydantic_function_tool(ToolChoiceReflection)],
        model=app_state.reflection_deployment
    )

    if result.choices[0].message.tool_calls:
        tool_call = result.choices[0].message.tool_calls[0]
        tool_reflection = json.loads(tool_call.function.arguments)
        follow_up_action_str = "stop"
        if "index_query" in tool_reflection["follow_up_action"]:
            follow_up_action_str = "index_search"
            next_query = tool_reflection["follow_up_action"]["index_query"]
        elif "web_query" in tool_reflection["follow_up_action"]:
            follow_up_action_str = "web_search"
            next_query = tool_reflection["follow_up_action"]["web_query"]
        action = ReflectionAction(
            answer_text=last_answer_action.answer_text,
            answer_reflection=tool_reflection["answer_reflection"],
            follow_up_action=follow_up_action_str,
            follow_up_action_reason=tool_reflection["follow_up_action_reason"],
            next_query=next_query,
            actions=action_list.actions
        )

    return action
```

#### Execute Next Step

If we need to perform another vector search, we execute the `index_search` method, which was already introduced in the first step above.

``` python
async def reflect_next_action(app_state: AppState, reflection: ReflectionAction, answer_sources: AnswerSources) -> Tuple[Action, AnswerSources]:
    if reflection.follow_up_action == "index_search" and reflection.next_query:
        index_action = await index_search(app_state, reflection.next_query, answer_sources.message_history)
        next_sources = answer_sources.add_index_search(index_action)
        return (index_action, next_sources)
    elif reflection.follow_up_action == "web_search" and reflection.next_query:
        web_search_action = await web_search(app_state, reflection.next_query)
        next_sources = answer_sources.add_web_search(web_search_action)
        return (web_search_action, next_sources)
    elif reflection.follow_up_action == "stop":
        return (StopAction(), answer_sources)
```

If we need to perform a web search, we execute `web_search` as follows:

```python
@step
async def web_search(app_state: AppState, query: str) -> WebSearchAction:
    # Initialize agent bing tool and add the connection id
    if not app_state.bing_tool:
        bing_connection = await app_state.ai_project_client.connections.get(app_state.bing_grounding_name)
        app_state.bing_tool = BingGroundingTool(connection_id=bing_connection.id)
    search_agent = await app_state.agents.create_agent(
        model="gpt-4o",
        name="my-web-assistant",
        instructions="You are a helpful assistant",
        tools=app_state.bing_tool.definitions,
        headers={"x-ms-enable-preview": "true"},
    )
    thread = await app_state.ai_project_client.agents.create_thread()
    await app_state.ai_project_client.agents.agents.create_message(
        thread_id=thread.id,
        role=MessageRole.USER,
        content="Search the web: " + query,
    )
    async for run_attempt in AsyncRetrying(retry=retry_if_exception_type(ValueError), wait=wait_exponential(min=4, max=60), stop=stop_after_attempt(10)):
        with run_attempt:
            run = await app_state.ai_project_client.agents.create_and_process_run(thread_id=thread.id, agent_id=search_agent.id)
            if run.status == "failed" and run.last_error and run.last_error.get('code') == 'rate_limit_exceeded':
                raise ValueError("Rate limit exceeded. Please try again later.")

            if run.status == "failed":
                raise ValueError(run.last_error)

            response_messages = await app_state.ai_project_client.agents.list_messages(thread_id=thread.id)
            response_message = response_messages.get_last_message_by_role(
                MessageRole.AGENT
            )
            if response_message.text_messages and len(response_message.text_messages) > 0:
                response_content = response_message.text_messages[0].text.value
                citations = [ WebCitation(name=annotation.text, url=annotation.url_citation.url, title=annotation.url_citation.title) for annotation in response_message.url_citation_annotations ]
            else:
                response_content = ""
                citations = []

            return WebSearchAction(
                query=query,
                response_content=response_content,
                citations=citations,
            )

```

The core logic here is creating an agent on Foundry based on the Azure Agent SDK: `my-web-assistant`. This agent's tool set includes `BingGroundingTool`, so it can call Bing for web searches.

#### Agentic Loop

All these key steps above run in the following loop. The conditions for breaking out of the loop include three: evaluation score greater than or equal to 4 (out of 5 total), reaching the maximum number of loops (such as 4 times here), or the large language model determining that there's no need for the next step.

```python
    max_turns = 3
    turn = 1
    while any(evaluation.score < 4 for evaluation in evaluation_action.evaluations):
        reflection_action = await reflect_answer(app_state, action_list)
        next_action, next_sources = await reflect_next_action(app_state, reflection_action, answer_action.answer_sources)
        next_answer_action = await generate_answer(app_state, message, next_sources, previous_answer=answer_action.answer_text, previous_answer_reflection=reflection_action.answer_reflection, previous_answer_evaluations=evaluation_action.evaluations)
        evaluation_action = await evaluate_answer(app_state, next_answer_action, reflection_action)
        action_list.actions.extend([reflection_action, next_action, next_answer_action, evaluation_action])

        if reflection_action.type == "stop":
            break
        turn += 1
        if turn > max_turns:
            break

```

Above shows a lot of code, don't be nervous - the complete runnable code is in this GitHub repo: https://github.com/baoqger/rag-time-demo.git

I believe you've also discovered that implementing an Agentic RAG system from scratch is a huge project and quite complex. Below, let's see how to build a ready-to-use intelligent RAG system based on the Agentic Retrieval functionality of Azure AI Search service!

## Ready-to-Use Agentic Retrieval

Previously, we introduced solutions based on Azure AI Search that actually used its `classic retrieval` mode. Besides this mode, it also provides another mode called `agentic retrieval`.

`agentic retrieval` utilizes the capabilities of large language models to decompose complex queries. This step is called `query planning`. A complex query will be decomposed into multiple subqueries, then retrieval is performed based on each subquery, followed by merging answers. Of course, if requirements are not met, this process can continuously iterate. The overall performance looks like this:

![[images/Pasted image 20260407222743.png]]

Here you can also see that data sources (knowledge source) can have many origins. These data sources are managed by Knowledge base, and agentic retrieval + knowledge base + knowledge source is `Foundry IQ`, which is a very important module on the Microsoft Foundry platform, providing a data layer for agents.

Based on Azure AI Search's agentic retrieval mode and Foundry IQ, you can relatively easily implement enterprise-level Agentic RAG systems. This work is left for everyone to explore!
