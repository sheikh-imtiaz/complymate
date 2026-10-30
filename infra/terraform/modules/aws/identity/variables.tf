variable "name" { type = string }
variable "domain_prefix" {
  description = "Cognito hosted UI prefix (<prefix>.auth.<region>.amazoncognito.com)"
  type        = string
}
variable "web_callback_urls" { type = list(string) }
variable "web_logout_urls" { type = list(string) }
variable "admin_callback_urls" { type = list(string) }
variable "admin_logout_urls" { type = list(string) }
variable "deletion_protection" {
  type    = bool
  default = true
}
variable "advanced_security" {
  description = "Cognito threat protection (adaptive auth, compromised credentials). Extra cost."
  type        = bool
  default     = false
}
variable "ses_identity_arn" {
  type    = string
  default = null
}
variable "email_from" {
  type    = string
  default = null
}
