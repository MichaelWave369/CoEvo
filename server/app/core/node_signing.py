import base64
import json
import os
from typing import Any, Tuple
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def load_or_create_node_key(path: str) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path, "rb") as f:
            pem = f.read()
        priv = serialization.load_pem_private_key(pem, password=None)
        assert isinstance(priv, Ed25519PrivateKey)
        return priv, priv.public_key()

    priv = Ed25519PrivateKey.generate()
    pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with open(path, "wb") as f:
        f.write(pem)
    return priv, priv.public_key()

def public_key_pem(pub: Ed25519PublicKey) -> str:
    pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pem.decode("utf-8")

def sign(priv: Ed25519PrivateKey, payload: Any) -> str:
    sig = priv.sign(_canon(payload))
    return base64.b64encode(sig).decode("ascii")
