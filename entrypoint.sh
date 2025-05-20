#!/bin/bash

if [ "$1" = "api" ]; then
    exec uvicorn src.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000}
elif [ "$1" = "ui" ]; then
    exec chainlit run app.py --host ${CHAINLIT_HOST:-0.0.0.0} --port ${CHAINLIT_PORT:-8501}
else
    echo "Please specify either \"api\" or \"ui\" as the first argument"
    exit 1
fi 