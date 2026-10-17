"""Ráp trang app superHuy / superYou HQ từ các phần nguồn theo mảng (docs/product-ownership.md).

Nguồn: webapp/app/shell.html (khung HTML) + webapp/app/css/*.css + webapp/app/js/*.js, ghép theo thứ tự tên file
thành MỘT trang duy nhất với <style> và <script> nội tuyến, giống hệt trước khi tách. Nhờ vậy:
- CSP, biến thể superYou cho khách (server._app_index) và tốc độ tải một lần không đổi;
- mỗi mảng sửa file của mình, không ai sửa chung một file 4.000 dòng.
Thêm phần mới: tạo file NN-ten.css / NN-ten.js (NN quyết định thứ tự), không cần sửa code này.

Dòng lệnh:
  python -m webapp.appbuild            in trang đã ráp ra stdout
  python -m webapp.appbuild --js F     ghi toàn bộ JS ra file F (CI chạy node --check)
"""
import hashlib
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent / "app"
_CACHE: dict = {"sig": None, "html": "", "hash": ""}


def parts() -> tuple[list[Path], list[Path]]:
    return sorted((APP / "css").glob("*.css")), sorted((APP / "js").glob("*.js"))


def _sig() -> tuple:
    css, js = parts()
    return tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in [APP / "shell.html", *css, *js])


def build() -> str:
    """Trả về HTML đã ráp (có bộ nhớ đệm theo thời điểm sửa và kích thước file)."""
    sig = _sig()
    if _CACHE["sig"] != sig:
        css, js = parts()
        shell = (APP / "shell.html").read_text(encoding="utf-8")
        if shell.count("<!--@css-->\n") != 1 or shell.count("<!--@js-->\n") != 1:
            raise RuntimeError("shell.html phải có đúng một dòng <!--@css--> và một dòng <!--@js-->")
        html = shell.replace("<!--@css-->\n", "".join(_read(p) for p in css), 1).replace("<!--@js-->\n", "".join(_read(p) for p in js), 1)
        _CACHE.update(sig=sig, html=html, hash=hashlib.sha256(html.encode("utf-8")).hexdigest()[:12])
    return _CACHE["html"]


def version() -> str:
    build()
    return _CACHE["hash"]


def write_to(path: Path) -> Path:
    """Ghi trang đã ráp ra file nếu nội dung khác (để server phục vụ bằng _file như các trang tĩnh khác)."""
    html = build()
    path = Path(path)
    if not path.exists() or path.read_text(encoding="utf-8") != html:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(html, encoding="utf-8")
        tmp.replace(path)
    return path


def js_source() -> str:
    return "".join(_read(p) for p in parts()[1])


def _read(p: Path) -> str:
    s = p.read_text(encoding="utf-8")
    return s if s.endswith("\n") else s + "\n"


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--js":
        Path(sys.argv[2]).write_text(js_source(), encoding="utf-8")
    else:
        sys.stdout.write(build())
