variable "name_prefix" {
  description = "Prefix used for all resource names."
  type        = string
}

variable "guardrail_description" {
  description = "Human-readable description for the Bedrock guardrail."
  type        = string
  default     = "Filters harmful, hateful, or privacy-violating content from AI assistant inputs and outputs."
}

variable "blocked_input_message" {
  description = "Message returned when the input guardrail intervenes."
  type        = string
  default     = "I cannot process that request. Please rephrase or ask something else."
}

variable "blocked_output_message" {
  description = "Message returned when the output guardrail intervenes."
  type        = string
  default     = "The assistant response was filtered. Please try a different request."
}


variable "tags" {
  description = "Resource tags."
  type        = map(string)
  default     = {}
}
