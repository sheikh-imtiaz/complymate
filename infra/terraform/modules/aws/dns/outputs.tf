output "zone_id" { value = data.aws_route53_zone.this.zone_id }
output "edge_certificate_arn" { value = aws_acm_certificate_validation.edge.certificate_arn }
output "ses_identity_arn" { value = aws_sesv2_email_identity.domain.arn }
output "ses_configuration_set" { value = aws_sesv2_configuration_set.this.configuration_set_name }
