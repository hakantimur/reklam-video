"""`app.jobs.handlers._settle_llm_cost` and `_settle_generation_cost` are
where job handlers turn a provider's own confirmed spend (OpenRouter's
`usage.cost`, never an estimate) into a real `BudgetEntry` settlement row.
Neither must ever raise — a bookkeeping failure must not turn an
otherwise-successful job into a failed one."""

from types import SimpleNamespace

from app.jobs.handlers import _settle_generation_cost, _settle_llm_cost
from app.models.asset import Asset
from app.models.jobs import BudgetEntry, Job
from app.services import projects as projects_service


def _make_project_and_job(session, kind="generate_ai_scene"):
    project = projects_service.create_project(session, name="Settle Testi")
    job = Job(project_id=project.id, kind=kind, state="running", idempotency_key="k1")
    session.add(job)
    session.flush()
    return project, job


def test_settle_llm_cost_records_a_settlement(db_session):
    project, job = _make_project_and_job(db_session, kind="discover")

    _settle_llm_cost(db_session, job, cost_usd=0.00035)

    entries = db_session.query(BudgetEntry).filter_by(project_id=project.id, job_id=job.id).all()
    assert len(entries) == 1
    assert entries[0].entry_type == "settlement"
    assert entries[0].amount_microusd == 350
    assert entries[0].confidence == "confirmed"


def test_settle_llm_cost_noop_when_zero(db_session):
    project, job = _make_project_and_job(db_session, kind="discover")

    _settle_llm_cost(db_session, job, cost_usd=0.0)

    assert db_session.query(BudgetEntry).filter_by(project_id=project.id).count() == 0


def test_settle_llm_cost_never_raises_on_double_settle(db_session):
    project, job = _make_project_and_job(db_session, kind="discover")

    _settle_llm_cost(db_session, job, cost_usd=0.1)
    # A second call for the same job (e.g. a retried handler) must not
    # raise — settle() itself rejects the double-settlement, and this
    # helper swallows that rather than failing the job a second time.
    _settle_llm_cost(db_session, job, cost_usd=0.1)

    assert db_session.query(BudgetEntry).filter_by(project_id=project.id, job_id=job.id).count() == 1


def test_settle_generation_cost_sums_video_and_text_cost(db_session):
    project, job = _make_project_and_job(db_session)
    asset = Asset(
        project_id=project.id, type="video", origin="provider_generation", relative_path="x.mp4",
        sha256="h", byte_size=1,
        metadata_json={"provider": {"model": "google/veo-3.1-lite", "actual_cost_usd": 0.32}},
    )
    db_session.add(asset)
    db_session.commit()
    text_provider = SimpleNamespace(total_cost_usd=0.0004)

    _settle_generation_cost(db_session, job, asset_id=asset.id, text_provider=text_provider)

    entries = db_session.query(BudgetEntry).filter_by(project_id=project.id, job_id=job.id).all()
    assert len(entries) == 1
    assert entries[0].amount_microusd == 320_400  # (0.32 + 0.0004) * 1_000_000


def test_settle_generation_cost_noop_when_no_cost_reported(db_session):
    project, job = _make_project_and_job(db_session)
    asset = Asset(
        project_id=project.id, type="video", origin="provider_generation", relative_path="x.mp4",
        sha256="h", byte_size=1, metadata_json={"provider": {"model": "m", "actual_cost_usd": None}},
    )
    db_session.add(asset)
    db_session.commit()
    text_provider = SimpleNamespace(total_cost_usd=0.0)

    _settle_generation_cost(db_session, job, asset_id=asset.id, text_provider=text_provider)

    assert db_session.query(BudgetEntry).filter_by(project_id=project.id).count() == 0


def test_settle_generation_cost_noop_when_asset_missing(db_session):
    project, job = _make_project_and_job(db_session)
    text_provider = SimpleNamespace(total_cost_usd=0.0)

    _settle_generation_cost(db_session, job, asset_id="does-not-exist", text_provider=text_provider)

    assert db_session.query(BudgetEntry).filter_by(project_id=project.id).count() == 0
