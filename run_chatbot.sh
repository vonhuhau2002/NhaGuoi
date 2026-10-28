#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$project_dir/src"
cd "$project_dir"
exec python3 -m cotu_app.features.chatbot "$@"
