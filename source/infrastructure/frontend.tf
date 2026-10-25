locals {
  content_types = {
    html  = "text/html; charset=utf-8"
    css   = "text/css; charset=utf-8"
    js    = "text/javascript; charset=utf-8"
    svg   = "image/svg+xml"
    woff2 = "font/woff2"
    png   = "image/png"
    ico   = "image/x-icon"
    txt   = "text/plain; charset=utf-8"
  }

  site_files = [
    for file in fileset(local.site_dir, "**") : file
    if !startswith(file, "test/") && !contains(["js/config.js", "js/mock-api.js", "README.md"], file)
  ]

  long_cache  = "public, max-age=31536000, immutable"
  short_cache = "public, max-age=${var.static_ttl_seconds}"

  frontend_config = <<-EOT
    export default {
      apiBase: "/api",
      cognitoDomain: "${local.cognito_url}",
      clientId: "${aws_cognito_user_pool_client.web.id}",
      redirectUri: `$${window.location.origin}/`,
      scopes: "openid email",
      mock: false,
    };
  EOT
}

resource "aws_s3_bucket" "site" {
  bucket        = "${local.name}-site-${local.suffix}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "site" {
  bucket = aws_s3_bucket.site.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

data "aws_iam_policy_document" "site" {
  statement {
    sid       = "CloudFrontReadOnly"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.site.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.site.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "site" {
  bucket     = aws_s3_bucket.site.id
  policy     = data.aws_iam_policy_document.site.json
  depends_on = [aws_s3_bucket_public_access_block.site]
}

resource "aws_s3_object" "site" {
  for_each = toset(local.site_files)

  bucket        = aws_s3_bucket.site.id
  key           = each.value
  source        = "${local.site_dir}/${each.value}"
  etag          = filemd5("${local.site_dir}/${each.value}")
  content_type  = lookup(local.content_types, reverse(split(".", each.value))[0], "application/octet-stream")
  cache_control = startswith(each.value, "assets/") ? local.long_cache : local.short_cache
}

resource "aws_s3_object" "config" {
  bucket        = aws_s3_bucket.site.id
  key           = "js/config.js"
  content       = local.frontend_config
  content_type  = local.content_types.js
  cache_control = local.short_cache
}

resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "${local.name}-site"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_cache_policy" "static" {
  for_each = {
    short     = var.static_ttl_seconds
    immutable = 31536000
  }

  name        = "${local.name}-static-${each.key}"
  min_ttl     = each.key == "immutable" ? each.value : 0
  default_ttl = each.value
  max_ttl     = each.value

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true

    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "none"
    }
    query_strings_config {
      query_string_behavior = "none"
    }
  }
}

resource "aws_cloudfront_cache_policy" "api" {
  name        = "${local.name}-api"
  min_ttl     = 0
  default_ttl = 0
  max_ttl     = 1

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "whitelist"
      headers {
        items = ["Authorization"]
      }
    }
    query_strings_config {
      query_string_behavior = "all"
    }
  }
}

data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

resource "aws_cloudfront_response_headers_policy" "security" {
  name = "${local.name}-security-headers"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      override                   = true
    }
    content_type_options {
      override = true
    }
    frame_options {
      frame_option = "DENY"
      override     = true
    }
    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }
    content_security_policy {
      override = true
      content_security_policy = join("; ", [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "font-src 'self'",
        "img-src 'self' data:",
        "connect-src 'self' ${local.cognito_url}",
        "form-action 'self' ${local.cognito_url}",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "object-src 'none'",
      ])
    }
  }
}

resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  comment             = "${local.name} frontend and API"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  http_version        = "http2and3"
  web_acl_id          = aws_wafv2_web_acl.edge.arn

  origin {
    origin_id                = "site"
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }

  origin {
    origin_id   = "api"
    domain_name = "${aws_api_gateway_rest_api.this.id}.execute-api.${var.region}.amazonaws.com"
    origin_path = "/${aws_api_gateway_stage.prod.stage_name}"

    custom_header {
      name  = local.origin_header
      value = random_password.origin_secret.result
    }

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id           = "site"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = aws_cloudfront_cache_policy.static["short"].id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  ordered_cache_behavior {
    path_pattern               = "/assets/*"
    target_origin_id           = "site"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = aws_cloudfront_cache_policy.static["immutable"].id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  ordered_cache_behavior {
    path_pattern               = "/api/*"
    target_origin_id           = "api"
    viewer_protocol_policy     = "https-only"
    allowed_methods            = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = aws_cloudfront_cache_policy.api.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
