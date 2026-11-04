output "instance_id" {
  description = "EC2 instance ID; set this as the GitHub Actions EC2_INSTANCE_ID variable."
  value       = aws_instance.app.id
}

output "public_ip" {
  description = "Public IPv4 address for the application and DNS A record."
  value       = aws_eip.app.public_ip
}

output "artifact_bucket" {
  description = "Private S3 bucket used only to transfer deployment archives."
  value       = aws_s3_bucket.artifacts.id
}

output "app_password_parameter_name" {
  description = "SSM SecureString name used by GitHub Actions and the EC2 instance."
  value       = "/${var.project_name}/prod/db-password"
}

output "github_actions_role_arn" {
  description = "OIDC role ARN; set this as the GitHub Actions AWS_ROLE_ARN variable."
  value       = aws_iam_role.github_actions.arn
}

output "application_url" {
  description = "HTTP URL until a domain is configured for Caddy TLS."
  value       = "http://${aws_eip.app.public_ip}"
}
