output "kms_key_arn" { value = aws_kms_key.data.arn }
output "kms_key_id" { value = aws_kms_key.data.key_id }
output "documents_bucket" { value = aws_s3_bucket.this["documents"].bucket }
output "exports_bucket" { value = aws_s3_bucket.this["exports"].bucket }
output "audit_bucket" { value = aws_s3_bucket.this["audit"].bucket }
output "bucket_arns" { value = { for k, b in aws_s3_bucket.this : k => b.arn } }
