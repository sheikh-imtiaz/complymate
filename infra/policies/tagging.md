# Tagging policy

Every resource carries these tags (AWS `default_tags`, Azure resource group `tags`):

| Tag | Values | Purpose |
|---|---|---|
| `Project` | `complymate` | Cost allocation, SCP scoping |
| `Environment` | `dev`, `staging`, `prod` | Budgets, access policies |
| `ManagedBy` | `terraform` | Drift detection — anything without it was created by hand |
| `DataResidency` | `AU` (or `NZ`) | Confirms tenant data stays in-country |
| `Stack` | `global` (bootstrap only) | Separates the state/OIDC bootstrap stack |

Rules:

* Activate `Project` and `Environment` as AWS cost allocation tags in the payer account.
* An AWS Organizations tag policy should enforce allowed values for `Environment` and `DataResidency`.
* Never put personal information or tenant names in tags (tags are visible in billing exports).
