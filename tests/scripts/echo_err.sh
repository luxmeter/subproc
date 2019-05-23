#! /bin/bash

SOURCE="${BASH_SOURCE[0]}"
DIR="$(dirname "$SOURCE")"
cat "$DIR/content_pipe_sized.txt" >&2