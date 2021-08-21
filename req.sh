#!/bin/bash
poetry export -f requirements.txt -o requirements.txt --without-hashes --dev
