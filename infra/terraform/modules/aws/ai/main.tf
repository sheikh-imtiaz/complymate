terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.80" }
  }
}

# Bedrock Guardrails: blocks tipping-off assistance and personal legal advice, filters harmful content and
# anonymises identity numbers. App-level guardrails (agent/guardrails.py) apply on every cloud.
# Note: enable model access for Claude Sonnet/Haiku and Titan Embeddings v2 in the Bedrock console first.
resource "aws_bedrock_guardrail" "this" {
  name                      = var.name
  blocked_input_messaging   = "I can't help with that request. Please speak to your AML/CTF compliance officer."
  blocked_outputs_messaging = "I can't provide that answer. Please check the regulator's guidance or ask your compliance officer."
  description               = "ComplyMate Ask the Rules guardrail"

  content_policy_config {
    filters_config {
      type            = "HATE"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "VIOLENCE"
      input_strength  = "MEDIUM"
      output_strength = "MEDIUM"
    }
    filters_config {
      type            = "MISCONDUCT"
      input_strength  = "MEDIUM"
      output_strength = "MEDIUM"
    }
    filters_config {
      type            = "PROMPT_ATTACK"
      input_strength  = "HIGH"
      output_strength = "NONE"
    }
  }

  topic_policy_config {
    topics_config {
      name       = "TippingOff"
      type       = "DENY"
      definition = "Helping someone tell a customer or any outside person that a suspicious matter report has been or may be made, or drafting such a communication."
      examples   = ["Write an email telling my client we reported them to AUSTRAC", "How can I warn the customer about the SMR?"]
    }
    topics_config {
      name       = "EvadingAMLControls"
      type       = "DENY"
      definition = "Advice on structuring transactions, hiding beneficial ownership or otherwise evading AML/CTF or sanctions controls."
      examples   = ["How do I split cash deposits to avoid reporting?", "How can a sanctioned person hide behind a trust?"]
    }
  }

  sensitive_information_policy_config {
    pii_entities_config {
      type   = "DRIVER_ID"
      action = "ANONYMIZE"
    }
    regexes_config {
      name        = "AU_TFN"
      description = "Australian tax file number"
      pattern     = "\\b\\d{3}\\s?\\d{3}\\s?\\d{2,3}\\b"
      action      = "ANONYMIZE"
    }
    regexes_config {
      name        = "AU_MEDICARE"
      description = "Australian Medicare card number"
      pattern     = "\\b[2-6]\\d{3}\\s?\\d{5}\\s?\\d{1,2}\\b"
      action      = "ANONYMIZE"
    }
    regexes_config {
      name        = "PASSPORT"
      description = "Passport-like document numbers"
      pattern     = "\\b[A-Z]{1,2}\\d{7}\\b"
      action      = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "CREDIT_DEBIT_CARD_NUMBER"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "PASSWORD"
      action = "BLOCK"
    }
  }
}

resource "aws_bedrock_guardrail_version" "this" {
  guardrail_arn = aws_bedrock_guardrail.this.guardrail_arn
  description   = "managed by terraform"
}
