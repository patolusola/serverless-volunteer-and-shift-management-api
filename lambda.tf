# this would zip the python code automatically
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/api"
  output_path = "${path.module}/api.zip"
}

# to create a security badge (iam role) for the robot
resource "aws_iam_role" "lambda_role" {
  name = "volunteer_api_lambda_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# this gives permission to the badge to write to dynamodb and save logs
resource "aws_iam_role_policy" "lambda_policy" {
  name = "volunteer_api_lambda_policy"
  role = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.volunteer_table.arn
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# this code builds the actual Lambda robot
resource "aws_lambda_function" "api_lambda" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "VolunteerShiftAPI"
  role             = aws_iam_role.lambda_role.arn
  handler          = "app.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.9"

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.volunteer_table.name
    }
  }
}