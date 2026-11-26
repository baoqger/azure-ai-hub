---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - Agentic DevOps
title: Adding AI to CI CD - Three Ways to Build AI Powered GitHub Actions
---
## Background

In my previous articles, I shared several new software development patterns in the AI era. Whether it is a `spec`-driven development approach or building your own development workflow with multiple custom `agent` components, these are all important directions worth learning and exploring.

But software development is only one part of the software engineering lifecycle. In the AI era, the whole lifecycle also needs an upgrade. So in this article, I will share how to add AI capabilities into a traditional `CI/CD` pipeline to improve engineering collaboration efficiency.

Here, we will use `GitHub Actions` as the example and break down three ways to inject AI capabilities into `GitHub Actions`.

After reading this post, you can understand how to use built-in actions, GitHub CLI extensions, and custom actions to make a CI/CD workflow more intelligent.

![[AI_Integration_Development_Pipeline_Paths.png]]

## What Is GitHub Actions?

Before we formally introduce the AI capabilities, let's first briefly understand `GitHub Actions`. In the software engineering context, its role is very clear: it is a `CI/CD` pipeline platform. This is also the name of the product itself.

For a project hosted on `GitHub`, we can define a CI pipeline by adding a `.github/workflows/<workflow-name>.yml` file. After that, the workflow appears under the `Actions` tab:

![[Pasted image 20260727093431.png]]

At the implementation level, `actions` are also an important building block inside `GitHub Actions`. An action represents a reusable function or step that can be shared and reused. This concept will appear many times in today's article.

You can find useful `action` components in the `Marketplace`, or you can contribute your own `action` to the community and expand your technical influence.

![[Pasted image 20260727093716.png]]

The basic CI/CD pipeline concepts and syntax of `GitHub Actions` are outside the scope of this article. If you are new to them, you can refer to the official documentation first.

## AI Powered GitHub Actions

Next, I will introduce three ways to add AI capabilities to `GitHub Actions`.

To make the following technical explanation clearer, let's first define a concrete requirement. Projects hosted on GitHub usually use `Issues` to manage feature requests, bug fixes, and other collaboration tasks. Therefore, the clarity of an Issue description is very important for team collaboration. If a bug description does not provide enough information for others to reproduce the problem, the follow-up fix becomes difficult.

So, we will build an AI powered `GitHub Actions` workflow: when a newly created Issue is labeled as `bug`, AI will review the Issue description and determine whether it provides enough information to reproduce the bug.

Let's see three ways to implement this requirement.

### Method 1: Use a Built-In Action

`GitHub` provides a built-in `action`: `actions/ai-inference`. You only need to specify a model from the `GitHub Models` catalog, and then you can use AI capabilities quite easily. This is the most direct approach.

```yml
name: Bug Report Reproduction Check
on:
  issues:
    types: [opened]
permissions:
  contents: read
  issues: write
  models: read
jobs:
  reproduction-steps-check:
    runs-on: ubuntu-latest
    steps:
      - name: Fetch Issue
        id: issue
        uses: actions/github-script@v7
        with:
          script: |
            const issue_number = context.issue.number
            const issue = await github.rest.issues.get({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number
            })
            core.setOutput('title', issue.data.title)
            core.setOutput('body', issue.data.body)
      - name: Analyze Issue For Reproduction
        if: contains(join(github.event.issue.labels.*.name, ','), 'bug')
        id: analyze-issue
        uses: actions/ai-inference@v1
        with:
          model: mistral-ai/ministral-3b
          system-prompt: |
            Given a bug report title and text for a web application, return 'pass' if there is enough information to reliably reproduce the issue, meaning the report clearly describes the steps to reproduce the problem, specifies the expected and actual behavior, and includes environment details such as browser and operating system; if any of these elements are missing or unclear, return a brief description of what is missing in a friendly response to the author instead of 'pass'. Consider the following title and body:
          prompt: |
            Title: ${{ steps.issue.outputs.title }}
            Body: ${{ steps.issue.outputs.body }}
      - name: Comment On Issue
        if: contains(join(github.event.issue.labels.*.name, ','), 'bug') && steps.analyze-issue.outputs.response != 'pass'
        uses: actions/github-script@v7
        env:
          AI_RESPONSE: ${{ steps.analyze-issue.outputs.response }}
        with:
          script: |
            const issue_number = context.issue.number
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number,
              body: process.env.AI_RESPONSE
            })
```

For this first method, let's spend a little more time explaining the context, because the same parts will be reused in the next two methods and will not be repeated later.

- `Trigger`: The `on` field defines the trigger condition. In this example, the workflow runs when a new Issue is opened.
- `Permissions`: The `permissions` field defines the permissions required by this workflow. Because this workflow needs to call a model from `GitHub Models`, it adds the `models: read` permission.

