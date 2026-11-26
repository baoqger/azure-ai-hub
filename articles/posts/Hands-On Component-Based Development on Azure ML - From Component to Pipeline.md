---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - Azure ML
title: Hands-On Component-Based Development on Azure ML - From Component to Pipeline
---
#azure #azureai #machinelearning

## Background

In my previous two articles, I shared how to train a machine learning model on Azure ML and deploy it as a public endpoint for online inference. After reading those posts, you should already have a basic understanding of several important resources in Azure ML.

In this article, I will share what I learned as I took one step further and started exploring Azure ML Pipelines in a hands-on way. This is also a good starting point for later topics such as MLOps and Automated ML.

## Why Do We Need Azure ML Pipelines?

As we mentioned above, a machine learning workflow is usually a complex multi-step process. Naturally, we want to break the full workflow into smaller components that can be developed and managed independently. When these components are connected together, they form a pipeline. This design brings several direct benefits:

- Higher training efficiency and lower cost: by reusing small components in a pipeline, we can avoid repeated work. Reusing outputs produced by existing components can also improve the overall execution efficiency.
- A solid foundation for MLOps: with a component-based design, it becomes much easier to automate the entire pipeline, which makes future MLOps practices much easier to implement.

Next, let's walk through a concrete example and build a component-based ML pipeline together.

## Building an Azure ML Pipeline

In this article, we will train a credit card default prediction model together. Before we build the pipeline itself, let's first prepare the data source and runtime environment.

### Data Preparation

In one of my previous articles, I introduced the data module in Azure ML, specifically `Datastores`. Today, let's use `Data Assets` instead. For example, with the following code, we can upload a CSV file as a Data Asset named `credit-card`.

```python
from azure.ai.ml.entities import Data
from azure.ai.ml.constants import AssetTypes

# Update the 'my_path' variable to match the location of where you downloaded the data on your
# local filesystem
my_path = "./data/default_of_credit_card_clients.csv"

# Set the version number of the data asset
v1 = "initial"

my_data = Data(
    name="credit-card",
    version=v1,
    description="Credit card data",
    path=my_path,
    type=AssetTypes.URI_FILE,
)

## Create data asset if it doesn't already exist:
try:
    data_asset = ml_client.data.get(name="credit-card", version=v1)
    print(
        f"Data asset already exists. Name: {my_data.name}, version: {my_data.version}"
    )
except:
    ml_client.data.create_or_update(my_data)
    print(f"Data asset created. Name: {my_data.name}, version: {my_data.version}")
```

After the Data Asset is created successfully, the result looks like this. In essence, you can see that it is stored in the Azure Blob Storage associated with the Azure ML workspace.

![[Pasted image 20260521112445.png]]

### Environment Setup

`Environment` in Azure ML provides the runtime dependencies required by jobs and models. In the same way, each component in a pipeline also needs its own environment. Of course, different components in the same pipeline can use different environments as well.

Here, we create a custom environment as follows:

```python
from azure.ai.ml.entities import Environment

dependencies_dir = "./dependencies"
custom_env_name = "aml-scikit-learn"

pipeline_job_env = Environment(
    name=custom_env_name,
    description="Custom environment for Credit Card Defaults pipeline",
    tags={"scikit-learn": "0.24.2"},
    conda_file=os.path.join(dependencies_dir, "conda.yaml"),
    image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu22.04:latest",
    version="0.4.0",
)

pipeline_job_env = ml_client.environments.create_or_update(pipeline_job_env)

print(
    f"Environment with name {pipeline_job_env.name} is registered to workspace, the environment version is {pipeline_job_env.version}"
)
```

```yaml
name: model-env

channels:
  - conda-forge

dependencies:
  - python=3.10
  - pip
  - numpy=1.23.5
  - scipy=1.10.1
  - pandas=1.5.3
  - scikit-learn=1.2.2
  - pip:
      - inference-schema[numpy-support]==1.3.0
      - xlrd==2.0.1
      - mlflow==2.4.1
      - azureml-mlflow==1.51.0
```

![[Pasted image 20260521115554.png]]

Once the data and environment are ready, we can move on to the pipeline itself.

### Azure ML Components

As mentioned above, an Azure ML pipeline is composed of multiple small building blocks, and these blocks correspond to the `Component` resource type in Azure ML. Azure ML supports two ways to create a component:

- Python script: define a component programmatically with Python code.
- YAML file: define a component declaratively with YAML.

The core elements of a component mainly include the following three parts:

- Metadata, such as component name, version, and type.
- Interface, which means the component inputs and outputs.
- Runtime code and environment.

