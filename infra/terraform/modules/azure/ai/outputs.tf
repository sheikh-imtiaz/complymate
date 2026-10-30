output "openai_endpoint" { value = azurerm_cognitive_account.openai.endpoint }
output "openai_id" { value = azurerm_cognitive_account.openai.id }
output "docintel_endpoint" { value = azurerm_cognitive_account.docintel.endpoint }
output "docintel_id" { value = azurerm_cognitive_account.docintel.id }
output "embedding_deployment" { value = azurerm_cognitive_deployment.embeddings.name }
