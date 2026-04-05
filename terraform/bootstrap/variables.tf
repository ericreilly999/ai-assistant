variable "github_org" {
  description = "GitHub organisation or username that owns the repository."
  type        = string
}

variable "github_repo" {
  description = "Repository name (without the org prefix)."
  type        = string
  default     = "ai-assistant"
}

variable "tfstate_bucket_name" {
  description = "Globally unique name for the S3 bucket that stores Terraform state."
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}
