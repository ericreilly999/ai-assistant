variable "name_prefix" {
  type = string
}

variable "secret_names" {
  type = set(string)
}

variable "kms_key_arn" {
  type        = string
  description = "ARN of the KMS key used to encrypt secrets at rest (optional; defaults to aws/secretsmanager)"
  default     = null
}

variable "tags" {
  type    = map(string)
  default = {}
}
