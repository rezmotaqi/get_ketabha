#!/bin/bash

# Download Speed Comparison Script
# Runs speed tests on both host and container, then compares results

echo "============================================================"
echo "DOWNLOAD SPEED COMPARISON: HOST vs CONTAINER"
echo "============================================================"
echo

# Check if container is running
if ! docker ps | grep -q "telegram-libgen-bot"; then
    echo "Error: Container 'telegram-libgen-bot' is not running"
    echo "Please start the container first with: docker-compose up -d"
    exit 1
fi

# Copy speed test script to container
echo "Copying speed test script to container..."
docker cp speed_test.py telegram-libgen-bot:/app/speed_test.py

echo
echo "============================================================"
echo "RUNNING HOST SYSTEM TEST"
echo "============================================================"
echo

# Run test on host
python3 speed_test.py > host_results.txt 2>&1
echo "Host test completed. Results saved to host_results.txt"

echo
echo "============================================================"
echo "RUNNING CONTAINER TEST"
echo "============================================================"
echo

# Run test in container
docker exec telegram-libgen-bot python /app/speed_test.py > container_results.txt 2>&1
echo "Container test completed. Results saved to container_results.txt"

echo
echo "============================================================"
echo "QUICK COMPARISON"
echo "============================================================"
echo

# Extract key metrics from results
echo "HOST SYSTEM:"
echo "------------"
grep "Average speed:" host_results.txt
grep "Median speed:" host_results.txt
grep "Max speed:" host_results.txt
grep "Total download time:" host_results.txt

echo
echo "CONTAINER SYSTEM:"
echo "-----------------"
grep "Average speed:" container_results.txt
grep "Median speed:" container_results.txt
grep "Max speed:" container_results.txt
grep "Total download time:" container_results.txt

echo
echo "============================================================"
echo "DETAILED RESULTS"
echo "============================================================"
echo "Host results: host_results.txt"
echo "Container results: container_results.txt"
echo "Detailed comparison: speed_test_comparison.md"
echo "============================================================"
