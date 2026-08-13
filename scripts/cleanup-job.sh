#!/usr/bin/env sh
set -eu

JOB_DIR="${1:-}"

if [ -z "$JOB_DIR" ] || [ "$JOB_DIR" = "/" ]; then
  echo "usage: cleanup-job.sh /var/lib/subextractor/jobs/<job-id>" >&2
  exit 2
fi

case "$JOB_DIR" in
  /var/lib/subextractor/jobs/*) ;;
  *)
    echo "refusing to clean path outside /var/lib/subextractor/jobs" >&2
    exit 2
    ;;
esac

find "$JOB_DIR" -type f \( -name '*.part' -o -name 'cancel' \) -delete
find "$JOB_DIR" -type d -empty -delete
