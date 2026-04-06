locals {
  application_name = "ai-assistant"
  name_prefix      = "${local.application_name}-${var.environment}"
  tags = merge(var.tags, {
    Application = local.application_name
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

data "archive_file" "orchestrator" {
  type        = "zip"
  source_dir  = "${path.root}/../../../backend/src"
  output_path = "${path.root}/build/orchestrator.zip"
}

module "auth" {
  source        = "../../modules/cognito_user_pool"
  name_prefix   = local.name_prefix
  callback_urls = var.callback_urls
  logout_urls   = var.logout_urls
  tags          = local.tags
}

module "secrets" {
  source       = "../../modules/secrets_bundle"
  name_prefix  = local.name_prefix
  secret_names = ["google-oauth", "microsoft-oauth", "plaid"]
  tags         = local.tags
}

module "bedrock" {
  source      = "../../modules/bedrock_ai_config"
  name_prefix = local.name_prefix
  tags        = local.tags
}

data "aws_iam_policy_document" "lambda_runtime" {
  statement {
    sid = "BedrockRuntime"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:ApplyGuardrail",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "SecretsRead"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = values(module.secrets.secret_arns)
  }
}

module "lambda" {
  source                 = "../../modules/lambda_service"
  function_name          = "${local.name_prefix}-orchestrator"
  handler                = "assistant_app.handler.lambda_handler"
  runtime                = "python3.13"
  filename               = data.archive_file.orchestrator.output_path
  source_code_hash       = data.archive_file.orchestrator.output_base64sha256
  timeout                = 30
  memory_size            = 512
  additional_policy_json = data.aws_iam_policy_document.lambda_runtime.json
  has_additional_policy  = true
  environment_variables = {
    APP_ENV                    = var.environment
    LOG_LEVEL                  = "INFO"
    MOCK_PROVIDER_MODE         = tostring(var.mock_provider_mode)
    DEFAULT_TIMEZONE           = "America/New_York"
    PROPOSAL_TTL_MINUTES       = "15"
    BEDROCK_ROUTER_MODEL_ID    = var.bedrock_router_model_id
    BEDROCK_GUARDRAIL_ID       = module.bedrock.guardrail_id
    BEDROCK_GUARDRAIL_VERSION  = module.bedrock.guardrail_version
    GOOGLE_OAUTH_SECRET_ARN    = module.secrets.secret_arns["google-oauth"]
    MICROSOFT_OAUTH_SECRET_ARN = module.secrets.secret_arns["microsoft-oauth"]
    PLAID_SECRET_ARN           = module.secrets.secret_arns["plaid"]
    CORS_ALLOWED_ORIGINS       = join(",", var.cors_allow_origins)
  }
  tags = local.tags
}

module "api" {
  source                 = "../../modules/http_api"
  name                   = "${local.name_prefix}-http-api"
  stage_name             = var.environment
  integration_uri        = module.lambda.invoke_arn
  lambda_function_name   = module.lambda.function_name
  cors_allow_origins     = var.cors_allow_origins
  authorizer_issuer      = "https://cognito-idp.${var.aws_region}.amazonaws.com/${module.auth.user_pool_id}"
  authorizer_audience    = [module.auth.app_client_id]
  routes                 = [
    "GET /health",
    "GET /v1/integrations",
    "POST /v1/chat/plan",
    "POST /v1/chat/execute"
  ]
  protected_routes = [
    "GET /v1/integrations",
    "POST /v1/chat/plan",
    "POST /v1/chat/execute"
  ]
  tags                   = local.tags
}

module "observability" {
  source                 = "../../modules/service_observability"
  name_prefix            = local.name_prefix
  lambda_function_name   = module.lambda.function_name
  api_id                 = module.api.api_id
  stage_name             = module.api.stage_name
  tags                   = local.tags
}
