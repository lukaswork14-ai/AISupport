#!/usr/bin/env bash
# Kiểm tra bảo mật trên VPS. CHỈ in kết quả đạt/không đạt, không in bí mật hay nội dung riêng tư.
S=/opt/superhuy/shared
ok(){ echo "PASS $1"; }
bad(){ echo "FAIL $1"; }
info(){ echo "INFO $1"; }
cfg=$(cat /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null | grep -v '^\s*#' | tr 'A-Z' 'a-z')
pa=$(echo "$cfg" | awk '$1=="passwordauthentication"{print $2; exit}'); pr=$(echo "$cfg" | awk '$1=="permitrootlogin"{print $2; exit}')
kb=$(echo "$cfg" | awk '$1=="kbdinteractiveauthentication"||$1=="challengeresponseauthentication"{print $2; exit}')
[ "$pa" = "no" ] && ok "ssh: tắt đăng nhập bằng mật khẩu" || bad "ssh: đăng nhập bằng mật khẩu đang BẬT (PasswordAuthentication=${pa:-mặc định yes})"
case "$pr" in no|prohibit-password|without-password) ok "ssh: root không đăng nhập được bằng mật khẩu ($pr)";; *) bad "ssh: root đăng nhập được bằng mật khẩu (PermitRootLogin=${pr:-mặc định})";; esac
info "ssh kbd-interactive: ${kb:-mặc định}"
info "sudo của user deploy: $(sudo -n -l 2>/dev/null | grep -E 'NOPASSWD|ALL' | tr -s ' ' | tr '\n' '|' | cut -c1-200)"
command -v ufw >/dev/null && info "ufw: $(sudo -n ufw status 2>/dev/null | head -1 || echo 'không đọc được')" || info "ufw: chưa cài"
command -v fail2ban-client >/dev/null && ok "fail2ban có cài" || bad "fail2ban chưa cài (chặn dò mật khẩu SSH)"
info "cổng đang mở ra ngoài: $(ss -tlnH 2>/dev/null | awk '{print $4}' | grep -v -E '^(127\.|\[::1\]|::1)' | sort -u | tr '\n' ' ')"
ss -tlnH | awk '{print $4}' | grep -q -E '(^|:)8787$' && { ss -tlnH | awk '{print $4}' | grep -E ':8787$' | grep -q -E '^(127\.0\.0\.1|\[::1\])' && ok "app chỉ nghe nội bộ 127.0.0.1:8787" || bad "app 8787 mở ra Internet (vượt qua HTTPS)"; }
for f in "$S/.env" "$S/notebooklm/storage_state.json" "$S/data/security.json"; do
  [ -e "$f" ] || continue; m=$(stat -c %a "$f"); [ "${m: -1}" = "0" ] && [ "${m: -2:1}" = "0" ] && ok "quyền file $(basename $f): $m" || bad "quyền file $(basename $f) quá rộng: $m (nên 600)"
done
m=$(stat -c %a "$S" 2>/dev/null); [ "${m: -1}" = "0" ] && ok "thư mục dữ liệu không cho người khác đọc ($m)" || bad "thư mục dữ liệu cho người khác đọc ($m, nên 750/700)"
[ -d "$S/vault/.git" ] && info "vault remote: $(git -C $S/vault remote get-url origin 2>/dev/null | sed 's#//[^@]*@#//***@#')"
grep -q '^TELEGRAM_TOKEN=' $S/.env 2>/dev/null && ok ".env có khoá (không in giá trị)"
info "đăng nhập SSH thất bại 24h: $(sudo -n journalctl -u ssh -u sshd --since -24h 2>/dev/null | grep -c -E 'Failed password|Invalid user' || echo '?')"
info "cập nhật bảo mật tự động: $(dpkg -l unattended-upgrades 2>/dev/null | grep -q '^ii' && echo có || echo không)"
info "hệ điều hành: $(. /etc/os-release; echo $PRETTY_NAME), kernel $(uname -r)"
