import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from service import QueryService, ServiceError
from storage import ConflictError, JobStore


@pytest.fixture
def service(tmp_path):
    return QueryService(JobStore(tmp_path / "jobs.sqlite"))


def test_cache_isolated_by_owner_and_ttl(tmp_path):
    now = [0.0]
    service = QueryService(
        JobStore(tmp_path / "jobs.sqlite"), ttl_seconds=1, clock=lambda: now[0]
    )
    assert service.query("alice", "refund")["cache_hit"] is False
    assert service.query("alice", "refund")["cache_hit"] is True
    assert service.query("bob", "refund")["cache_hit"] is False
    now[0] = 1
    assert service.query("alice", "refund")["cache_hit"] is False


@pytest.mark.parametrize("question", [None, 3, "", " " * 3, "a" * 101])
def test_reject_invalid_question(service, question):
    with pytest.raises(ServiceError, match="question"):
        service.query("alice", question)


def test_idempotency_and_owner_namespace(service):
    first, created = service.submit("alice", "key", "refund")
    repeated, created_again = service.submit("alice", "key", "refund")
    assert created and not created_again
    assert first["job_id"] == repeated["job_id"]
    with pytest.raises(ConflictError):
        service.submit("alice", "key", "support")
    other, _ = service.submit("bob", "key", "refund")
    assert other["job_id"] != first["job_id"]
    assert service.store.get("bob", first["job_id"]) is None


def test_concurrent_submission_creates_one_job(service):
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(
            executor.map(lambda _: service.submit("alice", "key", "refund"), range(8))
        )
    assert sum(created for _, created in results) == 1
    assert len({job["job_id"] for job, _ in results}) == 1


def test_cancel_pending_and_late_result_cannot_override(service):
    pending, _ = service.submit("alice", "pending", "refund")
    assert service.store.cancel("alice", pending["job_id"])["status"] == "cancelled"
    assert service.run_one() is False
    running, _ = service.submit("alice", "running", "refund")
    service.store.claim_next()
    service.store.cancel("alice", running["job_id"])
    service.store.finish(running["job_id"], "completed", {"answer": "late"})
    assert service.store.get("alice", running["job_id"])["status"] == "cancelled"


def test_worker_completion_and_timeout(service):
    good, _ = service.submit("alice", "good", "refund")
    bad, _ = service.submit("alice", "bad", "simulate_timeout")
    assert service.run_one() and service.run_one()
    assert service.store.get("alice", good["job_id"])["status"] == "completed"
    assert (
        json.loads(service.store.get("alice", bad["job_id"])["result"])["code"]
        == "upstream_timeout"
    )


def test_restart_keeps_pending_completed_and_marks_running_failed(service):
    running, _ = service.submit("alice", "running", "refund")
    service.store.claim_next()
    pending, _ = service.submit("alice", "pending", "support")
    restarted = QueryService(JobStore(service.store.path))
    assert restarted.store.recover_running() == 1
    assert restarted.store.get("alice", running["job_id"])["status"] == "failed"
    assert restarted.store.get("alice", pending["job_id"])["status"] == "pending"
    assert restarted.run_one()
    third = JobStore(service.store.path)
    assert third.get("alice", pending["job_id"])["status"] == "completed"


def test_cache_is_bounded(service):
    for index in range(40):
        service.query("alice", str(index))
    assert len(service.cache) == 32
