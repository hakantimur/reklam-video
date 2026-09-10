"""Budget ledger (spec 19.1).

``available = user_cap - settled_cost - active_reservations``

`user_cap` comes from the latest brief's `budget_microusd` (there is no
separate "set budget" endpoint yet — the brief is the only place the user
states a cap). Every reservation/settlement/release is an immutable
`BudgetEntry` row; nothing is ever updated in place, so the ledger is
always reconstructable by replaying entries.
"""

from __future__ import annotations

import threading

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.jobs import BudgetEntry
from app.models.project import Brief
from app.services.errors import BlockedError

# `settle()` does a check-then-insert to keep a job from being settled twice
# (spec 19.1: "Aynı işi iki worker'ın settle etmesi unique constraint ile
# engellenir"). The schema for this round has no DB-level unique constraint
# on (job_id, entry_type) — adding one means a new Alembic migration, which
# is out of scope for this round — so this lock is the enforcement boundary.
# It only protects against races *within this process*; a second process
# writing to the same SQLite file could still interleave between the check
# and the insert. Flagged here for the coordinator/next round to promote to
# a real unique index when a migration is allowed.
_settle_lock = threading.Lock()


class BudgetSummary:
    def __init__(self, user_cap_microusd: int | None, settled_microusd: int, reserved_microusd: int) -> None:
        self.user_cap_microusd = user_cap_microusd
        self.settled_cost_microusd = settled_microusd
        self.active_reservations_microusd = reserved_microusd
        self.available_microusd = (
            None if user_cap_microusd is None else user_cap_microusd - settled_microusd - reserved_microusd
        )

    def as_dict(self) -> dict:
        return {
            "user_cap_microusd": self.user_cap_microusd,
            "settled_cost_microusd": self.settled_cost_microusd,
            "active_reservations_microusd": self.active_reservations_microusd,
            "available_microusd": self.available_microusd,
        }


def _sum_entries(session: Session, project_id: str, entry_type: str) -> int:
    total = session.execute(
        select(func.coalesce(func.sum(BudgetEntry.amount_microusd), 0)).where(
            BudgetEntry.project_id == project_id, BudgetEntry.entry_type == entry_type
        )
    ).scalar_one()
    return int(total)


def get_budget_summary(session: Session, project_id: str) -> BudgetSummary:
    user_cap = (
        session.execute(
            select(Brief.budget_microusd).where(Brief.project_id == project_id).order_by(Brief.revision.desc())
        )
        .scalars()
        .first()
    )
    settled = _sum_entries(session, project_id, "settlement")
    reserved = _sum_entries(session, project_id, "reservation") - _sum_entries(session, project_id, "release")
    return BudgetSummary(user_cap, settled, reserved)


def reserve(
    session: Session,
    project_id: str,
    amount_microusd: int,
    *,
    job_id: str | None = None,
    provider_request_id: str | None = None,
) -> BudgetEntry:
    """Reserve budget for a job about to be submitted to a paid provider.

    Spec 19.1: an unknown price is never treated as free — if the cap is
    unknown (no brief yet) or the reservation would exceed what's available,
    this raises `BlockedError` instead of silently starting paid work.
    """

    if amount_microusd <= 0:
        raise ValueError("amount_microusd must be positive")

    summary = get_budget_summary(session, project_id)
    if summary.user_cap_microusd is None:
        raise BlockedError(
            "Bu proje için bütçe tanımlı değil (önce brief kaydedilmeli)",
            details={"project_id": project_id},
        )
    if amount_microusd > summary.available_microusd:
        raise BlockedError(
            "Bu işin tahmini maliyeti kalan bütçeyi aşıyor",
            details={
                "available_microusd": summary.available_microusd,
                "requested_microusd": amount_microusd,
            },
        )

    entry = BudgetEntry(
        project_id=project_id,
        job_id=job_id,
        entry_type="reservation",
        amount_microusd=amount_microusd,
        confidence="estimated",
        provider_request_id=provider_request_id,
        created_at=utcnow(),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def release(
    session: Session,
    project_id: str,
    amount_microusd: int,
    *,
    job_id: str | None = None,
    provider_request_id: str | None = None,
) -> BudgetEntry:
    if amount_microusd <= 0:
        raise ValueError("amount_microusd must be positive")
    entry = BudgetEntry(
        project_id=project_id,
        job_id=job_id,
        entry_type="release",
        amount_microusd=amount_microusd,
        confidence="confirmed",
        provider_request_id=provider_request_id,
        created_at=utcnow(),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def settle(
    session: Session,
    project_id: str,
    *,
    job_id: str,
    actual_amount_microusd: int,
    reserved_amount_microusd: int | None = None,
    provider_request_id: str | None = None,
) -> BudgetEntry:
    """Turn a reservation into a confirmed settlement, releasing any leftover.

    Raises `BlockedError` if this job has already been settled, so two
    workers racing to settle the same job cannot both succeed.
    """

    with _settle_lock:
        existing = (
            session.execute(
                select(BudgetEntry).where(
                    BudgetEntry.project_id == project_id,
                    BudgetEntry.job_id == job_id,
                    BudgetEntry.entry_type == "settlement",
                )
            )
            .scalars()
            .first()
        )
        if existing is not None:
            raise BlockedError(
                f"Job {job_id} is already settled", details={"job_id": job_id, "settlement_id": existing.id}
            )

        settlement = BudgetEntry(
            project_id=project_id,
            job_id=job_id,
            entry_type="settlement",
            amount_microusd=actual_amount_microusd,
            confidence="confirmed",
            provider_request_id=provider_request_id,
            created_at=utcnow(),
        )
        session.add(settlement)

        if reserved_amount_microusd is not None and reserved_amount_microusd > 0:
            # Close out the *entire* reservation, not just the difference:
            # the settlement entry above already records the actual cost in
            # its own ledger row, so releasing the full reserved amount here
            # is what makes `active_reservations` for this job go back to
            # zero rather than being double-counted alongside the
            # settlement (see `get_budget_summary`: settled and reservation
            # are separate sums).
            session.add(
                BudgetEntry(
                    project_id=project_id,
                    job_id=job_id,
                    entry_type="release",
                    amount_microusd=reserved_amount_microusd,
                    confidence="confirmed",
                    provider_request_id=provider_request_id,
                    created_at=utcnow(),
                )
            )

        session.commit()
        session.refresh(settlement)
        return settlement
