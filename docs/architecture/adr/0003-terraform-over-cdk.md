# ADR 0003: Terraform instead of AWS CDK

* Status: accepted
* Date: 2026-10-30

## Decision
Terraform 1.9 (OpenTofu compatible) with `modules/aws/*`, `modules/azure/*` and per-environment stacks in
`envs/`. State in S3 + DynamoDB lock (AWS) and Azure Storage (Azure). CI uses GitHub OIDC; no stored cloud keys.

## Consequences
* One IaC language and review process for both clouds; Checkov scans both.
* Some AWS-specific conveniences of CDK (asset bundling) are replaced by the container image built in CI.
