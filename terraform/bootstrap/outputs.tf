output "deploy_role_arn" {
  description = "Set this as the AWS_DEPLOY_ROLE_ARN GitHub secret."
  value       = aws_iam_role.github_actions.arn
}

output "tfstate_bucket_name" {
  description = "Set this as the TF_BACKEND_BUCKET GitHub secret."
  value       = aws_s3_bucket.tfstate.id
}
