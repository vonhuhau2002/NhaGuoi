#!/bin/sh
# Chạy bằng tài khoản desktop thông thường để cấu hình đúng người dùng.
set -eu

if [ "$(id -u)" -eq 0 ]; then
    printf '%s\n' 'Hãy chạy script bằng tài khoản thường, không thêm sudo trước tên script.' >&2
    printf '%s\n' 'Script sẽ tự xin quyền sudo khi cài gói hệ thống.' >&2
    exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
    printf '%s\n' 'Script này dùng cho Raspberry Pi OS/Debian có apt-get.' >&2
    exit 1
fi

printf '%s\n' 'Cài IBus UniKey để nhập tiếng Việt. Nhập mật khẩu tài khoản Pi nếu được hỏi.'
sudo -v
sudo apt-get update
sudo apt-get install -y ibus ibus-unikey ibus-gtk3 im-config
im-config -n ibus

printf '\n%s\n' 'Đã cài gói và chọn IBus làm bộ gõ cho tài khoản hiện tại.'
printf '%s\n' '1. Lưu công việc, đăng xuất desktop rồi đăng nhập lại.'
printf '%s\n' '2. Mở Terminal, chạy: ibus-setup'
printf '%s\n' '3. Chọn Input Method → Add → Vietnamese → Unikey → Add.'
printf '%s\n' '   Nếu không thấy Vietnamese, chọn dấu ba chấm/Show all input methods.'
printf '%s\n' '4. Chọn Unikey ở biểu tượng bộ gõ trên thanh hệ thống; dùng kiểu Telex.'
printf '%s\n' '5. Mở lại ứng dụng video rồi thử gõ: tieengs Vieetj → tiếng Việt.'
