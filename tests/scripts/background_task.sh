#!/usr/bin/env bash

SOURCE="${BASH_SOURCE[0]}"
DIR="$(dirname "$SOURCE")"

task() {
    while true; do
        echo "hello world"
        sleep 2
   done
}

main() {
    if [[ -f task.pid ]]; then
        kill -9 $(cat task.pid)
    fi
    task&
    local pid=$!
    echo $pid > "$DIR/task.pid"
}

main