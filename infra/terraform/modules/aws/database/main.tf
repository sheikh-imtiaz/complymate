terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 5.80"
      configuration_aliases = [aws.dr]
    }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

resource "aws_db_subnet_group" "this" {
  name       = var.name
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "db" {
  name        = "${var.name}-db"
  description = "Aurora PostgreSQL and RDS Proxy"
  vpc_id      = var.vpc_id
  ingress {
    description     = "PostgreSQL from Lambdas"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.client_security_group_ids
  }
  ingress {
    description = "Proxy to cluster"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    self        = true
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }
}

resource "aws_rds_cluster_parameter_group" "this" {
  name   = "${var.name}-pg16"
  family = "aurora-postgresql16"
  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }
  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }
}

# Aurora Serverless v2, PostgreSQL 16 + pgvector. Master password managed by Secrets Manager (rotated by RDS).
resource "aws_rds_cluster" "this" {
  cluster_identifier                  = var.name
  engine                              = "aurora-postgresql"
  engine_mode                         = "provisioned"
  engine_version                      = var.engine_version
  database_name                       = "complymate"
  master_username                     = "complymate_owner"
  manage_master_user_password         = true
  master_user_secret_kms_key_id       = var.kms_key_arn
  db_subnet_group_name                = aws_db_subnet_group.this.name
  vpc_security_group_ids              = [aws_security_group.db.id]
  db_cluster_parameter_group_name     = aws_rds_cluster_parameter_group.this.name
  storage_encrypted                   = true
  kms_key_id                          = var.kms_key_arn
  backup_retention_period             = 35            # point-in-time recovery 35 days (RPO 15 min target)
  preferred_backup_window             = "15:00-16:00" # 01:00-02:00 AEST
  copy_tags_to_snapshot               = true
  deletion_protection                 = var.deletion_protection
  skip_final_snapshot                 = !var.deletion_protection
  final_snapshot_identifier           = var.deletion_protection ? "${var.name}-final" : null
  iam_database_authentication_enabled = true
  enabled_cloudwatch_logs_exports     = ["postgresql"]
  serverlessv2_scaling_configuration {
    min_capacity = var.min_acu
    max_capacity = var.max_acu
  }
}

resource "aws_rds_cluster_instance" "this" {
  count                           = var.instance_count
  identifier                      = "${var.name}-${count.index}"
  cluster_identifier              = aws_rds_cluster.this.id
  instance_class                  = "db.serverless"
  engine                          = aws_rds_cluster.this.engine
  engine_version                  = aws_rds_cluster.this.engine_version
  performance_insights_enabled    = true
  performance_insights_kms_key_id = var.kms_key_arn
  auto_minor_version_upgrade      = true
}

# ---------------- application role secret (RLS-restricted login) ----------------
resource "random_password" "app" {
  length  = 40
  special = false
}

resource "aws_secretsmanager_secret" "app" {
  name                    = "${var.name}/db-app"
  kms_key_id              = var.kms_key_arn
  recovery_window_in_days = var.deletion_protection ? 30 : 0
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    username   = "complymate_app"
    password   = random_password.app.result
    engine     = "postgres"
    host       = aws_db_proxy.this.endpoint
    proxy_host = aws_db_proxy.this.endpoint
    port       = 5432
    dbname     = "complymate"
  })
}

# ---------------- RDS Proxy (stops Lambda opening too many connections) ----------------
data "aws_iam_policy_document" "proxy_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["rds.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "proxy" {
  name               = "${var.name}-rds-proxy"
  assume_role_policy = data.aws_iam_policy_document.proxy_trust.json
}

data "aws_iam_policy_document" "proxy" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.app.arn, aws_rds_cluster.this.master_user_secret[0].secret_arn]
  }
  statement {
    actions   = ["kms:Decrypt"]
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_role_policy" "proxy" {
  role   = aws_iam_role.proxy.id
  policy = data.aws_iam_policy_document.proxy.json
}

resource "aws_db_proxy" "this" {
  name                   = var.name
  engine_family          = "POSTGRESQL"
  role_arn               = aws_iam_role.proxy.arn
  vpc_subnet_ids         = var.subnet_ids
  vpc_security_group_ids = [aws_security_group.db.id]
  require_tls            = true
  idle_client_timeout    = 900
  auth {
    auth_scheme = "SECRETS"
    iam_auth    = "DISABLED"
    secret_arn  = aws_secretsmanager_secret.app.arn
  }
  auth {
    auth_scheme = "SECRETS"
    iam_auth    = "DISABLED"
    secret_arn  = aws_rds_cluster.this.master_user_secret[0].secret_arn
  }
}

resource "aws_db_proxy_default_target_group" "this" {
  db_proxy_name = aws_db_proxy.this.name
  connection_pool_config {
    max_connections_percent      = 90
    max_idle_connections_percent = 30
    connection_borrow_timeout    = 120
  }
}

resource "aws_db_proxy_target" "this" {
  db_proxy_name         = aws_db_proxy.this.name
  target_group_name     = aws_db_proxy_default_target_group.this.name
  db_cluster_identifier = aws_rds_cluster.this.id
}

# ---------------- Backups: cross-region copy to Melbourne (data stays in Australia) ----------------
resource "aws_backup_vault" "primary" {
  name        = "${var.name}-primary"
  kms_key_arn = var.kms_key_arn
}

resource "aws_kms_key" "dr" {
  provider            = aws.dr
  description         = "${var.name} DR backup vault key"
  enable_key_rotation = true
}

resource "aws_backup_vault" "dr" {
  provider    = aws.dr
  name        = "${var.name}-dr"
  kms_key_arn = aws_kms_key.dr.arn
}

resource "aws_backup_plan" "this" {
  name = "${var.name}-daily"
  rule {
    rule_name         = "daily"
    target_vault_name = aws_backup_vault.primary.name
    schedule          = "cron(0 17 * * ? *)" # 03:00 AEST
    lifecycle {
      delete_after = var.backup_retention_days
    }
    copy_action {
      destination_vault_arn = aws_backup_vault.dr.arn
      lifecycle {
        delete_after = var.backup_retention_days
      }
    }
  }
}

data "aws_iam_policy_document" "backup_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["backup.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "backup" {
  name               = "${var.name}-backup"
  assume_role_policy = data.aws_iam_policy_document.backup_trust.json
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_backup_selection" "this" {
  name         = "${var.name}-aurora"
  plan_id      = aws_backup_plan.this.id
  iam_role_arn = aws_iam_role.backup.arn
  resources    = [aws_rds_cluster.this.arn]
}
