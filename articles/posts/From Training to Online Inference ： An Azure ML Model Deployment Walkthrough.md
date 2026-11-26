---
date: 2026-09-25
authors:
  - chris-bao
categories:
  - Azure ML
title: From Training to Online Inference ： An Azure ML Model Deployment Walkthrough
---
#azure #azureai #machinelearning

## Background

In my previous article, I shared the first lesson in this Azure Machine Learning beginner series. Starting from how to run a training job, I broke down several important resources in Azure ML: `compute`, `environment`, `datastore`, and `job`. Once a training job is complete, we get a model.

In this post, I want to continue that story and focus on the second half: model deployment and online inference. After reading this post, you can understand the basic workflow for taking a trained model, deploying it to Azure ML, and invoking it through an online endpoint.

## Register the `Model`

After a training job completes, we can obtain a model artifact from the corresponding framework. A model usually consists of several binary files. In Azure Machine Learning, there are three main model types:

- `custom model`: a custom model that supports training outputs from different machine learning frameworks.
- `mlflow model`: a machine learning model based on the MLflow platform. I will share more about this in a future article.
- `triton_model`: a model based on the NVIDIA Triton inference server. I will also break this down separately later.

To make the later deployment steps easier, Azure ML generally recommends registering the model first. For example:

```python
from azure.ai.ml import MLClient
from azure.ai.ml.entities import Model
from azure.ai.ml.constants import AssetTypes
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import os

load_dotenv()

# enter details of your AML workspace
subscription_id = os.getenv("SUBSCRIPTION")
resource_group = os.getenv("RESOURCE_GROUP")
workspace = os.getenv("WS_NAME")

ml_client = MLClient(
    DefaultAzureCredential(), subscription_id, resource_group, workspace
)

file_model = Model(
    path="../model-1/model/",
    type=AssetTypes.CUSTOM_MODEL,
    name="my-model",
    description="Model created from local file.",
)

ml_client.models.create_or_update(file_model)
```

The code above uploads the model files under the local directory `model-1/model` to Azure ML and registers them as `my-model`. The model type here is `custom model`.

After the registration succeeds, we can see that the core file of this model is `sklearn_regression_model.pkl`. From the file name, we can tell that it is a regression model trained with scikit-learn.

![[Pasted image 20260516215412.png]]

With the model ready, the next step is to deploy it to the cloud and perform online inference.

## Create the `Endpoint`

In Azure ML, an `Endpoint` exposes a standard `HTTPS` interface to the outside world. By sending requests to that interface, we can perform real-time online inference. Of course, this interface is not just a simple URL. Behind it, there are still compute resources required to host the model. Azure ML simply groups and manages those resources under the `Endpoint` abstraction. Smart design, right?

`Endpoint` supports two types: `managed online endpoints` and `k8s online endpoints`. In this article, I will focus on the former. We can define and create an endpoint with the following code:

```python
from azure.ai.ml.entities import ManagedOnlineEndpoint
import datetime

endpoint_name = "sklearn-diabetes-" + datetime.datetime.now().strftime("%m%d%H%M%f")

# create an online endpoint
endpoint = ManagedOnlineEndpoint(
    name=endpoint_name,
    description="An online endpoint to generate predictions for the diabetes dataset",
    auth_mode="key",
    tags={"env": "dev"},
)

ml_client.begin_create_or_update(endpoint)
```

In the code above, `auth_mode="key"` means Azure ML API keys will be used for authentication when calling the endpoint. Other options include `aml_token` and `aad_token`. Since API keys do not expire automatically, their security level is relatively lower, so they are generally more suitable for development and testing scenarios.

After that, you can see the endpoint in your workspace:

![[Pasted image 20260517221019.png]]

One thing worth noting: before you create an endpoint in Azure ML, your Azure subscription must register two additional resource providers, `Microsoft.Cdn` and `Microsoft.PolicyInsights`. Otherwise, endpoint creation will fail.

## Create the `Deployment`

As I mentioned above, an `Endpoint` manages the compute resources required to serve the model, and those concrete serving resources are represented by `Deployment`. To define a `Deployment`, we need to gather several pieces of Azure ML resource information:

- `name`: the name of the deployment. There is also a more advanced usage here. One endpoint can host multiple deployments to manage different model versions and split traffic across them. I will share more about this topic in a future article.
- `endpoint_name`: specifies which endpoint this deployment belongs to.
- `model`: specifies which model will be deployed.
- `scoring` script: this is one of the most important parts. In Azure ML, `scoring` can be understood as `inference`, which means the online inference script. This script follows Azure ML conventions and implements two methods: `init` and `run`. `init` defines what happens when the service starts, usually loading the model. `run` defines how the service responds every time it receives an online inference request. The following is the `scoring` script used in this article:

