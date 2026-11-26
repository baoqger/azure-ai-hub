---
date: 2026-09-10
authors:
  - chris-bao
categories:
  - Azure ML
title: Azure Machine Learning 101 - Workspace, Job, Compute, Environment, Datastore
---
#azure #azureai #machinelearning 

- Azure ML environment, there are two types of environments in Azure ML: curated and custom. 
	- curated 
		- provided by Azure Machine Learning. 
		- they're backed by cached Docker images
	- custom
- multiple ways to submit ML training jobs. 
	- Az CLI extension for machine learning
	- python SDK
	- REST API
 - compute resource
	 - Compute instances
		 - a selection of CPU or GPU instances preconfigured with popular tools such as VS Code, Jupyter and RStudio, ML packages, deep learning frameworks, and GPU drivers. 
	 - Compute clusters
		 - create a single or multi node `computer cluster` for your training, batching inferencing or reinforcement learning workloads
		 - you can use Azure ML `computer cluster` to distribute a training or batch inference process across a cluster of CPU or GPU compute nodes in the cloud. 
	 - K8S clusters
	 - Attached computes
	 - Serverless instances

--- 



- although Jupyter notebooks are valuable for experimentation and exploration in an interactive development workflow on a single device, they are not designed for production or distribution. 
- Training jobs become essential in the ML workflow at this stage by deploying the task to multiple cloud instances in order to run for a longer time, and process mode data. 
- this requires setting up the data, code, compute instances and runtime environments to ensure consistent outputs when it is no longer executed on one local machine. 
- Think of it like the difference between developing a dinner recipe (Jupyter notebook) and hiring a catering team to cook it for 500 customers(ML job). It needs everyone in the catering team to access the same ingredients, recipe and tools, following the same cooking procedure. 

on azure ml, you need the following script to submit a training job: 


```python
from azure.ai.ml import command

job = command(
    code=...
    command=...
    environment=...
    compute=...
)

ml_client.jobs.create_or_update(job)
```

this training job can be broken down into the following dimensions: 
![[Pasted image 20260511145539.png|413]]
- Project and Permission Management
	- project management in Azure ML is `workspace-centric`, starting by creating a workspace for storing relevant resource and assets, and shared across the project team for collaboration.
	- permissions to access and manage resources are granted at the user-level based on their roles (RBAC). 比如 `AzureML Data Scientist` and  `AzureML Compute Operator` 
	- The objectives of setting up an Azure ML Workspace is to create a contained environments for storing data, compute, model and other resources, so that only users within the Workspace are given relevant access to read or edit the data assets. 

![[Pasted image 20260511150643.png]]
- Upon workspace creation, associated services like `Azure Storage Account`  and `Azure Key Vault` are also instantiated automatically!
- when developers run the code during an interactive dev session, the workspace connection is authenticated through the developer's personal credentials. 
- they would be able to create a training job using the command `ml_client.jobs.create_or_update(job)` 
- to detach personal account credentials in the production environment, it is recommended to use a service principal account to authenticate for automated pipelines or scheduled jobs.  
Note: AzureML的workspace就是它的管理单元! 


- Data Storage
	- you may have the question  - can i store the data in the working directory? at least that's been my question for a long time, and I believe the answer is still yes if you are experimenting or prototyping using a simple script or notebook in an interactive dev environment. 
	- but data storage location is important to consider in the context of creating ML jobs. 
	- since code runs in a cloud-managed environment or a docker container separate from your local directory, any locally stored data cannot be accessed when executing pipelines and  jobs in Azure ML. 
	- This requires centralized, managed data storage service. In Azure, this is handled by a storage account within the workspace that supports datastores and data assets. 
		- `datastores`: securely connect to a storage service on Azure by storing connection information. With `datastores`, you no longer need to provide credential information in your scripts to access your data. => 不用提供azure storage 的权限认证信息了. it decouples data location and access permission from the code, so that the code to remain unchanged even if the underlying data connection changes. 
		- data assets => 这个没有用上! is another option to access data in an ML job, especially when it is beneficial to keep track of multiple data versions, so data scientists can identify the correct data snapshots being used for model building or experimentations. 
	- azure ML treats data as attached resources and assets in the Workspaces, with one storage account and four build-in datastores automatically created upon the instantiation of each Workspace in order to store files (in Azure File Share) and datasets(in Azure Blob Storage). 

![[Pasted image 20260511161906.png]]

![[Pasted image 20260511162254.png]]

![[Pasted image 20260511163718.png]]

可以从上面这个snapshot看出, `workspaceblobstore`这个datastore 指向了`azureml-blobstore-653302d5-561f-4533-b17b-e5371171edde`  这个container! 

![[Pasted image 20260511163904.png]]


