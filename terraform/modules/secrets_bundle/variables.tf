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

variable "recovery_window_in_days" {
  type        = number
  description = "Number of days before a deleted secret is permanently removed. Use 0 for dev (immediate), 7+ for staging/prod."
  default     = 0

  validation {
    condition     = var.recovery_window_in_days == 0 || (var.recovery_window_in_days >= 7 && var.recovery_window_in_days <= 30)
    error_message = "recovery_window_in_days must be 0 (immediate deletion) or between 7 and 30 (AWS Secrets Manager constraint)."
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}
