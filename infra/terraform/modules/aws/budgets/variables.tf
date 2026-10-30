variable "name" { type = string }
variable "emails" { type = list(string) }
variable "monthly_limit_usd" {
  type    = number
  default = 500
}
variable "bedrock_limit_usd" {
  type    = number
  default = 200
}
