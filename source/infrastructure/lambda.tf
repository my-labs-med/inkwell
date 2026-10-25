locals {
  tasks_table_arns = [aws_dynamodb_table.tasks.arn, "${aws_dynamodb_table.tasks.arn}/index/byStatus"]

  table_environment = {
    TASKS_TABLE = aws_dynamodb_table.tasks.name
    STATS_TABLE = aws_dynamodb_table.stats.name
  }

  api_functions = {
    list-tasks = {
      handler  = "handlers.list_tasks.handler"
      method   = "GET"
      resource = "tasks"
      statements = [
        { actions = ["dynamodb:Query"], resources = local.tasks_table_arns },
      ]
    }
    create-task = {
      handler  = "handlers.create_task.handler"
      method   = "POST"
      resource = "tasks"
      statements = [
        { actions = ["dynamodb:Query", "dynamodb:PutItem"], resources = [aws_dynamodb_table.tasks.arn] },
      ]
    }
    get-task = {
      handler  = "handlers.get_task.handler"
      method   = "GET"
      resource = "task"
      statements = [
        { actions = ["dynamodb:GetItem"], resources = [aws_dynamodb_table.tasks.arn] },
      ]
    }
    update-task = {
      handler  = "handlers.update_task.handler"
      method   = "PUT"
      resource = "task"
      statements = [
        { actions = ["dynamodb:GetItem", "dynamodb:UpdateItem"], resources = [aws_dynamodb_table.tasks.arn] },
      ]
    }
    delete-task = {
      handler  = "handlers.delete_task.handler"
      method   = "DELETE"
      resource = "task"
      statements = [
        { actions = ["dynamodb:DeleteItem"], resources = [aws_dynamodb_table.tasks.arn] },
      ]
    }
    get-stats = {
      handler  = "handlers.get_stats.handler"
      method   = "GET"
      resource = "stats"
      statements = [
        { actions = ["dynamodb:GetItem", "dynamodb:Query"], resources = [aws_dynamodb_table.stats.arn] },
      ]
    }
  }
}

resource "aws_lambda_layer_version" "xray" {
  layer_name               = "${local.name}-xray-sdk"
  filename                 = "${local.dist_dir}/xray-layer.zip"
  source_code_hash         = filebase64sha256("${local.dist_dir}/xray-layer.zip")
  compatible_runtimes      = ["python3.12"]
  compatible_architectures = ["arm64"]
}

module "api_function" {
  source   = "./modules/lambda-function"
  for_each = local.api_functions

  name               = "${local.name}-${each.key}"
  handler            = each.value.handler
  package_path       = "${local.dist_dir}/task-api.zip"
  memory_size        = var.lambda_memory_mb
  timeout            = var.lambda_timeout_seconds
  log_retention_days = var.log_retention_days
  layers             = [aws_lambda_layer_version.xray.arn]
  environment        = local.table_environment
  policy_statements  = each.value.statements
}

module "stream_processor" {
  source = "./modules/lambda-function"

  name               = "${local.name}-stream-processor"
  handler            = "stream_processor.handler.handler"
  package_path       = "${local.dist_dir}/stream-processor.zip"
  memory_size        = var.lambda_memory_mb
  timeout            = var.stream_timeout_seconds
  log_retention_days = var.log_retention_days
  layers             = [aws_lambda_layer_version.xray.arn]

  environment = merge(local.table_environment, {
    USER_POOL_ID      = aws_cognito_user_pool.this.id
    SENDER_EMAIL      = var.sender_email
    APP_URL           = local.app_url
    DONE_MILESTONES   = var.done_milestones
    STREAK_MILESTONES = var.streak_milestones
  })

  policy_statements = [
    {
      actions = [
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:ConditionCheckItem",
      ]
      resources = [aws_dynamodb_table.stats.arn]
    },
    {
      actions = [
        "dynamodb:DescribeStream",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
      ]
      resources = [aws_dynamodb_table.tasks.stream_arn]
    },
    { actions = ["dynamodb:ListStreams"], resources = ["*"] },
    { actions = ["cognito-idp:ListUsers"], resources = [aws_cognito_user_pool.this.arn] },
    {
      actions   = ["ses:SendEmail"]
      resources = ["arn:aws:ses:${var.region}:${data.aws_caller_identity.current.account_id}:identity/*"]
    },
    { actions = ["sqs:SendMessage"], resources = [aws_sqs_queue.stream_dlq.arn] },
  ]
}

resource "aws_sqs_queue" "stream_dlq" {
  name                      = "${local.name}-stream-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}

resource "time_sleep" "stream_role_propagation" {
  create_duration = "15s"
  triggers        = { role = module.stream_processor.role_name }
}

resource "aws_lambda_event_source_mapping" "tasks_stream" {
  event_source_arn                   = aws_dynamodb_table.tasks.stream_arn
  function_name                      = module.stream_processor.arn
  starting_position                  = "LATEST"
  batch_size                         = 25
  maximum_batching_window_in_seconds = 1
  bisect_batch_on_function_error     = true
  maximum_retry_attempts             = 5
  function_response_types            = ["ReportBatchItemFailures"]
  depends_on                         = [time_sleep.stream_role_propagation]

  destination_config {
    on_failure {
      destination_arn = aws_sqs_queue.stream_dlq.arn
    }
  }
}

resource "aws_lambda_permission" "api" {
  for_each = local.api_functions

  statement_id  = "AllowApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = module.api_function[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.this.execution_arn}/*/${each.value.method}${replace(local.api_resource_paths[each.value.resource], "{id}", "*")}"
}
