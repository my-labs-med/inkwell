variable "project_name" {
  description = "Prefix for resource names."
  type        = string
  default     = "inkwell"
}

variable "region" {
  description = "Must be us-east-1: the CloudFront web ACL lives there and the stack uses a single provider."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = var.region == "us-east-1"
    error_message = "This stack is single-region and must be deployed to us-east-1."
  }
}

variable "sender_email" {
  description = "Address milestone emails are sent from. SES emails it a verification link on first apply."
  type        = string
}

variable "alert_email" {
  description = "Receives CloudWatch alarms and budget alerts. Confirm the SNS subscription email."
  type        = string
}

variable "demo_recipient_emails" {
  description = "Extra addresses to verify in SES so they can receive milestone emails while in the SES sandbox."
  type        = list(string)
  default     = []
}

variable "blocked_countries" {
  description = "ISO 3166-1 alpha-2 country codes the edge WAF blocks. Empty disables the geo rule."
  type        = list(string)
  default     = []
}

variable "waf_rate_limit" {
  description = "API requests (/api/*) allowed per IP in any 5-minute window before the edge WAF blocks it."
  type        = number
  default     = 300
}

variable "api_body_limit_bytes" {
  description = "Largest request body the edge WAF lets through to /api/*. Matches the Lambda limit."
  type        = number
  default     = 4096
}

variable "api_throttle_rate" {
  description = "Steady-state requests per second allowed by the API Gateway stage."
  type        = number
  default     = 20
}

variable "api_throttle_burst" {
  type    = number
  default = 40
}

variable "enable_api_cache" {
  description = "Provision the API Gateway cache (about $0.02/hour) and cache GET /api/stats per user."
  type        = bool
  default     = false
}

variable "stats_cache_ttl_seconds" {
  type    = number
  default = 60
}

variable "static_ttl_seconds" {
  description = "CloudFront TTL for HTML, CSS and JS. Assets under /assets/ are cached for a year."
  type        = number
  default     = 300
}

variable "log_retention_days" {
  type    = number
  default = 14
}

variable "lambda_memory_mb" {
  type    = number
  default = 256
}

variable "lambda_timeout_seconds" {
  type    = number
  default = 10
}

variable "stream_timeout_seconds" {
  type    = number
  default = 30
}

variable "done_milestones" {
  description = "Completion counts that trigger a milestone email. Lower them (e.g. \"1,3,5\") for a demo."
  type        = string
  default     = "1,10,50,100"
}

variable "streak_milestones" {
  type    = string
  default = "7,30"
}

variable "monthly_budget_usd" {
  type    = number
  default = 10
}
