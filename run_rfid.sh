#!/bin/sh
# Chạy bản kể chuyện RFID với ZeroTTS và thư viện âm thanh của dự án.
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
rfid_python="$project_dir/.venv-video/bin/python"

if [ ! -x "$rfid_python" ]; then
    printf '%s\n' 'Chưa có .venv-video. Xem docs/HUONG_DAN_VIDEO.md để cài đặt.' >&2
    exit 1
fi

for library_dir in "$project_dir"/.venv-video/native/usr/lib/*; do
    if [ -d "$library_dir" ]; then
        export LD_LIBRARY_PATH="$library_dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    fi
done
export HF_HOME="$project_dir/.venv-video/models"
export XDG_CACHE_HOME="$project_dir/.venv-video/cache"
export PYTHONPATH="$project_dir/src"

cd "$project_dir"
exec "$rfid_python" -m cotu_app.app.story_reader "$@"
