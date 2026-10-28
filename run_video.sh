#!/bin/sh
# Dùng Python và thư viện mic đã cài riêng trong dự án.
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
video_python="$project_dir/.venv-video/bin/python"

if [ ! -x "$video_python" ]; then
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
export NHARONG_VIDEO_ENV="$project_dir"
export PYTHONPATH="$project_dir/src"

cd "$project_dir"
exec "$video_python" -m cotu_app "$@"
