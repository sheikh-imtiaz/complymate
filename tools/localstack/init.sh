#!/bin/sh
# LocalStack bootstrap: queues, secrets and a KMS key that mirror the AWS names, so the AWS adapters can be
# exercised locally with CLOUD_PROVIDER=aws + AWS_ENDPOINT_URL=http://localhost:4566.
set -e
REGION=ap-southeast-2
PREFIX=complymate-local

for q in ocr screening exports notifications audit; do
  awslocal sqs create-queue --region "$REGION" --queue-name "${PREFIX}-${q}-dlq" >/dev/null
  DLQ_ARN=$(awslocal sqs get-queue-attributes --region "$REGION" \
    --queue-url "http://localhost:4566/000000000000/${PREFIX}-${q}-dlq" --attribute-names QueueArn \
    --query Attributes.QueueArn --output text)
  awslocal sqs create-queue --region "$REGION" --queue-name "${PREFIX}-${q}" \
    --attributes "{\"RedrivePolicy\":\"{\\\"deadLetterTargetArn\\\":\\\"${DLQ_ARN}\\\",\\\"maxReceiveCount\\\":\\\"5\\\"}\"}" >/dev/null
done

awslocal kms create-alias --region "$REGION" --alias-name alias/complymate-local \
  --target-key-id "$(awslocal kms create-key --region "$REGION" --query KeyMetadata.KeyId --output text)"

awslocal secretsmanager create-secret --region "$REGION" --name complymate/local/db-app \
  --secret-string '{"username":"complymate_app","password":"app_password","host":"postgres","port":5432,"dbname":"complymate"}' >/dev/null
awslocal secretsmanager create-secret --region "$REGION" --name complymate/local/stripe \
  --secret-string '{"secret_key":"sk_test_placeholder","webhook_secret":"whsec_placeholder"}' >/dev/null

awslocal ses verify-email-identity --region "$REGION" --email-address no-reply@complymate.test
awslocal scheduler create-schedule-group --region "$REGION" --name complymate-local >/dev/null 2>&1 || true

echo "LocalStack ready: queues ${PREFIX}-*, KMS alias/complymate-local, secrets complymate/local/*"
