A simple container orchestration platform. Takes shape via two underlying types of infrastructure: EC2 and Fargate.

- EC2: you provision and manage instances including setup, maintenance, updates, patches. ECS is only responsible for managing the containers running on these instances
- Fargate: ECS manages the infrastructure. As capacity is needed, resources are automatically provisioned on-demand. ECS then deploys containers onto these servers. Pay for what you use!

## Components

Task Definitions: similar to docker-compose file,

