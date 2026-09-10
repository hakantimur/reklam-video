import pytest

from app.jobs.queue import JobQueue
from app.services import budget as budget_service
from app.services import projects as projects_service
from app.services.errors import BlockedError


def _project_with_budget(db_session, budget_microusd=100_000_000, name="Butce Testi"):
    project = projects_service.create_project(db_session, name=name)
    projects_service.put_brief(
        db_session,
        project.id,
        audience="test kitle",
        single_message="test mesaj",
        objective="install",
        style_id="style-1",
        language="tr",
        target_frames=300,
        fps_num=30,
        fps_den=1,
        placement_id="placement-1",
        budget_microusd=budget_microusd,
        product_name="Test Urunu",
        description="Test aciklamasi",
        cta="Simdi indir",
    )
    return project


def _real_job_id(db_session, project_id: str, idempotency_key: str) -> str:
    """`budget_entries.job_id` is a real foreign key to `jobs.id` — a
    made-up string would trip the FK constraint, so tests reserve/settle
    against an actual enqueued job, as production code would."""

    queue = JobQueue(worker_id="budget-test-worker")
    job = queue.enqueue(
        db_session, project_id=project_id, kind="dummy_echo", idempotency_key=idempotency_key
    )
    return job.id


def test_available_equals_cap_when_no_activity(db_session):
    project = _project_with_budget(db_session, budget_microusd=100_000_000)
    summary = budget_service.get_budget_summary(db_session, project.id)
    assert summary.user_cap_microusd == 100_000_000
    assert summary.settled_cost_microusd == 0
    assert summary.active_reservations_microusd == 0
    assert summary.available_microusd == 100_000_000


def test_reserve_reduces_available(db_session):
    project = _project_with_budget(db_session, budget_microusd=100_000_000)
    job_id = _real_job_id(db_session, project.id, "budget-reserve-1")
    budget_service.reserve(db_session, project.id, 20_000_000, job_id=job_id)

    summary = budget_service.get_budget_summary(db_session, project.id)
    assert summary.active_reservations_microusd == 20_000_000
    assert summary.available_microusd == 80_000_000


def test_reserve_beyond_available_is_blocked(db_session):
    project = _project_with_budget(db_session, budget_microusd=10_000_000)
    job_id = _real_job_id(db_session, project.id, "budget-reserve-2")
    with pytest.raises(BlockedError):
        budget_service.reserve(db_session, project.id, 20_000_000, job_id=job_id)


def test_reserve_without_any_brief_is_blocked(db_session):
    project = projects_service.create_project(db_session, name="Briefsiz Proje")
    job_id = _real_job_id(db_session, project.id, "budget-reserve-3")
    with pytest.raises(BlockedError):
        budget_service.reserve(db_session, project.id, 1, job_id=job_id)


def test_settle_moves_reservation_to_settled_and_releases_leftover(db_session):
    project = _project_with_budget(db_session, budget_microusd=100_000_000)
    job_id = _real_job_id(db_session, project.id, "budget-settle-1")
    reservation = budget_service.reserve(db_session, project.id, 30_000_000, job_id=job_id)

    budget_service.settle(
        db_session,
        project.id,
        job_id=job_id,
        actual_amount_microusd=25_000_000,
        reserved_amount_microusd=reservation.amount_microusd,
    )

    summary = budget_service.get_budget_summary(db_session, project.id)
    assert summary.settled_cost_microusd == 25_000_000
    # 30M reserved, 25M settled, 5M released back -> 0 still "active".
    assert summary.active_reservations_microusd == 0
    assert summary.available_microusd == 75_000_000


def test_settling_same_job_twice_is_blocked(db_session):
    project = _project_with_budget(db_session, budget_microusd=100_000_000)
    job_id = _real_job_id(db_session, project.id, "budget-settle-2")
    budget_service.reserve(db_session, project.id, 10_000_000, job_id=job_id)
    budget_service.settle(db_session, project.id, job_id=job_id, actual_amount_microusd=10_000_000)

    with pytest.raises(BlockedError):
        budget_service.settle(db_session, project.id, job_id=job_id, actual_amount_microusd=10_000_000)