```python
import os
import logging
import json
import numpy
import joblib


def init():
    """
    This function is called when the container is initialized/started, typically after create/update of the deployment.
    You can write the logic here to perform init operations like caching the model in memory
    """
    global model

    # AZUREML_MODEL_DIR is an environment variable created during deployment.
    # It is the path to the model folder (./azureml-models/$MODEL_NAME/$VERSION)
    model_path = os.path.join(
        os.getenv("AZUREML_MODEL_DIR"), "model/sklearn_regression_model.pkl"
    )

    # deserialize the model file back into a sklearn model
    model = joblib.load(model_path)
    logging.info("Init complete")


def run(raw_data):
    """
    This function is called for every invocation of the endpoint to perform the actual scoring/prediction.
    In the example we extract the data from the json input and call the scikit-learn model's predict()
    method and return the result back
    """
    logging.info("Request received")
    data = json.loads(raw_data)["data"]
    data = numpy.array(data)
    result = model.predict(data)
    logging.info("Request processed")
    return result.tolist()
```

- `environment`: the software environment required to run the model, usually defined through a Docker image. For a more detailed explanation of `environment`, you can refer to the previous article. Here, we first create a custom environment named `my-env` based on a Microsoft-provided base image.

```python
env = Environment(
    name="my-env"

    conda_file="../model-1/environment/conda.yaml",
    image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04:latest",
)
ml_client.environments.create_or_update(env_docker_image)
```

- `instance`: this specifies the `compute` resource. Usually, we use `instance_type` to choose the VM size and `instance_count` to choose the number of instances. If you want more details about `compute`, you can also refer to the previous article.

Now the resources required for deployment are ready. Next step, let's create the `deployment`:

```python
model = "azureml:my-model:1"
env = "azureml:my-env:1"
endpoint_name = "sklearn-diabetes-05141720427035"

blue_deployment_with_registered_assets = ManagedOnlineDeployment(
    name="blue",
    endpoint_name=endpoint_name,
    model=model,
    environment=env,
    code_configuration=CodeConfiguration(
        code="../model-1/onlinescoring", scoring_script="score.py"
    ),
    instance_type="Standard_D2as_v4",
    instance_count=1,
)
ml_client.online_deployments.begin_create_or_update(blue_deployment_with_registered_assets)
```

After the deployment succeeds, we can see the resources created under the endpoint.

![[Pasted image 20260518091031.png]]

## Online Inference

The `Endpoint` exposes a URL like this:

`https://sklearn-diabetes-05141720427035.eastus2.inference.ml.azure.com/score`

You can call it by using an API key.

![[Pasted image 20260518091846.png]]

Of course, we can also send an online inference request by using the Azure SDK. In this example, the request payload is stored in a JSON file:

```python
ml_client.online_endpoints.invoke(
    endpoint_name=endpoint_name,
    deployment_name="blue",
    request_file="../model-1/sample-request.json",
)
```

At this point, we have finished the second half of the story: we successfully deployed the model online and invoked it for inference.

## The Technical Mechanism Behind Online Inference

As we discussed above, when deploying a model, we also need to prepare a `scoring` script, which is the code shown earlier. A natural follow-up question is: how exactly does that `scoring` script work behind the scenes?

Here we need to introduce an important component: `azureml inference server`. It is the startup entry point for most Azure ML base images. In essence, it is an HTTP service that dynamically loads the submitted `scoring` script as a Python module. That way, when a user sends an inference request to the `score` endpoint, the service can call the `run` method in the `scoring` script to process the request. If you want to dig deeper, you can check its GitHub repository: https://github.com/microsoft/azureml-inference-server

## Summary

In this post, I shared what I learned about the second half of the Azure ML workflow: taking a trained model, registering it, exposing an endpoint, defining a deployment, and finally sending an online inference request. If you are just getting started with Azure ML, understanding this serving path will help you connect model training with real production-style usage. I will share more about related topics, such as MLflow models or multi-deployment traffic routing, in coming articles.

---

I'm Chris Bao, a Microsoft Certified Trainer focused on the Azure AI platform. I specialize in Azure AI services and agent development, and I provide training and consulting services for both enterprises and individuals.  
For collaboration, please contact: baoqger@gmail.com
