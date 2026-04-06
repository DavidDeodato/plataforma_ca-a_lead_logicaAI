from contextlib import asynccontextmanager
import os
from threading import Event, Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.leads import router as leads_router
from app.api.routes.management import router as management_router
from app.api.routes.ops import router as ops_router
from app.api.webhooks.wasender import router as wasender_webhook_router
from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.services.whatsapp_sessions import WhatsappSessionService
from app.workers.followup_worker import process_pending_tasks


settings = get_settings()


def _background_worker_loop(stop_event: Event) -> None:
    while not stop_event.is_set():
        try:
            process_pending_tasks()
        except Exception:
            pass
        if stop_event.wait(5):
            break

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        WhatsappSessionService().ensure_env_backed_session(db)
        db.commit()
    stop_event: Event | None = None
    worker_thread: Thread | None = None
    if "PYTEST_CURRENT_TEST" not in os.environ:
        stop_event = Event()
        worker_thread = Thread(target=_background_worker_loop, args=(stop_event,), daemon=True, name="followup-worker")
        worker_thread.start()
    yield
    if stop_event and worker_thread:
        stop_event.set()
        worker_thread.join(timeout=1)


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


app.include_router(leads_router)
app.include_router(management_router)
app.include_router(ops_router)
app.include_router(wasender_webhook_router)
