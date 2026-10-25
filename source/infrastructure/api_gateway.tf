locals {
  api_resource_paths = {
    tasks = "/api/tasks"
    task  = "/api/tasks/{id}"
    stats = "/api/stats"
  }

  api_resource_ids = {
    tasks = aws_api_gateway_resource.tasks.id
    task  = aws_api_gateway_resource.task.id
    stats = aws_api_gateway_resource.stats.id
  }

  auth_header = "method.request.header.Authorization"
  date_header = "method.request.header.X-Client-Date"

  stats_cache_keys = [local.auth_header, local.date_header]

  method_settings = {
    "*/*" = {
      caching = false
    }
    "api/stats/GET" = {
      caching = var.enable_api_cache
    }
  }
}

resource "aws_api_gateway_rest_api" "this" {
  name = "${local.name}-api"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "api" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  parent_id   = aws_api_gateway_rest_api.this.root_resource_id
  path_part   = "api"
}

resource "aws_api_gateway_resource" "tasks" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "tasks"
}

resource "aws_api_gateway_resource" "task" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  parent_id   = aws_api_gateway_resource.tasks.id
  path_part   = "{id}"
}

resource "aws_api_gateway_resource" "stats" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "stats"
}

resource "aws_api_gateway_authorizer" "cognito" {
  name            = "${local.name}-cognito"
  rest_api_id     = aws_api_gateway_rest_api.this.id
  type            = "COGNITO_USER_POOLS"
  provider_arns   = [aws_cognito_user_pool.this.arn]
  identity_source = local.auth_header
}

resource "aws_api_gateway_method" "this" {
  for_each = local.api_functions

  rest_api_id   = aws_api_gateway_rest_api.this.id
  resource_id   = local.api_resource_ids[each.value.resource]
  http_method   = each.value.method
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = merge(
    each.value.resource == "task" ? { "method.request.path.id" = true } : {},
    each.value.resource == "stats" ? { (local.auth_header) = true, (local.date_header) = false } : {},
  )
}

resource "aws_api_gateway_integration" "this" {
  for_each = local.api_functions

  rest_api_id             = aws_api_gateway_rest_api.this.id
  resource_id             = aws_api_gateway_method.this[each.key].resource_id
  http_method             = aws_api_gateway_method.this[each.key].http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = module.api_function[each.key].invoke_arn
  cache_key_parameters    = each.value.resource == "stats" ? local.stats_cache_keys : []
}

resource "aws_api_gateway_deployment" "this" {
  rest_api_id = aws_api_gateway_rest_api.this.id

  triggers = {
    redeploy = sha1(jsonencode([
      local.api_resource_ids,
      aws_api_gateway_authorizer.cognito.id,
      [for key, method in aws_api_gateway_method.this : [key, method.id, method.request_parameters]],
      [for key, integration in aws_api_gateway_integration.this : [key, integration.id, integration.uri, integration.cache_key_parameters]],
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_api_gateway_integration.this]
}

resource "aws_cloudwatch_log_group" "api_access" {
  name              = "/aws/apigateway/${local.name}-access"
  retention_in_days = var.log_retention_days
}

resource "aws_api_gateway_stage" "prod" {
  rest_api_id           = aws_api_gateway_rest_api.this.id
  deployment_id         = aws_api_gateway_deployment.this.id
  stage_name            = "prod"
  xray_tracing_enabled  = true
  cache_cluster_enabled = var.enable_api_cache
  cache_cluster_size    = var.enable_api_cache ? "0.5" : null

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_access.arn
    format = jsonencode({
      requestId     = "$context.requestId"
      ip            = "$context.identity.sourceIp"
      method        = "$context.httpMethod"
      path          = "$context.path"
      status        = "$context.status"
      latencyMs     = "$context.responseLatency"
      user          = "$context.authorizer.claims.sub"
      integrationMs = "$context.integration.latency"
      wafStatus     = "$context.wafResponseCode"
      xrayTraceId   = "$context.xrayTraceId"
      requestTime   = "$context.requestTime"
      responseSize  = "$context.responseLength"
    })
  }

  depends_on = [aws_api_gateway_account.this]
}

resource "aws_api_gateway_method_settings" "this" {
  for_each = local.method_settings

  rest_api_id = aws_api_gateway_rest_api.this.id
  stage_name  = aws_api_gateway_stage.prod.stage_name
  method_path = each.key

  settings {
    metrics_enabled                            = true
    logging_level                              = "ERROR"
    throttling_rate_limit                      = var.api_throttle_rate
    throttling_burst_limit                     = var.api_throttle_burst
    caching_enabled                            = each.value.caching
    cache_ttl_in_seconds                       = var.stats_cache_ttl_seconds
    require_authorization_for_cache_control    = true
    unauthorized_cache_control_header_strategy = "SUCCEED_WITHOUT_RESPONSE_HEADER"
  }
}

data "aws_iam_policy_document" "apigw_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apigw_cloudwatch" {
  name               = "${local.name}-apigw-cloudwatch"
  assume_role_policy = data.aws_iam_policy_document.apigw_assume.json
}

resource "aws_iam_role_policy_attachment" "apigw_cloudwatch" {
  role       = aws_iam_role.apigw_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

resource "aws_api_gateway_account" "this" {
  cloudwatch_role_arn = aws_iam_role.apigw_cloudwatch.arn
  depends_on          = [aws_iam_role_policy_attachment.apigw_cloudwatch]
}
