#!/bin/bash

case "$1" in
  "save")
    export DISPLAY_MODE=save
    export SAVE_DIR=frames
    ;;
  "window")
    export DISPLAY_MODE=window
    ;;
  "none")
    export DISPLAY_MODE=none
    ;;
  *)
    echo "Usage: ./run_server.sh [save|window|none]"
    exit 1
    ;;
esac

python server.py