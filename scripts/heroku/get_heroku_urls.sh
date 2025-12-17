#!/bin/bash
# Get Heroku app URLs

echo "🔍 Finding Heroku app endpoints..."
echo ""

# Method 1: Using heroku info
for app in openagents-api openagents-web openagents-realtime; do
    echo "=== $app ==="
    URL=$(heroku info --app $app 2>/dev/null | grep "Web URL" | awk '{print $3}' || echo "")
    if [ -n "$URL" ]; then
        echo "  Web URL: $URL"
    else
        # Fallback: Construct URL from app name
        echo "  Web URL: https://${app}.herokuapp.com"
    fi
    echo ""
done

# Method 2: List all apps
echo "All your Heroku apps:"
heroku apps 2>/dev/null | tail -n +2
EOF
chmod +x /tmp/get_heroku_urls.sh && /tmp/get_heroku_urls.sh