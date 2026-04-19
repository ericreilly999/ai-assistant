variable "function_name" {
  type = string
}

variable "handler" {
  type = string
}

variable "runtime" {
  type = string
}

variable "filename" {
  type = string
}

variable "source_code_hash" {
  type = string
}

variable "timeout" {
  type    = number
  default = 30
}

variable "memory_size" {
  type    = number
  default = 512
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "additional_policy_json" {
  type    = string
  default = ""
}

variable "has_additional_policy" {
  description = "Set to true when additional_policy_json is provided."
  type        = bool
  default     = false
}

variable "managed_policy_arns" {
  type    = set(string)
  default = []
}

variable "kms_key_arn" {
  type        = string
  description = "ARN of the KMS key used to encrypt Lambda environment variables and the CloudWatch log group. When null, AWS-managed encryption is used."
  default     = null
}

variable "tags" {
  type    = map(string)
  default = {}
}
