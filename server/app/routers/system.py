from fastapi import APIRouter
from ..main import NODE_PUBLIC_KEY_PEM

router = APIRouter(prefix="/api/system", tags=["system"])

@router.get("/public-key")
def public_key():
    return {"public_key_pem": NODE_PUBLIC_KEY_PEM}
