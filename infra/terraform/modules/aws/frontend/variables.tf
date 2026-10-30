variable "name" { type = string }
variable "repository_url" { type = string }
variable "github_access_token" {
  description = "GitHub token Amplify uses to connect the repository (store in TF_VAR_github_access_token)"
  type        = string
  sensitive   = true
}
variable "branch" {
  type    = string
  default = "main"
}
variable "stage" {
  type    = string
  default = "DEVELOPMENT"
}
variable "zone_name" {
  type    = string
  default = null
}
variable "web_domain" {
  type    = string
  default = null
}
variable "admin_domain" {
  type    = string
  default = null
}
variable "web_client_id" { type = string }
variable "admin_client_id" { type = string }
variable "common_env" { type = map(string) }
