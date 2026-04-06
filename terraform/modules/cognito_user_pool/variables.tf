variable "name_prefix" {
  type = string
}

variable "callback_urls" {
  type    = list(string)
  default = []
}

variable "logout_urls" {
  type    = list(string)
  default = []
}

variable "cognito_domain" {
  type        = string
  description = "Domain name for Cognito hosted UI (optional)"
  default     = null
}

variable "certificate_arn" {
  type        = string
  description = "ARN of ACM certificate for Cognito custom domain (optional)"
  default     = null
}

variable "tags" {
  type    = map(string)
  default = {}
}