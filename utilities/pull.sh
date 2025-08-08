#!/bin/bash

REPO_DIR="/home/drux/demandResponse_UX_research"

# Check if destination already exists
if [ -d "$REPO_DIR" ]; then
    echo "Directory '$REPO_DIR' already exists. Pulling most recent version."

	cd /home/drux/demandResponse_UX_research
	git stash
    git pull origin main

else
    echo "Repository doesn't exist."
fi