In this article, we can split the training process for the credit card default prediction model into two components: `data preparation` and `model training`. Next, let's define these two components using a Python script and a YAML file respectively.

### A Component Defined with a Python Script

For the first `data preparation` component, we will define and register it with a Python script. Let's first look at the logic of this component: read the raw CSV file and then split it into a training set and a validation set.

```python
import os
import argparse
import pandas as pd
from sklearn.model_selection import train_test_split
import logging
import mlflow


def main():
    """Main function of the script."""

    # input and output arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, help="path to input data")
    parser.add_argument("--test_train_ratio", type=float, required=False, default=0.25)
    parser.add_argument("--train_data", type=str, help="path to train data")
    parser.add_argument("--test_data", type=str, help="path to test data")
    args = parser.parse_args()

    # Start Logging
    mlflow.start_run()

    print(" ".join(f"{k}={v}" for k, v in vars(args).items()))
    print("input data:", args.data)

    credit_df = pd.read_csv(args.data, header=1, index_col=0)

    mlflow.log_metric("num_samples", credit_df.shape[0])
    mlflow.log_metric("num_features", credit_df.shape[1] - 1)

    credit_train_df, credit_test_df = train_test_split(
        credit_df,
        test_size=args.test_train_ratio,
    )

    # output paths are mounted as folder, therefore, we are adding a filename to the path
    credit_train_df.to_csv(os.path.join(args.train_data, "data.csv"), index=False)
    credit_test_df.to_csv(os.path.join(args.test_data, "data.csv"), index=False)

    # Stop Logging
    mlflow.end_run()


if __name__ == "__main__":
    main()
```

We can package this script into a component with the following code:

```python
from azure.ai.ml import command
from azure.ai.ml import Input, Output

data_prep_component = command(
    name="data_prep_credit_defaults",
    display_name="Data preparation for training",
    description="reads a .xl input, split the input to train and test",
    inputs={
        "data": Input(type="uri_folder"),
        "test_train_ratio": Input(type="number"),
    },
    outputs=dict(
        train_data=Output(type="uri_folder", mode="rw_mount"),
        test_data=Output(type="uri_folder", mode="rw_mount"),
    ),
    # The source folder of the component
    code=data_prep_src_dir,
    command="""python data_prep.py \
            --data ${{inputs.data}} --test_train_ratio ${{inputs.test_train_ratio}} \
            --train_data ${{outputs.train_data}} --test_data ${{outputs.test_data}} \
            """,
    environment=f"{pipeline_job_env.name}:{pipeline_job_env.version}",
)

# Now register the component to the workspace
data_prep_component = ml_client.create_or_update(data_prep_component.component)

# Create and register the component in your workspace
print(
    f"Component {data_prep_component.name} with Version {data_prep_component.version} is registered"
)
```

Notice that this component uses the custom `Environment` we created just now.

### A Component Defined with a YAML File

The second `model training` component is defined with a YAML specification. Let's first look at the training script:

```python
import argparse
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report
import os
import pandas as pd
import mlflow


def select_first_file(path):
    """Selects first file in folder, use under assumption there is only one file in folder
    Args:
        path (str): path to directory or file to choose
    Returns:
        str: full path of selected file
    """

    files = os.listdir(path)
    return os.path.join(path, files[0])


# Start Logging
mlflow.start_run()

# enable autologging
mlflow.sklearn.autolog()

os.makedirs("./outputs", exist_ok=True)


def main():
    """Main function of the script."""

    # input and output arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_data", type=str, help="path to train data")
    parser.add_argument("--test_data", type=str, help="path to test data")
    parser.add_argument("--n_estimators", required=False, default=100, type=int)
    parser.add_argument("--learning_rate", required=False, default=0.1, type=float)
    parser.add_argument("--registered_model_name", type=str, help="model name")
    parser.add_argument("--model", type=str, help="path to model file")
    args = parser.parse_args()

    # paths are mounted as folder, therefore, we are selecting the file from folder
    train_df = pd.read_csv(select_first_file(args.train_data))

    # Extracting the label column
    y_train = train_df.pop("default payment next month")

    # convert the dataframe values to array
    X_train = train_df.values

    # paths are mounted as folder, therefore, we are selecting the file from folder
    test_df = pd.read_csv(select_first_file(args.test_data))

    # Extracting the label column
    y_test = test_df.pop("default payment next month")

    # convert the dataframe values to array
    X_test = test_df.values

    print(f"Training with data of shape {X_train.shape}")

    clf = GradientBoostingClassifier(
        n_estimators=args.n_estimators, learning_rate=args.learning_rate
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred))

    # Registering the model to the workspace
    print("Registering the model via MLFlow")
    mlflow.sklearn.log_model(
        sk_model=clf,
        registered_model_name=args.registered_model_name,
        artifact_path=args.registered_model_name,
    )

    # Saving the model to a file
    mlflow.sklearn.save_model(
        sk_model=clf,
        path=os.path.join(args.model, "trained_model"),
    )

    # Stop Logging
    mlflow.end_run()


if __name__ == "__main__":
    main()
```

