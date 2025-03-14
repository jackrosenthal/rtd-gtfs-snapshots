#!/bin/bash
set -exuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

for f in */update.sh; do
  dirname="${f%/update.sh}"
  msg="${dirname}: Downloaded new data

update.sh output follows:

$("${f}" 2>&1)"
  if [[ -n "$(git status --porcelain)" ]]; then
    git add "${dirname}"
    git commit -m "${msg}"
  fi
done
