"""Passkey (WebAuthn): đăng nhập bằng Face ID / Touch ID / vân tay / Windows Hello thay cho mã PIN, theo từng thiết bị.

Chỉ chủ nhân (OWNER_CHAT_ID). Đăng ký cần phiên đã mở khoá bằng PIN; đăng nhập không cần PIN.
Xác thực tối giản theo chuẩn WebAuthn Level 2: kiểm clientDataJSON (type, challenge, origin), authenticatorData (rpIdHash, UP/UV flags,
signCount), chữ ký ES256 (P-256) hoặc RS256 bằng khoá công khai lưu lúc đăng ký (attestation "none").
Khoá lưu ở DATA_DIR/passkeys.json: {creds: [{id, pub (PEM), alg, name, created, last, count}], challenges: {}}.
"""
import base64
import datetime as dt
import hashlib
import json
import os
import secrets
import struct
import threading
import time
from urllib.parse import urlparse

from config import DATA_DIR

FILE = DATA_DIR / "passkeys.json"
_LOCK = threading.Lock()
CH_TTL = 300


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64u(s: str) -> bytes:
    s = (s or "").strip()
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    except Exception:
        d = {}
    d.setdefault("creds", [])
    d.setdefault("challenges", {})
    return d


def _save(d: dict):
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)
    try:
        os.chmod(FILE, 0o600)
    except Exception:
        pass


def rp() -> tuple[str, str]:
    """(rp_id, origin) từ WEBAPP_URL / base url."""
    base = ""
    try:
        from agents import lark_oauth
        base = lark_oauth.base_url()
    except Exception:
        pass
    base = base or os.getenv("WEBAPP_URL", "") or "http://localhost:8787"
    u = urlparse(base)
    return u.hostname or "localhost", f"{u.scheme}://{u.netloc}"


def _challenge(d: dict, kind: str) -> str:
    now = time.time()
    d["challenges"] = {k: v for k, v in d["challenges"].items() if v["exp"] > now}
    ch = _b64u(secrets.token_bytes(32))
    d["challenges"][ch] = {"kind": kind, "exp": now + CH_TTL}
    return ch


def _take_challenge(d: dict, ch: str, kind: str) -> bool:
    v = d["challenges"].pop(ch or "", None)
    return bool(v and v["kind"] == kind and v["exp"] > time.time())


def enabled() -> bool:
    return bool(_load()["creds"])


def list_creds() -> list[dict]:
    return [{k: c.get(k) for k in ("id", "name", "created", "last", "count")} for c in _load()["creds"]]


# ------------------------------------------------------------------ đăng ký
def register_options(display_name: str = "Huy") -> dict:
    rp_id, _ = rp()
    with _LOCK:
        d = _load()
        ch = _challenge(d, "reg")
        exclude = [{"type": "public-key", "id": c["id"]} for c in d["creds"]]
        _save(d)
    return {"publicKey": {"challenge": ch, "rp": {"name": "superYou", "id": rp_id},
                          "user": {"id": _b64u(b"superyou-owner"), "name": "owner@superyou", "displayName": display_name[:60]},
                          "pubKeyCredParams": [{"type": "public-key", "alg": -7}, {"type": "public-key", "alg": -257}],
                          "authenticatorSelection": {"residentKey": "preferred", "userVerification": "required"},
                          "timeout": 120000, "attestation": "none", "excludeCredentials": exclude}}


def _parse_cose(cose: bytes):
    """COSE_Key (CBOR tối giản) -> (alg, public key object)."""
    from cryptography.hazmat.primitives.asymmetric import ec, rsa
    m, _ = _cbor(cose, 0)
    alg = m.get(3)
    if m.get(1) == 2 and alg == -7:  # EC2 P-256
        x, y = int.from_bytes(m[-2], "big"), int.from_bytes(m[-3], "big")
        return alg, ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
    if m.get(1) == 3 and alg == -257:  # RSA
        n, e = int.from_bytes(m[-1], "big"), int.from_bytes(m[-2], "big")
        return alg, rsa.RSAPublicNumbers(e, n).public_key()
    raise ValueError("Thuật toán khoá không hỗ trợ")


def _cbor(b: bytes, i: int):
    """Bộ giải CBOR tối giản cho attestationObject/COSE (map, bytes, text, int, array)."""
    ib = b[i]
    major, info = ib >> 5, ib & 0x1F
    i += 1
    if info < 24:
        n = info
    elif info == 24:
        n, i = b[i], i + 1
    elif info == 25:
        n, i = struct.unpack(">H", b[i:i + 2])[0], i + 2
    elif info == 26:
        n, i = struct.unpack(">I", b[i:i + 4])[0], i + 4
    elif info == 27:
        n, i = struct.unpack(">Q", b[i:i + 8])[0], i + 8
    else:
        raise ValueError("CBOR không hỗ trợ")
    if major == 0:
        return n, i
    if major == 1:
        return -1 - n, i
    if major == 2:
        return b[i:i + n], i + n
    if major == 3:
        return b[i:i + n].decode(), i + n
    if major == 4:
        out = []
        for _ in range(n):
            v, i = _cbor(b, i)
            out.append(v)
        return out, i
    if major == 5:
        out = {}
        for _ in range(n):
            k, i = _cbor(b, i)
            v, i = _cbor(b, i)
            out[k] = v
        return out, i
    raise ValueError("CBOR không hỗ trợ")


