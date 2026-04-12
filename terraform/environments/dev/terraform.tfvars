environment             = "dev"
aws_region              = "us-east-1"
mock_provider_mode      = false
cors_allow_origins      = ["*"]
bedrock_router_model_id = "us.amazon.nova-pro-v1:0"
callback_urls = [
  "exp://localhost:8081",
  "exp://127.0.0.1:8081",
  "exp://10.0.2.2:8081",
  "exp://192.168.1.92:8081",
  "exp://localhost:8081/--/",
  "exp://127.0.0.1:8081/--/",
  "exp://10.0.2.2:8081/--/",
  "exp://192.168.1.92:8081/--/",
]
logout_urls = [
  "exp://localhost:8081",
  "exp://127.0.0.1:8081",
  "exp://10.0.2.2:8081",
  "exp://192.168.1.92:8081",
]
cognito_domain = "ai-assistant-dev"
