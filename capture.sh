#!/bin/bash
name="$1"; shift
out="media/terminal/$name.log"
{ echo "sreemanti@MacBook-Pro concurrent-web-fetcher % $*"; "$@" 2>&1; } | tee "$out"
