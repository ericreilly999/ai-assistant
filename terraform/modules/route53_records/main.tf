# Route53 A record pointing to API Gateway
resource "aws_route53_record" "api_gateway" {
  count   = var.api_gateway_domain_name != null ? 1 : 0
  zone_id = var.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = var.api_gateway_domain_name
    zone_id                = var.api_gateway_zone_id
    evaluate_target_health = true
  }
}

# Additional CNAME records if specified
resource "aws_route53_record" "additional" {
  for_each = var.additional_records

  zone_id = var.zone_id
  name    = each.value.name
  type    = each.value.type
  ttl     = each.value.ttl
  records = each.value.records
}
