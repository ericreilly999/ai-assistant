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

variable "router_model_id" {
  description = "Bedrock model ID used for intent routing and plan generation (e.g. amazon.nova-lite-v1:0)."
  type        = string
  default     = "amazon.nova-lite-v1:0"
}

variable "prompt_template" {
  description = "System prompt template stored as a Bedrock managed prompt variant."
  type        = string
  default     = <<-EOT
    You are an AI assistant orchestration router.
    Classify the user request into one of: calendar, meeting_prep, grocery, travel, tasks, general.
    Reply with a JSON object: {"domain": string, "operation": "read"|"write", "requires_confirmation": bool}.
  EOT
}

variable "tags" {
  description = "Resource tags."
  type        = map(string)
  default     = {}
}
