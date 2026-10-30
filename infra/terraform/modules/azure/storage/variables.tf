variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "replication" {
  type    = string
  default = "ZRS"
}
variable "audit_retention_days" {
  type    = number
  default = 2557
}
variable "lock_audit_policy" {
  description = "Locking is irreversible. Leave false in staging."
  type        = bool
  default     = false
}
variable "restrict_network" {
  type    = bool
  default = false
}
