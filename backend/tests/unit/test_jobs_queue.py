import threading

import pytest

from app.jobs.handlers import run_worker_once
from app.jobs.queue import JobQueue
from app.services.projects import create_project


def _make_project(db_session, name="Job Testi"):
    return create_project(db_session, name=name)


@pytest.fixture(autouse=True)
def _drain_dummy_echo_queue(db_session):
    """This file's tests rely on "the job I just enqueued is the next one
    claimed" (spec's FIFO queue has only one worker in these tests). The
    underlying SQLite DB is shared across the whole test session (see
    conftest's session-scoped migration), so a `dummy_echo` job left queued
    by an earlier test elsewhere would break that assumption. Draining
    before each test here removes that cross-test coupling.
    """

    queue = JobQueue(worker_id="cleanup-worker")
    while True:
        job = queue.claim_next(db_session, kinds=["dummy_echo"])
        if job is None:
            break
        queue.complete(db_session, job.id, result={"drained_by": "test_cleanup"})
    yield


def test_enqueue_is_idempotent_on_repeated_key(db_session):
    project = _make_project(db_session)
    queue = JobQueue(worker_id="test-worker")

    first = queue.enqueue(
        db_session, project_id=project.id, kind="dummy_echo", idempotency_key="abc-1", payload={"x": 1}
    )
    second = queue.enqueue(
        db_session, project_id=project.id, kind="dummy_echo", idempotency_key="abc-1", payload={"x": 999}
    )

    assert first.id == second.id
    assert second.payload_json == {"x": 1}  # the retry did not create/overwrite a new job


def test_claim_next_transitions_queued_to_running(db_session):
    project = _make_project(db_session)
    queue = JobQueue(worker_id="test-worker")
    job = queue.enqueue(db_session, project_id=project.id, kind="dummy_echo", idempotency_key="claim-1")

    claimed = queue.claim_next(db_session, kinds=["dummy_echo"])
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.state == "running"
    assert claimed.lease_owner == "test-worker"
    assert claimed.attempt == 1
    assert claimed.lease_until is not None


def test_claim_next_returns_none_for_unmatched_kind_filter(db_session):
    project = _make_project(db_session)
    queue = JobQueue(worker_id="test-worker")
    queue.enqueue(db_session, project_id=project.id, kind="dummy_echo", idempotency_key="filter-1")

    assert queue.claim_next(db_session, kinds=["some_kind_nobody_registers"]) is None


def test_claim_next_only_gives_the_job_to_one_of_two_racing_workers(db_session):
    from app.core.db import SessionLocal

    project = _make_project(db_session)
    queue = JobQueue(worker_id="race-workers")
    job = queue.enqueue(db_session, project_id=project.id, kind="dummy_echo", idempotency_key="race-1")

    winning_ids: list = []

    def _claim():
        with SessionLocal() as session:
            claimed = queue.claim_next(session, kinds=["dummy_echo"])
            # Capture the id while the session is still open; the ORM
            # instance itself becomes unusable once this `with` block exits
            # and the session closes.
            winning_ids.append(claimed.id if claimed is not None else None)

    threads = [threading.Thread(target=_claim) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    winners = [job_id for job_id in winning_ids if job_id == job.id]
    assert len(winners) == 1, "exactly one racing claim must win the same job row"


def test_run_worker_once_completes_dummy_echo_job(db_session):
    project = _make_project(db_session)
    queue = JobQueue(worker_id="test-worker")
    job = queue.enqueue(
        db_session,
        project_id=project.id,
        kind="dummy_echo",
        idempotency_key="echo-1",
        payload={"hello": "world"},
    )

    completed = run_worker_once(db_session, queue=queue, kinds=["dummy_echo"])

    assert completed is not None
    assert completed.id == job.id
    assert completed.state == "succeeded"
    assert completed.result_json == {"echo": {"hello": "world"}}


def test_run_worker_once_returns_none_when_queue_empty(db_session):
    queue = JobQueue(worker_id="test-worker")
    assert run_worker_once(db_session, queue=queue, kinds=["dummy_echo"]) is None


def test_run_worker_once_fails_unknown_job_kind(db_session):
    project = _make_project(db_session)
    queue = JobQueue(worker_id="test-worker")
    queue.enqueue(db_session, project_id=project.id, kind="totally_unknown_kind", idempotency_key="unknown-1")

    completed = run_worker_once(db_session, queue=queue, kinds=["totally_unknown_kind"])

    assert completed is not None
    assert completed.state == "failed"
    assert completed.error_code == "unknown_job_kind"


def test_pause_then_resume_returns_job_to_queued(db_session):
    project = _make_project(db_session)
    queue = JobQueue(worker_id="test-worker")
    job = queue.enqueue(db_session, project_id=project.id, kind="dummy_echo", idempotency_key="pause-1")

    paused = queue.pause(db_session, job.id)
    assert paused.state == "paused"

    resumed = queue.resume(db_session, job.id)
    assert resumed.state == "queued"
    assert resumed.lease_owner is None


def test_cancel_running_job_sets_cancel_requested(db_session):
    project = _make_project(db_session)
    queue = JobQueue(worker_id="test-worker")
    job = queue.enqueue(db_session, project_id=project.id, kind="dummy_echo", idempotency_key="cancel-1")
    claimed = queue.claim_next(db_session, kinds=["dummy_echo"])
    assert claimed.id == job.id

    cancelled = queue.cancel(db_session, job.id)
    assert cancelled.state == "cancel_requested"


def test_cancel_queued_job_cancels_immediately(db_session):
    project = _make_project(db_session)
    queue = JobQueue(worker_id="test-worker")
    job = queue.enqueue(db_session, project_id=project.id, kind="dummy_echo", idempotency_key="cancel-2")

    cancelled = queue.cancel(db_session, job.id)
    assert cancelled.state == "cancelled"


def test_reap_expired_leases_marks_interrupted(db_session):
    from datetime import timedelta

    from app.models.base import utcnow

    project = _make_project(db_session)
    queue = JobQueue(worker_id="test-worker")
    job = queue.enqueue(db_session, project_id=project.id, kind="dummy_echo", idempotency_key="reap-1")
    claimed = queue.claim_next(db_session, kinds=["dummy_echo"])
    assert claimed.id == job.id

    # Simulate an expired lease (worker crashed) directly, bypassing the
    # normal 30s wait.
    claimed.lease_until = utcnow() - timedelta(seconds=1)
    db_session.commit()

    interrupted = queue.reap_expired_leases(db_session)
    assert any(j.id == job.id for j in interrupted)
    db_session.refresh(claimed)
    assert claimed.state == "interrupted"
