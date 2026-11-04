variable "aws_region" {
  description = "AWS region for the EC2 deployment."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Short lowercase prefix for AWS resource names."
  type        = string
  default     = "r2-assessment"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,20}$", var.project_name))
    error_message = "Use 3-21 lowercase letters, digits, or hyphens; start with a letter."
  }
}

variable "instance_type" {
  description = "EC2 instance type; t3.medium provides memory for the Next.js build."
  type        = string
  default     = "t3.medium"
}

variable "vpc_cidr" {
  description = "CIDR block for the single-instance VPC."
  type        = string
  default     = "10.40.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public EC2 subnet."
  type        = string
  default     = "10.40.1.0/24"
}

variable "github_owner" {
  description = "GitHub user or organization that owns the source repository."
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name used by the deployment workflow."
  type        = string
}

variable "docker_compose_version" {
  description = "Docker Compose v2 release installed by EC2 user data."
  type        = string
  default     = "v2.29.7"
}
