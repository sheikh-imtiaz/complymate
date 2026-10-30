variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "deploy_openai_chat" {
  type    = bool
  default = false
}
variable "chat_model" {
  type    = string
  default = "gpt-4o"
}
variable "chat_model_version" {
  type    = string
  default = "2024-11-20"
}
