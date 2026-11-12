# this tells aws to trust github's login system
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1", "1c58a3a8518e8759bf075b76b750d4f2df264fcd"]
}

# this would create a temporary vip pass (iam role) for github when required
resource "aws_iam_role" "github_actions_role" {
  name = "github-actions-deploy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
      Condition = {
      StringLike = {
        "token.actions.githubusercontent.com:sub" = [
          "repo:patolusola/*",
          "repo:Patolusola/*",
          "repo:PatOlusola/*",
          "repo:PATOLUSOLA/*"
        ]
      }
      StringEquals = {
        "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
      }
      }
      }
    ]
  })
}

# this gives the vip pass permission to build things in my aws account
resource "aws_iam_role_policy_attachment" "github_actions_admin" {
  role       = aws_iam_role.github_actions_role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

# prints out the id of the vip pass so it can be passed to github later
output "github_role_arn" {
  value       = aws_iam_role.github_actions_role.arn
  description = "Copy this ARN, we will need it for the GitHub Assembly Line!"
}