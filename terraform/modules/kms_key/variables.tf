variable "name" {
  type        = string
  description = "Name for the KMS key alias (will be prefixed with 'alias/')"
}

variable "description" {
  type        = string
  description = "Description of the KMS key"
  default     = "KMS key for encrypting sensitive data"
}

variable "deletion_window_in_days" {
  type        = number
  description = "Number of days before the key is deleted after being scheduled"
  default     = 10
}

variable "lambda_role_arn" {
  type        = string
  description = "ARN of the Lambda execution role (optional, for granting permissions)"
  default     = null
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to the key"
  default     = {}
}
