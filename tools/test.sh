#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export PYTHONPATH="$project_dir/src:$project_dir"
cd "$project_dir"
exec "$project_dir/.venv-video/bin/python" -B -m unittest discover -s tests "$@"
