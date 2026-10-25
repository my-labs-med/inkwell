mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }

  mock_data "aws_cloudfront_origin_request_policy" {
    defaults = {
      id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
    }
  }

  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }

  mock_resource "aws_cognito_user_pool" {
    defaults = {
      arn = "arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_EXAMPLE"
      id  = "us-east-1_EXAMPLE"
    }
  }

  mock_resource "aws_sns_topic" {
    defaults = {
      arn = "arn:aws:sns:us-east-1:123456789012:inkwell-alerts"
    }
  }

  mock_resource "aws_iam_role" {
    defaults = {
      arn = "arn:aws:iam::123456789012:role/inkwell-role"
    }
  }

  mock_resource "aws_lambda_layer_version" {
    defaults = {
      arn = "arn:aws:lambda:us-east-1:123456789012:layer:inkwell-xray-sdk:1"
    }
  }

  mock_resource "aws_sqs_queue" {
    defaults = {
      arn = "arn:aws:sqs:us-east-1:123456789012:inkwell-stream-dlq"
    }
  }

  mock_resource "aws_dynamodb_table" {
    defaults = {
      arn        = "arn:aws:dynamodb:us-east-1:123456789012:table/inkwell-tasks"
      stream_arn = "arn:aws:dynamodb:us-east-1:123456789012:table/inkwell-tasks/stream/2026-10-25T00:00:00.000"
    }
  }

  mock_resource "aws_cloudwatch_log_group" {
    defaults = {
      arn = "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/inkwell"
    }
  }

  mock_resource "aws_lambda_function" {
    defaults = {
      arn        = "arn:aws:lambda:us-east-1:123456789012:function:inkwell"
      invoke_arn = "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:inkwell/invocations"
    }
  }

  mock_resource "aws_wafv2_web_acl" {
    defaults = {
      arn = "arn:aws:wafv2:us-east-1:123456789012:global/webacl/inkwell/abc"
    }
  }

  mock_resource "aws_api_gateway_stage" {
    defaults = {
      arn = "arn:aws:apigateway:us-east-1::/restapis/a1b2c3d4e5/stages/prod"
    }
  }

  mock_resource "aws_cloudfront_distribution" {
    defaults = {
      domain_name = "d111111abcdef8.cloudfront.net"
      arn         = "arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE"
    }
  }

  mock_resource "aws_api_gateway_rest_api" {
    defaults = {
      id            = "a1b2c3d4e5"
      execution_arn = "arn:aws:execute-api:us-east-1:123456789012:a1b2c3d4e5"
    }
  }
}

mock_provider "random" {}

mock_provider "time" {}

variables {
  sender_email = "sender@example.com"
  alert_email  = "alerts@example.com"
}

run "defaults" {
  command = apply

  assert {
    condition     = !contains(keys(aws_s3_object.site), "js/mock-api.js") && !contains(keys(aws_s3_object.site), "js/config.js")
    error_message = "Mock API and hand-written config must not be uploaded."
  }

  assert {
    condition     = length([for key in keys(aws_s3_object.site) : key if startswith(key, "test/")]) == 0
    error_message = "Frontend tests must not be uploaded."
  }

  assert {
    condition     = aws_s3_object.site["assets/fonts/fraunces-latin-wght-normal.woff2"].cache_control == "public, max-age=31536000, immutable"
    error_message = "Assets must be cached for a year."
  }

  assert {
    condition     = aws_s3_object.site["index.html"].cache_control == "public, max-age=300" && aws_s3_object.site["index.html"].content_type == "text/html; charset=utf-8"
    error_message = "index.html must have a short cache and an HTML content type."
  }

  assert {
    condition     = strcontains(aws_s3_object.config.content, "redirectUri: `$${window.location.origin}/`") && strcontains(aws_s3_object.config.content, "mock: false")
    error_message = "Generated config.js must keep the JS template literal and disable mock mode."
  }

  assert {
    condition     = aws_api_gateway_integration.this["get-stats"].cache_key_parameters == toset(["method.request.header.Authorization", "method.request.header.X-Client-Date"])
    error_message = "Stats cache must be keyed by the caller's token and local date."
  }

  assert {
    condition     = length(aws_api_gateway_integration.this["list-tasks"].cache_key_parameters) == 0
    error_message = "Task routes must not declare cache keys."
  }

  assert {
    condition     = aws_lambda_permission.api["update-task"].source_arn == "arn:aws:execute-api:us-east-1:123456789012:a1b2c3d4e5/*/PUT/api/tasks/*"
    error_message = "Lambda permission must cover the {id} path."
  }

  assert {
    condition     = aws_api_gateway_stage.prod.cache_cluster_enabled == false && aws_api_gateway_method_settings.this["api/stats/GET"].settings[0].caching_enabled == false
    error_message = "The API cache must be off by default."
  }

  assert {
    condition     = one([for rule in aws_wafv2_web_acl.edge.rule : rule if rule.name == "rate-limit-per-ip"]).statement[0].rate_based_statement[0].scope_down_statement[0].byte_match_statement[0].search_string == "/api/"
    error_message = "The rate limit must only count API calls, not static files."
  }

  assert {
    condition     = length([for rule in aws_wafv2_web_acl.edge.rule : rule if rule.name == "geo-block"]) == 0
    error_message = "No geo rule when no countries are blocked."
  }

  assert {
    condition     = module.stream_processor.function_name == "inkwell-stream-processor"
    error_message = "Unexpected stream processor name."
  }

  assert {
    condition     = aws_cognito_user_pool_client.web.callback_urls == toset(["https://d111111abcdef8.cloudfront.net/"])
    error_message = "Cognito must redirect back to the CloudFront URL."
  }

  assert {
    condition     = strcontains(aws_cloudfront_response_headers_policy.security.security_headers_config[0].content_security_policy[0].content_security_policy, "connect-src 'self' https://inkwell-")
    error_message = "CSP must allow calls to the Cognito domain."
  }
}

run "demo_toggles" {
  command = apply

  variables {
    blocked_countries = ["TN"]
    enable_api_cache  = true
  }

  assert {
    condition     = length([for rule in aws_wafv2_web_acl.edge.rule : rule if rule.name == "geo-block"]) == 1
    error_message = "Geo rule must appear when countries are blocked."
  }

  assert {
    condition     = aws_api_gateway_stage.prod.cache_cluster_enabled && aws_api_gateway_stage.prod.cache_cluster_size == "0.5" && aws_api_gateway_method_settings.this["api/stats/GET"].settings[0].caching_enabled
    error_message = "Cache toggle must provision the cluster and enable stats caching."
  }

  assert {
    condition     = !aws_api_gateway_method_settings.this["*/*"].settings[0].caching_enabled
    error_message = "Only stats may be cached."
  }

  assert {
    condition     = aws_api_gateway_method_settings.this["api/stats/GET"].settings[0].unauthorized_cache_control_header_strategy == "SUCCEED_WITHOUT_RESPONSE_HEADER"
    error_message = "Browsers send Cache-Control: max-age=0 on no-cache fetches; that must not turn into a 403."
  }
}

run "rejects_other_regions" {
  command = plan

  variables {
    region = "eu-west-3"
  }

  expect_failures = [var.region]
}
