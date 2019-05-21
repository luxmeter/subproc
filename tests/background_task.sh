#!/usr/bin/env bash

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
    echo $pid > task.pid
}

main