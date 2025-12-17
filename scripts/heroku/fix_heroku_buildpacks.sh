#!/bin/bash
##############################################################################
# Fix Heroku Buildpack Order
#
# This script fixes the buildpack order for Heroku apps that use the
# monorepo buildpack. The monorepo buildpack MUST run BEFORE the Python
# buildpack so it can copy the subdirectory to /app first.
#
# Usage:
#   ./scripts/fix_heroku_buildpacks.sh <app_name> [subdirectory]
#
# Examples:
#   ./scripts/fix_heroku_buildpacks.sh openagents-api server
#   ./scripts/fix_heroku_buildpacks.sh openagents-realtime server
#   ./scripts/fix_heroku_buildpacks.sh openagents-web frontend_web
##############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

show_usage() {
    cat << EOF
Usage: $0 <app_name> [subdirectory]

Fix buildpack order for Heroku apps using monorepo buildpack.

Arguments:
  app_name       Heroku app name (e.g., openagents-api)
  subdirectory   Subdirectory to use (default: server)

Examples:
  $0 openagents-api server
  $0 openagents-realtime server
  $0 openagents-web frontend_web

This script:
  1. Clears existing buildpacks
  2. Adds monorepo buildpack first (index 1)
  3. Adds Python/Node buildpack second (index 2)
  4. Sets APP_BASE config var

EOF
}

fix_buildpacks() {
    local app_name="$1"
    local subdirectory="${2:-server}"
    
    if [[ -z "$app_name" ]]; then
        print_error "App name is required"
        show_usage
        exit 1
    fi
    
    # Check if app exists
    if ! heroku apps:info --app "$app_name" &> /dev/null; then
        print_error "App '$app_name' not found or you don't have access"
        exit 1
    fi
    
    print_info "🔧 Fixing buildpack order for $app_name..."
    echo ""
    
    # Show current buildpacks
    print_info "Current buildpack order:"
    heroku buildpacks --app "$app_name" || true
    echo ""
    
    # Remove existing buildpacks
    print_info "Removing existing buildpacks..."
    heroku buildpacks:clear --app "$app_name"
    
    # Add monorepo buildpack FIRST (index 1)
    print_info "Adding monorepo buildpack (index 1)..."
    heroku buildpacks:add -i 1 https://github.com/lstoll/heroku-buildpack-monorepo --app "$app_name"
    
    # Determine second buildpack based on subdirectory
    if [[ "$subdirectory" == "frontend_web" ]]; then
        print_info "Adding Node.js buildpack (index 2)..."
        heroku buildpacks:add -i 2 heroku/nodejs --app "$app_name"
    else
        print_info "Adding Python buildpack (index 2)..."
        heroku buildpacks:add -i 2 heroku/python --app "$app_name"
    fi
    
    # Set APP_BASE
    print_info "Setting APP_BASE=$subdirectory..."
    heroku config:set APP_BASE="$subdirectory" --app "$app_name"
    
    echo ""
    print_success "✅ Buildpack configuration complete!"
    echo ""
    print_info "New buildpack order:"
    heroku buildpacks --app "$app_name"
    echo ""
    print_info "APP_BASE config:"
    heroku config:get APP_BASE --app "$app_name" || echo "  (not set)"
    echo ""
    print_success "You can now redeploy: git push heroku-$(echo $app_name | tr '-' '_') main"
}

# Main
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]] || [[ -z "$1" ]]; then
    show_usage
    exit 0
fi

fix_buildpacks "$@"

