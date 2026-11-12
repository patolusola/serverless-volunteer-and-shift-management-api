# this create the gateway for the http api (the receptionist)
resource "aws_apigatewayv2_api" "http_api" {
  name          = "volunteer-api"
  protocol_type = "HTTP"
}

# this code tells the receptionist (api) how to talk to the (lambda) robot (integration)
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api_lambda.invoke_arn
  payload_format_version = "2.0"
}

# here i define the exact messages allowed (routes)
resource "aws_apigatewayv2_route" "post_volunteer" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /volunteers"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "post_shift" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /shifts/log"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# we light up the api so it is live on the internet
resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

# we give the receptionist security clearance to wake up the robot
resource "aws_lambda_permission" "api_gw_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

# this prints out my brand new url on my terminal
output "api_url" {
  value       = aws_apigatewayv2_api.http_api.api_endpoint
  description = "This is the live web address for your API!"
}