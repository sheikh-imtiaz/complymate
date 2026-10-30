# subscription_id, external_id_tenant_id and images come from CI (TF_VAR_*).
location          = "australiaeast"
vnet_cidr         = "10.51.0.0/16"
db_sku            = "B_Standard_B2ms"
oidc_issuer       = "https://complymatestaging.ciamlogin.com/00000000-0000-0000-0000-000000000000/v2.0"
web_url           = "https://app.staging.complymate.example"
admin_url         = "https://admin.staging.complymate.example"
email_from        = "no-reply@staging.complymate.example"
monthly_budget    = 600
budget_start_date = "2026-11-01T00:00:00Z"
