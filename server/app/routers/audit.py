from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlmodel import Session
from ..db import get_session
from ..deps import require_role
from ..services.audit import export_audit_zip

router = APIRouter(prefix="/api/audit", tags=["audit"])

@router.get("/export")
def export(session: Session = Depends(get_session), _admin=Depends(require_role("admin","mod"))):
    data = export_audit_zip(session)
    headers = {"Content-Disposition": "attachment; filename=coevo_audit_export.zip"}
    return Response(content=data, media_type="application/zip", headers=headers)
