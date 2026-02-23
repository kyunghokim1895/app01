#!/bin/bash

# Configuration
APPS=("SentvSummaryApp" "JipconomyApp" "HKKoreaApp" "MKSummaryApp" "HKGlobalApp")
ROOT_DIR=$(pwd)

echo "Starting Build Process for ${#APPS[@]} Apps..."

for APP in "${APPS[@]}"; do
    echo "========================================"
    echo "Building APK for: $APP"
    echo "========================================"
    
    cd "$ROOT_DIR/$APP" || { echo "Directory $APP not found. Skipping..."; continue; }
    
    # 1. Install dependencies if needed
    # npm install
    
    # 2. Build Release APK using Gradle
    cd android || { echo "Android folder not found in $APP. Skipping..."; continue; }
    ./gradlew assembleRelease
    
    if [ $? -eq 0 ]; then
        echo "Successfully built $APP-release.apk"
        # Optional: Copy APK to a central location
        mkdir -p "$ROOT_DIR/builds"
        cp app/build/outputs/apk/release/app-release.apk "$ROOT_DIR/builds/$APP-release.apk"
    else
        echo "FAILED to build $APP"
    fi
    
    cd "$ROOT_DIR"
done

echo "========================================"
echo "All Builds Completed!"
echo "Check the 'builds' folder for APKs."
