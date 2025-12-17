#!/bin/bash
# scripts/deploy_heroku.sh - Deploy OpenAgents to Heroku Enterprise

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 OpenAgents Heroku Deployment${NC}"
echo "=================================="

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo -e "${YELLOW}⚠️  Warning: You have uncommitted changes${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Deploy Backend API
deploy_api() {
    echo -e "\n${GREEN}📦 Deploying Backend API...${NC}"
    
    # Ensure correct Procfile
    cp Procfile.api Procfile 2>/dev/null || cat > Procfile << 'EOF'
web: uvicorn server.main:app --host 0.0.0.0 --port $PORT
EOF
    
    git add Procfile
    git commit -m "Deploy: Configure API Procfile" --allow-empty
    
    git push heroku-api main
    
    echo -e "${GREEN}✅ Backend API deployed${NC}"
    heroku open --app openagents-api
}

# Deploy Realtime Worker
deploy_realtime() {
    echo -e "\n${GREEN}📦 Deploying Realtime Worker...${NC}"
    
    # Use worker Procfile
    cat > Procfile << 'EOF'
worker: python -m server.voice.realtime.worker
EOF
    
    git add Procfile
    git commit -m "Deploy: Configure Realtime Worker Procfile" --allow-empty
    
    git push heroku-realtime main
    
    # Scale worker dyno (no web process - only worker defined in Procfile)
    heroku ps:scale worker=1 --app openagents-realtime
    
    echo -e "${GREEN}✅ Realtime Worker deployed${NC}"
}

# Deploy Frontend
deploy_frontend() {
    echo -e "\n${GREEN}📦 Deploying Frontend...${NC}"
    
    # Using monorepo buildpack
    git push heroku-web main
    
    echo -e "${GREEN}✅ Frontend deployed${NC}"
    heroku open --app openagents-web
}

# Parse arguments
case "${1:-all}" in
    api)
        deploy_api
        ;;
    realtime)
        deploy_realtime
        ;;
    frontend|web)
        deploy_frontend
        ;;
    all)
        deploy_api
        deploy_realtime
        deploy_frontend
        ;;
    *)
        echo "Usage: $0 {api|realtime|frontend|all}"
        exit 1
        ;;
esac

echo -e "\n${GREEN}🎉 Deployment complete!${NC}"
echo "=================================="
echo "Frontend: https://openagents-web.herokuapp.com"
echo "API:      https://openagents-api.herokuapp.com"
echo "API Docs: https://openagents-api.herokuapp.com/docs"
