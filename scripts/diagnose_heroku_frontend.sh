#!/bin/bash
# Diagnose Heroku Frontend Deployment Issues

APP_NAME="${1:-openagents-web}"

echo "🔍 Diagnosing Heroku frontend deployment for $APP_NAME"
echo ""

echo "1. Buildpack Configuration:"
heroku buildpacks --app "$APP_NAME"
echo ""

echo "2. APP_BASE Config:"
heroku config:get APP_BASE --app "$APP_NAME"
echo ""

echo "3. Recent Build Logs (last 100 lines):"
heroku logs --num 100 --app "$APP_NAME" 2>&1 | grep -E "error|Error|ERROR|fail|Fail|FAIL|compile|Compile" | tail -20
echo ""

echo "4. Full Recent Logs:"
heroku logs --num 50 --app "$APP_NAME" 2>&1 | tail -30
