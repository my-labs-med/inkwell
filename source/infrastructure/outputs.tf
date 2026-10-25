output "app_url" {
  description = "Open this to use Inkwell."
  value       = "${local.app_url}/"
}

output "api_url_via_cloudfront" {
  value = "${local.app_url}/api"
}

output "api_url_direct" {
  description = "The raw API Gateway URL. Requests here are blocked by the regional WAF; useful to demo that."
  value       = aws_api_gateway_stage.prod.invoke_url
}

output "cognito_sign_in_url" {
  value = "${local.cognito_url}/login?client_id=${aws_cognito_user_pool_client.web.id}&response_type=code&scope=openid+email&redirect_uri=${urlencode("${local.app_url}/")}"
}

output "user_pool_id" {
  value = aws_cognito_user_pool.this.id
}

output "user_pool_client_id" {
  value = aws_cognito_user_pool_client.web.id
}

output "tasks_table" {
  value = aws_dynamodb_table.tasks.name
}

output "stats_table" {
  value = aws_dynamodb_table.stats.name
}

output "stream_dlq_url" {
  value = aws_sqs_queue.stream_dlq.url
}

output "api_cache_enabled" {
  value = var.enable_api_cache
}

output "next_steps" {
  value = <<-EOT
    1. Click the SES verification link sent to ${var.sender_email} (and to each demo recipient).
    2. Confirm the SNS subscription email sent to ${var.alert_email}.
    3. Open ${local.app_url}/ and sign up.
  EOT
}
