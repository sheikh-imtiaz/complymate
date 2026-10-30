variable "name" { type = string }
variable "audit_retention_years" {
  type    = number
  default = 7
}
variable "force_destroy" {
  description = "Allow destroying non-empty document/export buckets (dev only). The audit bucket is never force-destroyed."
  type        = bool
  default     = false
}
variable "allowed_origins" {
  type    = list(string)
  default = []
}