This workflow contains one `job`, and the job is made up of multiple `step` objects. In `GitHub Actions`, all `step` objects in the same `job` run on the same `runner`. In this example, the runner is `ubuntu-latest`. Multiple jobs can run in parallel, but steps inside the same job run sequentially.

This workflow includes three steps:

- `Fetch Issue description`: This step uses the built-in `actions/github-script` action to run an inline script and retrieve the current Issue title and body.
- `Use AI to review Issue information`: This is where AI is used. We directly use the built-in action `actions/ai-inference`, then pass the system prompt, user prompt, model name, and other parameters through the `with` field.
- `Add a comment`: Based on the AI review result, this step adds a comment to the current Issue. Like the first step, it also uses inline script capability.

Another important point is that different `step` objects can share context through the `${{ steps.<step-id>.outputs.<field-name> }}` expression.

Next, let's look at the second method.

### Method 2: Use the gh models Extension

The second method uses the `gh models` extension to achieve the same effect. We know that `gh` is the CLI command system for `GitHub`, and it supports extending its capabilities through an `extension` mechanism. `gh models` is the extension for `GitHub Models`.

So, based on this tool, we can refactor the workflow like this:

```yml
name: Bug Report Reproduction Check (GH Models)
on:
  issues:
    types: [opened]
permissions:
  contents: read
  issues: write
  models: read
jobs:
  reproduction-steps-check:
    runs-on: ubuntu-latest
    steps:
      - name: Fetch Issue
        id: issue
        uses: actions/github-script@v7
        with:
          script: |
            const issue_number = context.issue.number
            const issue = await github.rest.issues.get({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number
            })
            core.setOutput('title', issue.data.title)
            core.setOutput('body', issue.data.body)
      - name: Install gh-models extension
        if: contains(join(github.event.issue.labels.*.name, ','), 'bug')
        run: gh extension install https://github.com/github/gh-models
        env:
          GH_TOKEN: ${{ github.token }}
      - name: Analyze Issue For Reproduction
        if: contains(join(github.event.issue.labels.*.name, ','), 'bug')
        id: analyze-issue
        run: |-
          {
            printf '%s\n' "Given a bug report title and body for a web application, return 'pass' if there is enough information to reliably reproduce the issue, meaning the report clearly describes the steps to reproduce the problem, specifies the expected and actual behavior, and includes environment details such as browser and operating system; if any of these elements are missing or unclear, return a brief description of what is missing in a friendly response to the author instead of 'pass'. Consider the following title and body:"
            printf 'Title: %s\n' "$ISSUE_TITLE"
            printf 'Body: %s\n' "$ISSUE_BODY"
          } > bug-report-prompt.md
          response="$(gh models run openai/gpt-5 < bug-report-prompt.md)"
          {
            echo 'response<<EOF'
            printf '%s\n' "$response"
            echo 'EOF'
          } >> "$GITHUB_OUTPUT"
        env:
          GH_TOKEN: ${{ github.token }}
          ISSUE_TITLE: ${{ steps.issue.outputs.title }}
          ISSUE_BODY: ${{ steps.issue.outputs.body }}
      - name: Comment On Issue
        if: contains(join(github.event.issue.labels.*.name, ','), 'bug') && steps.analyze-issue.outputs.response != 'pass'
        uses: actions/github-script@v7
        env:
          AI_RESPONSE: ${{ steps.analyze-issue.outputs.response }}
        with:
          script: |
            const issue_number = context.issue.number
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number,
              body: process.env.AI_RESPONSE
            })
```

We only changed the AI review part. The other steps remain the same. Here, we added two new steps:

- `Install the gh models extension`: The default `runner` environment does not include this extension, so we need to install it first by using `gh extension install`.
- `Use gh models to review Issue information`: This step uses the `run` field to execute a Bash script. The script first writes the prompt into a file, then calls `gh models run openai/gpt-5` with that prompt file, and finally sets the model response as the action output.

With this method, you can directly call models from `GitHub Models` and define the parameters and execution behavior yourself. Compared with the first built-in `action` approach, this is much more flexible.

However, the biggest problem with this method is reusability. Other people cannot easily reuse it, and even you cannot conveniently reuse it across your own projects. So, the next step is to go further and develop a reusable and shareable custom action that encapsulates the AI calling capability.

### Method 3: Develop a Custom Action

Developing a custom `action` requires several core components.

#### Code Implementation

Here, we will use `JavaScript` to implement our own `action`. In the project, we create a `src` directory to store the source code of the `action`.

```plain
src/
├── checkBugReport.js
├── index.js
└── main.js
```

The core logic is in `checkBugReport.js`:

