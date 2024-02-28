# Setting up AWS authentication for CI/CD using OIDC

## Why?

Remove reliance on long-lived keys for AWS access with on-demand temporary access.

## Setup

We create an OIDC identity provider in AWS:

Our primary use-cases are:

- Publishing image builds to ECR
- Uploading static content to CDN
- Running Terraform
- Execute actions in EKS


## Provisioning permissions

## EKS