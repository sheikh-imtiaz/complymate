variable "name" { type = string }
variable "origin_domain" {
  description = "HTTP API domain (xxxx.execute-api.ap-southeast-2.amazonaws.com)"
  type        = string
}
variable "api_domain" {
  type    = string
  default = null
}
variable "certificate_arn" {
  description = "ACM certificate in us-east-1 for api_domain"
  type        = string
  default     = null
}
variable "rate_limit_per_5min" {
  type    = number
  default = 2000
}
