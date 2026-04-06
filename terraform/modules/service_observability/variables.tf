variable "name_prefix" {
  type = string
}

variable "lambda_function_name" {
  type = string
}

variable "api_id" {
  type = string
}

variable "stage_name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