def register_verify(resp: dict, name: str = "") -> dict:
    from cryptography.hazmat.primitives import serialization
    rp_id, origin = rp()
    cdj = _unb64u(resp.get("clientDataJSON", ""))
    cd = json.loads(cdj)
    with _LOCK:
        d = _load()
        if cd.get("type") != "webauthn.create" or not _take_challenge(d, cd.get("challenge", ""), "reg"):
            raise ValueError("Phiên đăng ký passkey đã hết hạn, thử lại")
        if cd.get("origin") != origin:
            raise ValueError("Sai nguồn gốc trang")
        att, _ = _cbor(_unb64u(resp.get("attestationObject", "")), 0)
        ad = att["authData"]
        if ad[:32] != hashlib.sha256(rp_id.encode()).digest():
            raise ValueError("Sai tên miền")
        flags = ad[32]
        if not (flags & 0x01) or not (flags & 0x40):
            raise ValueError("Thiết bị chưa xác nhận người dùng")
        cl = struct.unpack(">H", ad[53:55])[0]
        cred_id = ad[55:55 + cl]
        alg, pub = _parse_cose(ad[55 + cl:])
        pem = pub.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        cid = _b64u(cred_id)
        if any(c["id"] == cid for c in d["creds"]):
            raise ValueError("Thiết bị này đã đăng ký")
        if len(d["creds"]) >= 10:
            raise ValueError("Tối đa 10 thiết bị")
        d["creds"].append({"id": cid, "pub": pem, "alg": alg, "name": (name or "Thiết bị")[:60], "created": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
                           "last": "", "count": struct.unpack(">I", ad[33:37])[0]})
        _save(d)
    return {"ok": True, "text": f"Đã bật đăng nhập bằng Face ID / vân tay trên “{(name or 'Thiết bị')[:60]}”."}


# ------------------------------------------------------------------ đăng nhập
def login_options() -> dict:
    rp_id, _ = rp()
    with _LOCK:
        d = _load()
        if not d["creds"]:
            raise ValueError("Chưa đăng ký passkey")
        ch = _challenge(d, "auth")
        _save(d)
        allow = [{"type": "public-key", "id": c["id"]} for c in d["creds"]]
    return {"publicKey": {"challenge": ch, "rpId": rp_id, "allowCredentials": allow, "userVerification": "required", "timeout": 90000}}


def login_verify(resp: dict) -> dict:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, padding
    from cryptography.hazmat.primitives import serialization
    rp_id, origin = rp()
    cdj = _unb64u(resp.get("clientDataJSON", ""))
    cd = json.loads(cdj)
    with _LOCK:
        d = _load()
        if cd.get("type") != "webauthn.get" or not _take_challenge(d, cd.get("challenge", ""), "auth"):
            raise ValueError("Phiên đăng nhập hết hạn, thử lại")
        if cd.get("origin") != origin:
            raise ValueError("Sai nguồn gốc trang")
        cred = next((c for c in d["creds"] if c["id"] == resp.get("id")), None)
        if not cred:
            raise ValueError("Thiết bị chưa đăng ký")
        ad = _unb64u(resp.get("authenticatorData", ""))
        if ad[:32] != hashlib.sha256(rp_id.encode()).digest():
            raise ValueError("Sai tên miền")
        flags = ad[32]
        if not (flags & 0x01) or not (flags & 0x04):
            raise ValueError("Thiết bị chưa xác minh người dùng (Face ID / vân tay)")
        count = struct.unpack(">I", ad[33:37])[0]
        if count and cred.get("count") and count <= cred["count"]:
            raise ValueError("Phát hiện bộ đếm bất thường, passkey này bị từ chối")
        signed = ad + hashlib.sha256(cdj).digest()
        pub = serialization.load_pem_public_key(cred["pub"].encode())
        sig = _unb64u(resp.get("signature", ""))
        try:
            if cred["alg"] == -7:
                pub.verify(sig, signed, ec.ECDSA(hashes.SHA256()))
            else:
                pub.verify(sig, signed, padding.PKCS1v15(), hashes.SHA256())
        except Exception:
            raise ValueError("Chữ ký không hợp lệ")
        cred["count"] = count
        cred["last"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        _save(d)
    return {"ok": True, "name": cred["name"]}


def remove(cid: str) -> dict:
    with _LOCK:
        d = _load()
        d["creds"] = [c for c in d["creds"] if c["id"] != cid]
        _save(d)
    return {"text": "Đã gỡ thiết bị."}
