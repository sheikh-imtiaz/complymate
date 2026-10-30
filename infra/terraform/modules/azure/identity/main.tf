terraform {
  required_providers {
    azuread = { source = "hashicorp/azuread", version = "~> 3.0" }
  }
}

# The Entra External ID (customer) tenant is created once in the portal; the azuread provider for this module
# points at it. MFA is enforced with a Conditional Access policy in that tenant (see docs/architecture/azure.md).
resource "azuread_application" "web" {
  display_name     = "${var.name}-web"
  sign_in_audience = "AzureADMyOrg"
  single_page_application {
    redirect_uris = var.web_redirect_uris
  }
  api {
    requested_access_token_version = 2
  }
  optional_claims {
    id_token {
      name = "email"
    }
    id_token {
      name = "auth_time"
    }
  }
}

resource "azuread_application" "admin" {
  display_name     = "${var.name}-platform-admin"
  sign_in_audience = "AzureADMyOrg"
  single_page_application {
    redirect_uris = var.admin_redirect_uris
  }
  optional_claims {
    id_token {
      name = "email"
    }
    id_token {
      name = "auth_time"
    }
  }
}

resource "azuread_service_principal" "web" {
  client_id = azuread_application.web.client_id
}

resource "azuread_service_principal" "admin" {
  client_id = azuread_application.admin.client_id
}
