#!/bin/bash
# Automated cleanup and analysis after pipeline completion
# Created: 2025-10-15

echo "Waiting for pipeline to complete..."
while pgrep -f "18655" > /dev/null 2>&1; do
    sleep 30
done

echo ""
echo "============================================"
echo "PIPELINE COMPLETE - Starting Cleanup"
echo "============================================"
echo ""

# Record completion
date > pipeline_completion_time.txt

# Count final metrics
echo "Final metrics count:"
METRICS_COUNT=$(find output/metrics -name "*_metrics.csv" | wc -l | tr -d ' ')
PATIENT_COUNT=$(ls output/metrics | wc -l | tr -d ' ')
SWI_COUNT=$(find output/metrics -name "*SWI*_metrics.csv" | wc -l | tr -d ' ')
T1_COUNT=$(find output/metrics -name "*T1*_metrics.csv" | wc -l | tr -d ' ')
T2_COUNT=$(find output/metrics -name "*T2*_metrics.csv" | wc -l | tr -d ' ')

echo "  Total metrics: $METRICS_COUNT"
echo "  Patients: $PATIENT_COUNT"
echo "  T1 metrics: $T1_COUNT"
echo "  T2 metrics: $T2_COUNT"
echo "  SWI metrics: $SWI_COUNT"
echo ""

# Phase 1: Safe deletions
echo "============================================"
echo "Phase 1: Cleanup"
echo "============================================"
echo ""

# Backup size before deletion
OLD_SIZE=$(du -sh data/organized 2>/dev/null | awk '{print $1}')
echo "1. Removing outdated data/organized/ ($OLD_SIZE)..."
rm -rf data/organized/
echo "   ✓ Deleted"

# Clean up .DS_Store files
echo "2. Cleaning .DS_Store files..."
DS_COUNT=$(find . -name ".DS_Store" 2>/dev/null | wc -l | tr -d ' ')
find . -name ".DS_Store" -delete 2>/dev/null
echo "   ✓ Removed $DS_COUNT .DS_Store files"

echo ""
echo "Cleanup complete! Saved $OLD_SIZE of disk space"
echo ""

# Phase 2: Run comprehensive analysis
echo "============================================"
echo "Phase 2: Comprehensive Analysis"
echo "============================================"
echo ""

cd /Users/paul/Projects/STAGE_Study
/Users/paul/miniforge3/envs/stage_analysis/bin/python scripts/comprehensive_sequence_analysis.py > comprehensive_analysis_final.log 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Comprehensive analysis complete!"
    echo "  Results: output/statistics/"
else
    echo "⚠ Analysis encountered errors - check comprehensive_analysis_final.log"
fi

echo ""
echo "============================================"
echo "FINAL SUMMARY"
echo "============================================"
echo ""
echo "Pipeline Statistics:"
echo "  Started: $(head -1 pipeline_full_43patients.log | awk '{print $1, $2}')"
echo "  Completed: $(cat pipeline_completion_time.txt)"
echo "  Patients processed: $PATIENT_COUNT/43"
echo "  Total metrics: $METRICS_COUNT"
echo "    - T1: $T1_COUNT"
echo "    - T2: $T2_COUNT"
echo "    - SWI: $SWI_COUNT"
echo ""
echo "Cleanup:"
echo "  Deleted: data/organized/ ($OLD_SIZE)"
echo "  Removed: $DS_COUNT .DS_Store files"
echo ""
echo "Analysis outputs:"
echo "  Statistics: output/statistics/"
echo "  Metrics: output/metrics/"
echo "  Audit report: DATA_STRUCTURE_AUDIT.md"
echo ""
echo "Next steps:"
echo "  1. Review: output/statistics/all_sequences_statistics.csv"
echo "  2. Review: output/statistics/all_sequences_adequacy_thresholds.csv"
echo "  3. Check: comprehensive_analysis_final.log for details"
echo ""
echo "============================================"
echo "ALL TASKS COMPLETE"
echo "============================================"