```javascript
const OpenAI = require("openai");

const endpoint = "https://models.github.ai/inference";
const model = "openai/gpt-5";

const systemPrompt =
  "Given a bug report title and body for a web application, return 'pass' if there is enough information to reliably reproduce the issue, meaning the report clearly describes the steps to reproduce the problem, specifies the expected and actual behavior, and includes environment details such as browser and operating system; if any of these elements are missing or unclear, return a brief description of what is missing in a friendly response to the author instead of 'pass'.";

async function checkBugReport({ title, body, token }) {
  const client = new OpenAI({ baseURL: endpoint, apiKey: token });
  const completion = await client.chat.completions.create({
    model,
    messages: [
      {
        role: "system",
        content: systemPrompt,
      },
      {
        role: "user",
        content: `Title: ${title}\nBody: ${body || ""}`,
      },
    ],
  });

  const response = completion.choices[0]?.message?.content?.trim();

  if (!response) {
    throw new Error("GitHub Models returned an empty response.");
  }

  return response;
}

module.exports = { checkBugReport };
```

This module uses the `openai` library to communicate with the model hosted on `GitHub Models`. With this implementation, we have almost no limitation from the workflow layer because we can freely write code. It encapsulates a method named `checkBugReport`, which accepts three input parameters: `title`, `body`, and `token`.

The `main.js` file handles the interaction with `GitHub Actions`.

```javascript
const { checkBugReport } = require("./checkBugReport");
const core = require("@actions/core");

async function run() {
  try {
    const title = core.getInput("title", { required: true });
    const body = core.getInput("body");
    const token = core.getInput("token", { required: true });
    const response = await checkBugReport({ title, body, token });
    core.setOutput("response", response);
  } catch (error) {
    core.setFailed(error instanceof Error ? error.message : String(error));
  }
}

module.exports = { run };
```

This module depends on the `@actions/core` library to handle `input` and `output`.

Finally, the `index.js` file is the entry point, and it is very simple:

```javascript
const { run } = require("./main");
run();
```

#### Package the Action

For easier usage, we need to bundle the whole `action` implementation together with its dependencies into a single module:

```shell
ncc build src/index.js -o dist
```

#### Declare the Action

Every `action` needs a declaration file to define its behavior. The core idea is to define its `inputs`, `outputs`, runtime environment, and script file path.

```yml
name: "Bug Reproduction Check Action"
description: "Checks whether a bug report contains enough information to reproduce"
inputs:
  title:
    description: "The bug report title"
    required: true
  body:
    description: "The bug report body"
    required: false
    default: ""
  token:
    description: "Token to use for GitHub Models API calls"
    default: ${{ github.token }}
outputs:
  response:
    description: "AI-generated reproduction check response"
runs:
  using: node24
  main: dist/index.js
```

With these three steps, we have finished developing the custom `action`. Next, we can use it inside a workflow.

#### Reuse the Action

```yml
name: Bug Report Reproduction Check (Custom Action)
on:
  issues:
    types: [opened]
permissions:
  contents: read
  issues: write
  models: read
jobs:
  reproduction-steps-check:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      - name: Fetch Issue
        id: issue
        uses: actions/github-script@v7
        with:
          script: |
            const issue_number = context.issue.number
            const issue = await github.rest.issues.get({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number
            })
            core.setOutput('title', issue.data.title)
            core.setOutput('body', issue.data.body)
      - name: Analyze Issue For Reproduction
        if: contains(join(github.event.issue.labels.*.name, ','), 'bug')
        id: analyze-issue
        uses: ./
        with:
          title: ${{ steps.issue.outputs.title }}
          body: ${{ steps.issue.outputs.body }}
          token: ${{ github.token }}
      - name: Comment On Issue
        if: contains(join(github.event.issue.labels.*.name, ','), 'bug') && steps.analyze-issue.outputs.response != 'pass'
        uses: actions/github-script@v7
        env:
          AI_RESPONSE: ${{ steps.analyze-issue.outputs.response }}
        with:
          script: |
            const issue_number = context.issue.number
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number,
              body: process.env.AI_RESPONSE
            })
```

Because the corresponding logic has already been encapsulated inside the `action`, the workflow layer becomes much simpler. We only need to specify the input parameters through the `with` field.

Also, because this `action` is currently inside the same repository, we need to use `actions/checkout` first to pull the code onto the runner. If someone else wants to use my `action`, they can directly write the repository address in the `uses` field, such as `uses: owner/repo@ref`.

## Summary

In this article, we used the same bug report review requirement to break down three ways to create AI powered GitHub Actions:

- Use `actions/ai-inference`: the fastest way to get started, suitable for quickly validating an idea.
- Use the `gh models` extension: more flexible, suitable for customizing model invocation logic inside a workflow.
- Develop a custom `action`: the most reusable approach, suitable for turning a capability into something that can be shared by a team or the community.

If you only want to quickly try AI capabilities in a single project, the first two methods are already enough. If you want to productize and modularize the capability and reuse it across multiple projects for the long term, building a custom `action` is the direction worth investing in.

The detailed code for the three methods in this article is available in my repo: https://github.com/baoqger/demo-models-in-actions
