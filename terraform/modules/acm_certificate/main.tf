# ACM Certificate for HTTPS/TLS
resource "aws_acm_certificate" "this" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  subject_alternative_names = var.subject_alternative_names

  lifecycle {
    create_before_destroy = true
  }

  tags = var.tags
}

# Validate the certificate using DNS (requires Route53 zone)
resource "aws_acm_certificate_validation" "this" {
  count           = var.validate_certificate ? 1 : 0
  certificate_arn = aws_acm_certificate.this.arn

  timeouts {
    create = "5m"
  }

  depends_on = [aws_route53_record.validation]
}

# Route53 records for DNS validation
resource "aws_route53_record" "validation" {
  for_each = var.validate_certificate && var.zone_id != null ? {
    for dvo in aws_acm_certificate.this.domain_validation_options : dvo.domain => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = var.zone_id
}
