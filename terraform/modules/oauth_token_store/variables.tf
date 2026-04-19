variable "name_prefix" {
  type        = string
  description = "Prefix applied to the DynamoDB table name (result: <name_prefix>-tokens)"
}

variable "kms_key_arn" {
  type        = string
  description = "ARN of the KMS Customer Managed Key used for DynamoDB server-side encryption"

  validation {
    condition     = can(regex("^arn:aws:kms:", var.kms_key_arn))
    error_message = "kms_key_arn must be a valid KMS key ARN starting with 'arn:aws:kms:'"
  }
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to the DynamoDB table"
  default     = {}
}
