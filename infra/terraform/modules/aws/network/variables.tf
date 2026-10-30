variable "name" { type = string }
variable "region" { type = string }
variable "cidr" {
  type    = string
  default = "10.40.0.0/16"
}
variable "az_count" {
  type    = number
  default = 2
}
variable "enable_nat_gateway" {
  description = "One NAT gateway for internet egress (Stripe API, sanctions list downloads). Set false to rely on VPC endpoints only."
  type        = bool
  default     = true
}
variable "endpoint_services" {
  description = "Interface endpoints to create (each costs ~US$8/month per AZ)."
  type        = list(string)
  default     = ["secretsmanager", "sqs", "kms", "bedrock-runtime"]
}
