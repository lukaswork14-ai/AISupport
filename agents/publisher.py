"""Đăng bài lên Facebook Page qua Graph API.
Cấu hình trong .env (bạn tự điền, bot không lưu mật khẩu):
  FB_PAGES=Tên page 1|PAGE_ID_1|PAGE_ACCESS_TOKEN_1;Tên page 2|PAGE_ID_2|PAGE_ACCESS_TOKEN_2
  MANUAL_TARGETS=Group Seller POD;Group TikTok Shop VN;Facebook cá nhân;TikTok cá nhân
Group và trang cá nhân: Facebook không cho đăng qua API nữa -> bot gửi gói nội dung sẵn để bạn dán."""
import os

import requests

GRAPH = "https://graph.facebook.com/v21.0"
GRAPH_VIDEO = "https://graph-video.facebook.com/v21.0"


def pages() -> list[dict]:
    out = []
    for chunk in os.getenv("FB_PAGES", "").split(";"):
        parts = [p.strip() for p in chunk.split("|")]
        if len(parts) == 3 and all(parts):
            out.append({"name": parts[0], "id": parts[1], "token": parts[2]})
    return out


def manual_targets() -> list[str]:
    return [t.strip() for t in os.getenv("MANUAL_TARGETS", "").split(";") if t.strip()]


def _check(r):
    data = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in data:
        msg = data.get("error", {}).get("message", r.text[:300])
        raise RuntimeError(f"Facebook từ chối: {msg}")
    return data


def post_photo(page: dict, image_path: str, message: str) -> str:
    with open(image_path, "rb") as f:
        r = requests.post(f"{GRAPH}/{page['id']}/photos", timeout=120,
                          data={"message": message, "access_token": page["token"]}, files={"source": f})
    d = _check(r)
    return f"https://www.facebook.com/{d.get('post_id') or d.get('id')}"


def post_video(page: dict, video_path: str, description: str) -> str:
    with open(video_path, "rb") as f:
        r = requests.post(f"{GRAPH_VIDEO}/{page['id']}/videos", timeout=600,
                          data={"description": description, "access_token": page["token"]}, files={"source": f})
    d = _check(r)
    return f"https://www.facebook.com/{d.get('id')}"


def post_text(page: dict, message: str) -> str:
    r = requests.post(f"{GRAPH}/{page['id']}/feed", timeout=60, data={"message": message, "access_token": page["token"]})
    d = _check(r)
    return f"https://www.facebook.com/{d.get('id')}"