- Compute 
	- compute is the virtual machine where your model and code run. Along with `network` and `storage`, it is one of the fundamental building blocks of cloud computing. (云计算的三大支柱: `network`, `storage`, `compute`) 
	- compute resources typically represent the largest cost component of an ML project, as training models - especially large AI models - requires long training times and often specialized compute instances (e.g., GPU instances) with high costs. => therefore, Azure ML designs a dedicated `AzureMl Compute Operator` role for managing compute resources. 
	- computers are persistent resources in the Azure ML workspace, typically created once by the AzureML Compute Operator and reused by the data science team. 
	- Since compute resources are cost-intensive, this structure allows them to be centrally managed by a role with cloud infra expertise, while data scientists and engineers can focus on dev work. 
	- Azure offers a spectrum of compute target options designated for ML development and deployment, depending on the scale of the workload. 
		- a `compute instance` is a single node machine suitable for interactive dev and testing in Jupyter notebook env. 
		- a `computer cluster` is another type of compute target that spins up multi-node cluster machines. It can be scaled for parallel processing based on workload demand and supports `auto-scaling` by configuring the parameter `min_instances` and `max_instances`. 
		- `serverless compute`
		- `k8s clusters` 
		- `containers` 
	- to create an Azure ML managed compute target we create an `AmlCompute` object using the code below: 
		- `type`: `amlcompute` for compute cluster. `computeinstance` for single-node interactive dev; `kubernetes` for AKS clusters
		- `name`: the compute target name
		- `size`: instance size
		- `min_instances` and `max_instances` : set the range of instances allowed to run simultaneously. 
		- `idle_time_before_scale_down`: automatically shut down the compute cluster when idle to avoid incurring unnecessary costs. 

	- once the compute resource is created, anyone in the shared Workspace can use it by simply referencing its `name` in an ML job. 
	- Azure's persistent compute approach allows centralized management and sharing across multiple developers, allowing data scientists to focus on model development rather than infrastructure management. 
```python
# Create a compute cluster
cpu_cluster = AmlCompute(
    name="cpu-cluster",
    type="amlcompute",
    size="Standard_DS3_v2",
    min_instances=0,
    max_instances=4,
    idle_time_before_scale_down=120
)

# Create or update the compute
ml_client.compute.begin_create_or_update(cpu_cluster)
```


```python
# Use the persisted compute "cpu-cluster" in the job
job = command(
    code='./src',
    command='python code.py',
    compute='cpu-cluster',
    display_name='train-custom-env',
    experiment_name='training'
)
```



- Environment
	- environment defines where the code or job is running, including software, operating system, program packages, docker image and environment variables. 
	- while `compute` is responsible for the underlying `infrastructure` and `hardware` selections; `environment` setup is crucial in ensuring consistent and reproducible behaviors across dev and pro environment, mitigating package conflicts and dependency issues when executing the same code in different runtime setup by different developers. 
	- Similar to `Data` and `Compute`, `Environment` is considered a type of resource and asset in the Azure ML workspace. 
	- Azure ML offers a comprehensive list of curated environments for popular python frameworks, like `PyTorch`, `Tensorflow`,  `scikit-learn` designed for `CPU` or `GPU/CUDA` target. 
	- The code snippet below helps to retrieve the list of all curated environment in Azure ML. 
	- They generally follow a naming convention that includes the framework name, version, operating system, python version, and compute target(CPU or GPU). for example, `AzureML-sklearn-1.0-ubuntu20.04-py38-cpu` indicates `scikit-learn` version1.0, running on `Ubuntu 20.04` with `python 3.8` for `CPU` compute.
	- To run the training job in a curated environment, we create an `environment object` by reference its name and version, then passing it as a job parameter.
	- Or create a custom environment from Docker image registered in Docker Hub using the code snippet below => 没有对应的code样例
	- Azure ML does not currently offer the build-in algorithm  approach that encapsulates and packages popular machine learning algorithms directly into the environment in the same way that SageMaker does. 

```python
envs = ml_client.environments.list()
for env in envs:
    print(env.name)
    
    
# >>> Auzre ML Curated Environments
"""
AzureML-AI-Studio-Development
AzureML-ACPT-pytorch-1.13-py38-cuda11.7-gpu
AzureML-ACPT-pytorch-1.12-py38-cuda11.6-gpu
AzureML-ACPT-pytorch-1.12-py39-cuda11.6-gpu
AzureML-ACPT-pytorch-1.11-py38-cuda11.5-gpu
AzureML-ACPT-pytorch-1.11-py38-cuda11.3-gpu
AzureML-responsibleai-0.21-ubuntu20.04-py38-cpu
AzureML-responsibleai-0.20-ubuntu20.04-py38-cpu
AzureML-tensorflow-2.5-ubuntu20.04-py38-cuda11-gpu
AzureML-tensorflow-2.6-ubuntu20.04-py38-cuda11-gpu
AzureML-tensorflow-2.7-ubuntu20.04-py38-cuda11-gpu
AzureML-sklearn-1.0-ubuntu20.04-py38-cpu
AzureML-pytorch-1.10-ubuntu18.04-py38-cuda11-gpu
AzureML-pytorch-1.9-ubuntu18.04-py37-cuda11-gpu
AzureML-pytorch-1.8-ubuntu18.04-py37-cuda11-gpu
AzureML-sklearn-0.24-ubuntu18.04-py37-cpu
AzureML-lightgbm-3.2-ubuntu18.04-py37-cpu
AzureML-pytorch-1.7-ubuntu18.04-py37-cuda11-gpu
AzureML-tensorflow-2.4-ubuntu18.04-py37-cuda11-gpu
AzureML-Triton
AzureML-Designer-Score
AzureML-VowpalWabbit-8.8.0
AzureML-PyTorch-1.3-CPU
"""
```

