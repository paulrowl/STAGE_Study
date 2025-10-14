#!/bin/bash
# Pipeline Progress Monitor with Ventricle Normalization

echo "======================================================"
echo "STAGE Pipeline Monitor - Ventricle Normalization Run"
echo "======================================================"
echo ""

if [ -f pipeline_run_normalized.log ]; then
    echo "Started: $(head -1 pipeline_run_normalized.log | awk '{print $1, $2}')"
else
    echo "Log file not found yet..."
fi

echo "Current time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Count progress
metrics_count=$(find output/metrics -name "*_metrics.csv" 2>/dev/null | wc -l | tr -d ' ')
patients_count=$(ls output/metrics 2>/dev/null | wc -l | tr -d ' ')

echo "Progress:"
echo "  - Metrics files created: $metrics_count"
echo "  - Patients processed: $patients_count / 10"
echo ""

# Check if pipeline is running
if pgrep -f "master_pipeline.py" > /dev/null; then
    echo "Status: RUNNING ✓"
else
    echo "Status: COMPLETED or NOT STARTED"
fi

echo ""
echo "Last 15 log lines:"
echo "------------------------------------------------------"
if [ -f pipeline_run_normalized.log ]; then
    tail -15 pipeline_run_normalized.log
else
    echo "No log file yet..."
fi
echo ""
echo "======================================================"
echo "Run: ./monitor_pipeline.sh to refresh this view"
echo "======================================================"
