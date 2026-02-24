import os
import hashlib
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from ..db import get_session
from ..models import Artifact, ThreadArtifact
from ..deps import get_current_user
from ..core.config import settings
from ..services.events_log import log_event

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])

def ensure_dirs():
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_artifact(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    ensure_dirs()
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    sha = hashlib.sha256(data).hexdigest()
    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    storage_path = os.path.join(settings.UPLOAD_DIR, f"{sha}_{safe_name}")
    with open(storage_path, "wb") as f:
        f.write(data)

    art = Artifact(
        uploader_user_id=user.id,
        filename=safe_name,
        mime=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        sha256=sha,
        storage_path=storage_path,
    )
    session.add(art)
    session.commit()
    session.refresh(art)
    log_event(session, "artifact_uploaded", {"artifact_id": art.id, "by": user.handle, "sha256": art.sha256})
    return {
        "id": art.id,
        "filename": art.filename,
        "mime": art.mime,
        "size_bytes": art.size_bytes,
        "sha256": art.sha256,
        "created_at": art.created_at.isoformat() + "Z"
    }

@router.get("")
def list_artifacts(session: Session = Depends(get_session), user=Depends(get_current_user)):
    arts = session.exec(select(Artifact).order_by(Artifact.id.desc())).all()
    return [{
        "id": a.id, "filename": a.filename, "mime": a.mime, "size_bytes": a.size_bytes,
        "sha256": a.sha256, "created_at": a.created_at.isoformat()+"Z"
    } for a in arts]

@router.post("/{artifact_id}/attach/thread/{thread_id}")
def attach_to_thread(artifact_id: int, thread_id: int, session: Session = Depends(get_session), user=Depends(get_current_user)):
    existing = session.exec(select(ThreadArtifact).where(
        ThreadArtifact.thread_id==thread_id, ThreadArtifact.artifact_id==artifact_id
    )).first()
    if existing:
        return {"ok": True}
    ta = ThreadArtifact(thread_id=thread_id, artifact_id=artifact_id)
    session.add(ta)
    session.commit()
    log_event(session, "artifact_attached", {"artifact_id": artifact_id, "thread_id": thread_id, "by": user.handle})
    return {"ok": True}

@router.get("/{artifact_id}/download")
def download_artifact(artifact_id: int, session: Session = Depends(get_session), user=Depends(get_current_user)):
    a = session.get(Artifact, artifact_id)
    if not a:
        raise HTTPException(404, "Not found")
    if not os.path.exists(a.storage_path):
        raise HTTPException(404, "File missing on disk")
    return FileResponse(a.storage_path, filename=a.filename, media_type=a.mime)
