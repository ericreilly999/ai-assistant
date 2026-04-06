variable "domain_name" {
  type        = string
  description = "The primary domain name for the certificate"
}

variable "subject_alternative_names" {
  type        = list(string)
  description = "List of additional domain names to include in the certificate"
  default     = []
}

variable "zone_id" {
  type        = string
  description = "Route53 zone ID for DNS validation (optional)"
  default     = null
}

variable "validate_certificate" {
  type        = bool
  description = "Whether to validate the certificate using DNS validation"
  default     = false
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to the certificate"
  default     = {}
}
