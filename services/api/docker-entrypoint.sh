#!/bin/sh
set -e
# On AWS Lambda the runtime API is present: run the Lambda runtime interface client with the handler from CMD.
if [ -n "${AWS_LAMBDA_RUNTIME_API}" ]; then
  exec python -m awslambdaric "$@"
fi

case "$1" in
  worker)
    exec python -m complymate.workers.entry --serve ;;
  job)
    shift; exec python -m complymate.workers.entry --task "$@" ;;
  migrate)
    exec alembic upgrade head ;;
  complymate.lambda_handlers.*|"")
    exec uvicorn complymate.main:app --host 0.0.0.0 --port "${PORT:-8080}" --proxy-headers ;;
  *)
    exec "$@" ;;
esac
