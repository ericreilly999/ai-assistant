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

variable "managed_policy_arns" {
  type    = set(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}