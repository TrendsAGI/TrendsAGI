variable "project_name" {
  type        = string
  description = "Prefix for generated AWS resources."
  default     = "trendsagi"
}

variable "aws_region" {
  type        = string
  description = "AWS region for infrastructure."
  default     = "us-east-1"
}

variable "lambda_image_uri" {
  type        = string
  description = "Container image URI for the trendsagi worker."
}

variable "trendsagi_api_key" {
  type        = string
  description = "API key for TrendsAGI."
  sensitive   = true
}

variable "google_ads_token" {
  type        = string
  description = "Runtime Google Ads OAuth token."
  sensitive   = true
}

