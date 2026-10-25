resource "aws_dynamodb_table" "tasks" {
  name             = "${local.name}-tasks"
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "userId"
  range_key        = "taskId"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "taskId"
    type = "S"
  }

  attribute {
    name = "statusCreatedAt"
    type = "S"
  }

  global_secondary_index {
    name            = "byStatus"
    projection_type = "ALL"

    key_schema {
      attribute_name = "userId"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "statusCreatedAt"
      key_type       = "RANGE"
    }
  }
}

resource "aws_dynamodb_table" "stats" {
  name         = "${local.name}-stats"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "sk"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }
}
