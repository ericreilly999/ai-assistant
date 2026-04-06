variable "zone_id" {
  type        = string
  description = "Route53 hosted zone ID"
}

variable "domain_name" {
  type        = string
  description = "Domain name for the main A record"
}

variable "api_gateway_domain_name" {
  type        = string
  description = "API Gateway domain name (for alias record)"
  default     = null
}

variable "api_gateway_zone_id" {
  type        = string
  description = "API Gateway zone ID (for alias record)"
  default     = null
}

variable "additional_records" {
  type        = map(object({
    name    = string
    type    = string
    ttl     = number
    records = list(string)
  }))
  description = "Additional Route53 records to create"
  default     = {}
}
