from app.api import assets, briefs, concepts, events, jobs, plans, projects, settings

# The coordinator mounts these onto the shared FastAPI app in `app/main.py`
# (e.g. `for r in ROUTERS: app.include_router(r, prefix="/api/v1")`), the
# same way `health_router` is already mounted there. This module does not
# touch `main.py` itself.
ROUTERS = [
    projects.router,
    briefs.router,
    assets.router,
    jobs.router,
    settings.router,
    events.router,
    concepts.router,
    plans.router,
]

__all__ = ["ROUTERS"]
