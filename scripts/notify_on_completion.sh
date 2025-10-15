#!/bin/bash
# Monitor pipeline and send notification when complete

PIPELINE_LOG="pipeline_run_recovered.log"
TARGET_COUNT=43

echo "Monitoring pipeline progress..."
echo "Will notify when all $TARGET_COUNT patients are processed"

while true; do
    # Count processed patients
    CURRENT_COUNT=$(ls -1 output/metrics/ 2>/dev/null | wc -l | tr -d ' ')

    # Check if pipeline is still running
    if ! pgrep -f "master_pipeline.py.*pipeline_run_recovered" > /dev/null; then
        # Pipeline process ended
        echo "Pipeline process completed at $(date)"

        # Check final count
        FINAL_COUNT=$(ls -1 output/metrics/ 2>/dev/null | wc -l | tr -d ' ')

        # Send notification
        osascript -e "display notification \"Processed $FINAL_COUNT/$TARGET_COUNT patients successfully!\" with title \"STAGE Analysis Complete\" sound name \"Glass\""

        echo "Notification sent! Final count: $FINAL_COUNT patients"
        break
    fi

    # Still running - check periodically
    sleep 30
done
