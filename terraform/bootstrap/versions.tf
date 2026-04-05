terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.95"
    }
  }

  # Bootstrap state is stored locally — it's a one-time run and the
  # state file should be committed or kept safe manually.
}

provider "aws" {
  region = var.aws_region
}
