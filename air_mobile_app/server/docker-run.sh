#!/bin/bash

case "$1" in
  "save")
    export DISPLAY_MODE=save
    ;;
  "window")
    export DISPLAY_MODE=window
    ;;
  "none")
    export DISPLAY_MODE=none
    ;;
  *)
    echo "Usage: ./docker-run.sh [save|window|none]"
    exit 1
    ;;
esac

docker compose up 