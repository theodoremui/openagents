#!/bin/bash

# Check if app name is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <heroku-app-name>"
    exit 1
fi

HEROKU_APP_NAME=$1

# Read .env file
ENV_FILE=".env"

if [ -f "$ENV_FILE" ]; then
  # Array to store all environment variables
  env_vars=()

  # Read the file and append a newline to ensure the last line is processed
  while IFS= read -r line || [ -n "$line" ]; do
    # Ignore comments and empty lines
    if [[ ! $line =~ ^#.*$ ]] && [ ! -z "$line" ]; then
      # Split the line into key and value
      IFS='=' read -r key value <<< "$line"
      
      # Remove any surrounding quotes from the value
      value=$(echo $value | sed -e 's/^"//' -e 's/"$//')
      
      # Store the variable in the array
      env_vars+=("$key=$value")
    fi
  done < "$ENV_FILE"

  # Process the variables, prioritizing HEROKU_ prefixed ones
  for var in "${env_vars[@]}"; do
    key="${var%%=*}"
    value="${var#*=}"
    
    if [[ $key == HEROKU_* ]]; then
      non_prefixed_key="${key#HEROKU_}"
      echo "Setting $non_prefixed_key with the value of $key"
      heroku config:set "$non_prefixed_key=$value" -a $HEROKU_APP_NAME
    else
      # Only set non-prefixed if HEROKU_ version doesn't exist
      if ! echo "${env_vars[@]}" | grep -q "HEROKU_$key="; then
        echo "Setting $key"
        heroku config:set "$key=$value" -a $HEROKU_APP_NAME
      fi
    fi
  done

  echo "Environment variables set successfully for $HEROKU_APP_NAME!"
else
  echo "$ENV_FILE not found!"
  exit 1
fi
