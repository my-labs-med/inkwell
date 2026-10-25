resource "random_id" "suffix" {
  byte_length = 3
}

resource "random_password" "origin_secret" {
  length  = 40
  special = false
}

locals {
  name        = var.project_name
  suffix      = random_id.suffix.hex
  repo_root   = abspath("${path.module}/../..")
  dist_dir    = "${local.repo_root}/deployment/dist"
  site_dir    = "${local.repo_root}/source/frontend"
  app_url     = "https://${aws_cloudfront_distribution.site.domain_name}"
  cognito_url = "https://${aws_cognito_user_pool_domain.this.domain}.auth.${var.region}.amazoncognito.com"

  origin_header = "x-origin-verify"
}

data "aws_caller_identity" "current" {}
