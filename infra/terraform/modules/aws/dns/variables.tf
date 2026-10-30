variable "name" { type = string }
variable "zone_name" { type = string }
variable "api_domain" { type = string }
variable "email_domain" { type = string }
variable "cloudfront_domain" {
  type    = string
  default = null
}
variable "cloudfront_zone_id" {
  type    = string
  default = null
}
