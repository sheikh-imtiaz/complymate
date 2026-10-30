resource "aws_route53_record" "api" {
  count   = var.cloudfront_domain == null ? 0 : 1
  zone_id = data.aws_route53_zone.this.zone_id
  name    = var.api_domain
  type    = "A"
  alias {
    name                   = var.cloudfront_domain
    zone_id                = var.cloudfront_zone_id
    evaluate_target_health = false
  }
}
