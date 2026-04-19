resource "aws_apigatewayv2_api" "this" {
  name          = var.name
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["authorization", "content-type"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_origins = var.cors_allow_origins
    max_age       = 3600
  }

  tags = var.tags
}

resource "aws_apigatewayv2_authorizer" "jwt" {
  count            = var.authorizer_issuer == "" ? 0 : 1
  api_id           = aws_apigatewayv2_api.this.id
  name             = "${var.name}-jwt"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = var.authorizer_audience
    issuer   = var.authorizer_issuer
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = var.integration_uri
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "this" {
  for_each = var.routes

  api_id    = aws_apigatewayv2_api.this.id
  route_key = each.value
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"

  authorization_type = contains(tolist(var.protected_routes), each.value) && length(aws_apigatewayv2_authorizer.jwt) > 0 ? "JWT" : "NONE"
  authorizer_id      = contains(tolist(var.protected_routes), each.value) && length(aws_apigatewayv2_authorizer.jwt) > 0 ? aws_apigatewayv2_authorizer.jwt[0].id : null
}

# $default catch-all: routes unmatched paths to Lambda so they return a structured JSON 404
# instead of API Gateway's bare built-in "Not Found" string.
#
# IMPORTANT — deployment-order constraint: new protected routes must be added to var.routes
# (and therefore get the JWT authorizer) before or at the same time as their Lambda handler
# code is deployed. If a handler ships before the named route exists, that path is temporarily
# reachable unauthenticated via this catch-all. Always deploy Terraform first, then Lambda.
resource "aws_apigatewayv2_route" "default_catchall" {
  # checkov:skip=CKV_AWS_309:Catch-all route is intentionally unauthenticated — returns structured
  # JSON 404 for unmatched paths; JWT auth applies to all named protected routes.
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "$default"
  target             = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorization_type = "NONE"
  authorizer_id      = null
}

# CKV_AWS_76: access logging log group — always created so the stage can enable access logging.
resource "aws_cloudwatch_log_group" "access_logs" {
  name              = "/aws/apigateway/${var.name}/access-logs"
  retention_in_days = 365
  tags              = var.tags
}

resource "aws_apigatewayv2_stage" "this" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = var.stage_name
  auto_deploy = true

  # CKV_AWS_76: enable access logging to a dedicated CloudWatch log group.
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.access_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      sourceIp       = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  default_route_settings {
    throttling_burst_limit = 20
    throttling_rate_limit  = 10
  }

  tags = var.tags
}

resource "aws_lambda_permission" "api_invoke" {
  statement_id  = "AllowExecutionFromHttpApi"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}
