"""Adapter contract tests: every adapter for a port behaves the same. AWS adapters run against moto;
Azure adapters run in the nightly Azure pipeline (CONTRACT_AZURE=1) against real resources."""

from __future__ import annotations

import json
import os

import boto3
import pytest
from moto import mock_aws

from complymate.adapters.local.cron_scheduler import cron_matches
from complymate.adapters.local.dev_identity import DevIdentity
from complymate.adapters.local.fake_embeddings import FakeEmbeddings
from complymate.adapters.local.fake_llm import FakeLLM
from complymate.adapters.local.file_audit_sink import FileAuditSink
from complymate.adapters.local.local_kms import LocalKMS
from complymate.ports.llm import ChatMessage
from complymate.ports.queue import QueueName

pytestmark = pytest.mark.contract
REGION = "ap-southeast-2"


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    from complymate.adapters.aws import _session

    _session.client.cache_clear()


# ---------------- storage ----------------


async def _storage_contract(storage, bucket: str) -> None:
    await storage.put_object(bucket, "t1/a.txt", b"hello", "text/plain", {"tenant-id": "t1"})
    obj = await storage.get_object(bucket, "t1/a.txt")
    assert obj.data == b"hello"
    assert obj.metadata.get("tenant-id") == "t1"
    assert (await storage.presigned_get_url(bucket, "t1/a.txt")).startswith("http")
    await storage.delete_object(bucket, "t1/a.txt")


async def test_s3_storage_contract():
    from complymate.adapters.aws.s3_storage import S3Storage

    with mock_aws():
        boto3.client("s3", region_name=REGION).create_bucket(
            Bucket="docs", CreateBucketConfiguration={"LocationConstraint": REGION}
        )
        await _storage_contract(S3Storage(REGION), "docs")


# ---------------- queue ----------------


async def test_sqs_queue_contract():
    from complymate.adapters.aws.sqs_queue import SqsQueue

    with mock_aws():
        sqs = boto3.client("sqs", region_name=REGION)
        url = sqs.create_queue(QueueName="complymate-test-ocr")["QueueUrl"]
        queue = SqsQueue(REGION, url.removesuffix("ocr"))
        msg_id = await queue.send(QueueName.OCR, {"task": "ocr_document", "payload": {"x": 1}})
        assert msg_id
        body = json.loads(sqs.receive_message(QueueUrl=url)["Messages"][0]["Body"])
        assert body["task"] == "ocr_document"


async def test_memory_queue_contract():
    from complymate.adapters.local.memory_queue import MemoryQueue

    seen = []

    async def dispatcher(task, payload):
        seen.append((task, payload))

    q = MemoryQueue(dispatcher)
    await q.send(QueueName.OCR, {"task": "ocr_document", "payload": {"x": 1}})
    await q.drain()
    assert seen == [("ocr_document", {"x": 1})]


# ---------------- secrets & kms ----------------


async def test_secrets_manager_contract():
    from complymate.adapters.aws.secrets_manager import SecretsManagerStore

    with mock_aws():
        boto3.client("secretsmanager", region_name=REGION).create_secret(
            Name="complymate/test/db", SecretString=json.dumps({"username": "u", "password": "p"})
        )
        store = SecretsManagerStore(REGION)
        assert (await store.get_json("complymate/test/db"))["password"] == "p"


async def test_env_secrets_contract(monkeypatch):
    from complymate.adapters.local.env_secrets import EnvSecrets

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test")
    assert await EnvSecrets().get_secret("stripe/secret_key") == "sk_test"


@pytest.mark.parametrize("kind", ["local", "aws"])
async def test_kms_contract(kind):
    if kind == "local":
        kms = LocalKMS("secret")
        dk = await kms.generate_data_key("tenant-1")
        assert await kms.decrypt_data_key(dk.ciphertext, "tenant-1") == dk.plaintext
        with pytest.raises(Exception):
            await kms.decrypt_data_key(dk.ciphertext, "tenant-2")
        return
    from complymate.adapters.aws.kms import AwsKMS

    with mock_aws():
        key_id = boto3.client("kms", region_name=REGION).create_key()["KeyMetadata"]["KeyId"]
        kms = AwsKMS(REGION, key_id)
        dk = await kms.generate_data_key("tenant-1")
        assert await kms.decrypt_data_key(dk.ciphertext, "tenant-1") == dk.plaintext
        with pytest.raises(Exception):
            await kms.decrypt_data_key(dk.ciphertext, "tenant-2")


# ---------------- email ----------------


async def test_ses_email_contract():
    from complymate.adapters.aws.ses_email import SesEmail

    with mock_aws():
        boto3.client("ses", region_name=REGION).verify_email_identity(EmailAddress="no-reply@test.example")
        sender = SesEmail(REGION, "no-reply@test.example")
        assert await sender.send(["a@test.example"], "Hi", "<p>Hi</p>", "Hi")


# ---------------- audit sink ----------------


async def test_file_audit_sink_is_write_once(tmp_path):
    sink = FileAuditSink(str(tmp_path))
    await sink.write_batch("t1", "2026/01/01/1-2", [{"seq": 1}, {"seq": 2}])
    with pytest.raises(FileExistsError):
        await sink.write_batch("t1", "2026/01/01/1-2", [{"seq": 1}])


# ---------------- identity / llm / embeddings ----------------


async def test_dev_identity_round_trip():
    idp = DevIdentity("secret")
    claims = await idp.verify_token(idp.issue_token("sub-1", "a@test.example"))
    assert claims.sub == "sub-1" and claims.mfa_verified and claims.auth_time is not None
    await idp.disable_user("sub-1")
    with pytest.raises(Exception):
        await idp.verify_token(idp.issue_token("sub-1", "a@test.example"))


async def test_fake_llm_cites_sources_and_streams():
    llm = FakeLLM()
    msg = [ChatMessage("user", "Question: x\n\nSources:\n[S1] Title\nRecords must be kept for 7 years.")]
    result = await llm.complete("system", msg)
    assert "[S1]" in result.text
    assert "".join([c async for c in llm.stream("system", msg)]) == result.text


async def test_embeddings_dimensions_and_similarity():
    emb = FakeEmbeddings(1024)
    a, b, c = await emb.embed(["suspicious matter report timeframe", "SMR suspicious matter report deadline", "fish"])
    dot = lambda x, y: sum(i * j for i, j in zip(x, y, strict=True))  # noqa: E731
    assert len(a) == 1024
    assert dot(a, b) > dot(a, c)


def test_cron_matching():
    from datetime import datetime

    assert cron_matches("*/15 * * * *", datetime(2026, 1, 1, 10, 30))
    assert not cron_matches("0 2 * * *", datetime(2026, 1, 1, 3, 0))


def test_eventbridge_cron_expression():
    from complymate.adapters.aws.eventbridge_scheduler import EventBridgeScheduler

    assert EventBridgeScheduler._expression("0 2 * * *") == "cron(0 2 * * ? *)"
    assert EventBridgeScheduler._expression("0 9 * * 1") == "cron(0 9 ? * 1 *)"


@pytest.mark.skipif(not os.environ.get("CONTRACT_AZURE"), reason="Azure contract tests run in the nightly Azure job")
async def test_azure_blob_storage_contract():
    from complymate.adapters.azure.blob_storage import BlobStorage

    await _storage_contract(BlobStorage(os.environ["AZURE_STORAGE_ACCOUNT_URL"]), "contract-tests")
