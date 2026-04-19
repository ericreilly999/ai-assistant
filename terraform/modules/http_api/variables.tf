variable "name" {
  type = string
}

variable "stage_name" {
  type = string
}

variable "integration_uri" {
  type = string
}

variable "lambda_function_name" {
  type = string
}

variable "routes" {
  type = set(string)
}

variable "protected_routes" {
  type    = set(string)
  default = []
}

variable "cors_allow_origins" {
  type    = list(string)
  default = ["*"]
}

variable "authorizer_issuer" {
  type    = string
  default = ""
}

variable "authorizer_audience" {
  type    = list(string)
  default = []
}

variable "kms_key_arn" {
  type        = string
  description = "ARN of the KMS key used to encrypt the API Gateway access log group. When null, AWS-managed encryption is used."
  default     = null
}

variable "tags" {
  type    = map(string)
  default = {}
}
