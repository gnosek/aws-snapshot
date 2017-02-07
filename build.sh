#!/bin/bash
BASEDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ -e lambda_function.py ]] || ln aws-snapshot-cleaner lambda_function.py
zip -qr9 dist.zip lambda_function.py
ls -la dist.zip
