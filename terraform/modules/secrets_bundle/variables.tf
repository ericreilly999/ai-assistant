variable "name_prefix" {
  type = string
}

variable "secret_names" {
  type = set(string)
}

variable "tags" {
  type    = map(string)
  default = {}
}