And here is the corresponding YAML file:

```yaml
# <component>
name: train_credit_defaults_model
display_name: Train Credit Defaults Model
# version: 1 # Not specifying a version will automatically update the version
type: command

inputs:
  train_data:
    type: uri_folder
  test_data:
    type: uri_folder
  learning_rate:
    type: number
  registered_model_name:
    type: string

outputs:
  model:
    type: uri_folder

code: .

environment:
  # for this step, we'll use an AzureML curate environment
  azureml://registries/azureml/environments/sklearn-1.0/labels/latest

command: >-
  python train.py
  --train_data ${{inputs.train_data}}
  --test_data ${{inputs.test_data}}
  --learning_rate ${{inputs.learning_rate}}
  --registered_model_name ${{inputs.registered_model_name}}
  --model ${{outputs.model}}
# </component>
```

As you can see, this component uses the Azure ML curated environment `sklearn-1.0`.

After the component is registered successfully, the result looks like this:

![[Pasted image 20260521134328.png]]

## Building the Pipeline

The Azure ML SDK provides the `@dsl.pipeline` decorator to define a pipeline. In this pipeline, we invoke each component in sequence. Each component has inputs and outputs, so you can think of it almost like a method call. The output of an earlier component becomes the input of a later one. In addition, this pipeline job runs with `serverless` compute, which saves us from managing compute resources ourselves. Smart design, right?

```python
# the dsl decorator tells the sdk that we are defining an Azure Machine Learning pipeline
from azure.ai.ml import dsl, Input, Output


@dsl.pipeline(
    compute="serverless",  # "serverless" value runs pipeline on serverless compute
    description="E2E data_perp-train pipeline",
)
def credit_defaults_pipeline(
    pipeline_job_data_input,
    pipeline_job_test_train_ratio,
    pipeline_job_learning_rate,
    pipeline_job_registered_model_name,
):
    # using data_prep_function like a python call with its own inputs
    data_prep_job = data_prep_component(
        data=pipeline_job_data_input,
        test_train_ratio=pipeline_job_test_train_ratio,
    )

    # using train_func like a python call with its own inputs
    train_job = train_component(
        train_data=data_prep_job.outputs.train_data,  # note: using outputs from previous step
        test_data=data_prep_job.outputs.test_data,  # note: using outputs from previous step
        learning_rate=pipeline_job_learning_rate,  # note: using a pipeline input as parameter
        registered_model_name=pipeline_job_registered_model_name,
    )

    # a pipeline returns a dictionary of outputs
    # keys will code for the pipeline output identifier
    return {
        "pipeline_job_train_data": data_prep_job.outputs.train_data,
        "pipeline_job_test_data": data_prep_job.outputs.test_data,
    }


registered_model_name = "credit_defaults_model"

# Let's instantiate the pipeline with the parameters of our choice
pipeline = credit_defaults_pipeline(
    pipeline_job_data_input=Input(type="uri_file", path=credit_data.path),
    pipeline_job_test_train_ratio=0.25,
    pipeline_job_learning_rate=0.05,
    pipeline_job_registered_model_name=registered_model_name,
)

# submit the pipeline job
pipeline_job = ml_client.jobs.create_or_update(
    pipeline,
    # Project's name
    experiment_name="e2e_registered_components",
)
```

At this point, we get the following pipeline:

![[Pasted image 20260521135613.png]]

## Summary

In this article, I shared what I learned while building a component-based Azure ML pipeline. We started with data and environment preparation, then defined two components in different ways, and finally connected them into a complete pipeline.

After reading this post, you should have a clearer understanding of:

- why Azure ML Pipelines matter,
- how Azure ML Components are defined,
- how to combine components into a reusable pipeline,
- and how this design prepares you for more advanced topics such as MLOps.

I will continue sharing more Azure AI and Azure ML hands-on topics in future articles.

---

I'm Chris Bao, a Microsoft Certified Trainer focused on the Azure AI platform. I specialize in Azure AI services and agent development, and I provide training and consulting services for enterprises and individuals.
For collaboration, feel free to contact me at: baoqger@gmail.com
