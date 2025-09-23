#!/bin/bash
cd /home/kavia/workspace/code-generation/knowledge-graph-question-answering-system-29986-29995/question_answering_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

