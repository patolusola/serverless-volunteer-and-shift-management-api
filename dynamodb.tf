resource "aws_dynamodb_table" "volunteer_table" {
  name         = "VolunteerManagement"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }
}

resource "aws_dynamodb_table_item" "admin_user" {
  table_name = aws_dynamodb_table.volunteer_table.name
  hash_key   = aws_dynamodb_table.volunteer_table.hash_key
  range_key  = aws_dynamodb_table.volunteer_table.range_key

  item = <<ITEM
{
  "PK": {"S": "VOL#ADMIN"},
  "SK": {"S": "PROFILE"},
  "StaffId": {"S": "ADMIN"},
  "FullName": {"S": "System Administrator"},
  "Role": {"S": "ADMIN"},
  "Password": {"S": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"}
}
ITEM
}