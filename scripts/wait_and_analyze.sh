#!/bin/bash
# Wait for pipeline to complete, then run group statistics

echo "Waiting for pipeline to complete..."
echo "Started: $(date)"

# Wait for the pipeline process to finish
while pgrep -f "master_pipeline.py" > /dev/null; do
    sleep 30
done

echo "Pipeline completed: $(date)"
echo "Running group statistics..."

# Run group statistics
/Users/paul/miniforge3/envs/stage_analysis/bin/python scripts/compute_group_stats.py

echo "Analysis complete: $(date)"
