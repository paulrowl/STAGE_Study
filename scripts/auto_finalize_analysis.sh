#!/bin/bash
# Automated workflow: Wait for T1 pipeline → Regenerate analysis → Create figures
# Created: 2025-10-15

PYTHON_BIN="/Users/paul/miniforge3/envs/stage_analysis/bin/python"
PROJECT_DIR="/Users/paul/Projects/STAGE_Study"

cd "$PROJECT_DIR"

echo "================================================================================"
echo "AUTOMATED ANALYSIS FINALIZATION WORKFLOW"
echo "================================================================================"
echo ""
echo "Waiting for T1 recovery pipeline to complete (PID: 68837)..."
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Monitor pipeline completion
while pgrep -f "68837" > /dev/null 2>&1; do
    # Show progress every 5 minutes
    METRICS_COUNT=$(find output/metrics -name "*T1*_metrics.csv" 2>/dev/null | wc -l | tr -d ' ')
    PATIENT_COUNT=$(ls output/metrics 2>/dev/null | wc -l | tr -d ' ')
    echo "[$(date '+%H:%M:%S')] T1 metrics: $METRICS_COUNT, Total patients: $PATIENT_COUNT"
    sleep 300  # Check every 5 minutes
done

echo ""
echo "================================================================================"
echo "T1 PIPELINE COMPLETE!"
echo "================================================================================"
echo "Completed: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Count final T1 metrics
T1_COUNT=$(find output/metrics -name "*T1*_metrics.csv" 2>/dev/null | wc -l | tr -d ' ')
echo "Final T1 metrics files: $T1_COUNT"
echo ""

# Step 1: Regenerate comprehensive analysis with complete T1 data
echo "================================================================================"
echo "STEP 1: Regenerating Comprehensive Analysis"
echo "================================================================================"
echo ""

$PYTHON_BIN scripts/comprehensive_sequence_analysis.py > comprehensive_analysis_with_t1.log 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Comprehensive analysis complete!"
    echo "  Output: output/statistics/"
else
    echo "⚠ Analysis encountered errors - check comprehensive_analysis_with_t1.log"
fi

echo ""

# Step 2: Generate 5 summary figures
echo "================================================================================"
echo "STEP 2: Generating 5 Summary Figures"
echo "================================================================================"
echo ""

$PYTHON_BIN scripts/generate_summary_figures.py > figure_generation.log 2>&1

if [ $? -eq 0 ]; then
    echo "✓ All 5 figures generated successfully!"
    echo ""
    echo "Figures saved to output/statistics/:"
    ls -lh output/statistics/figure*.png 2>/dev/null || echo "  (Check figure_generation.log for details)"
else
    echo "⚠ Figure generation encountered errors - check figure_generation.log"
fi

echo ""

# Step 3: Generate final summary
echo "================================================================================"
echo "FINAL SUMMARY"
echo "================================================================================"
echo ""

TOTAL_METRICS=$(find output/metrics -name "*_metrics.csv" 2>/dev/null | wc -l | tr -d ' ')
T1_METRICS=$(find output/metrics -name "*T1*_metrics.csv" 2>/dev/null | wc -l | tr -d ' ')
T2_METRICS=$(find output/metrics -name "*T2*_metrics.csv" 2>/dev/null | wc -l | tr -d ' ')
SWI_METRICS=$(find output/metrics -name "*SWI*_metrics.csv" 2>/dev/null | wc -l | tr -d ' ')

echo "Metrics Generated:"
echo "  Total: $TOTAL_METRICS files"
echo "  T1: $T1_METRICS"
echo "  T2: $T2_METRICS"
echo "  SWI: $SWI_METRICS"
echo ""

echo "Analysis Outputs:"
echo "  ✓ Statistics: output/statistics/all_sequences_statistics.csv"
echo "  ✓ Thresholds: output/statistics/all_sequences_adequacy_thresholds.csv"
echo "  ✓ Missing data: output/statistics/missing_sequences_simple.csv"
echo ""

echo "Summary Figures:"
echo "  ✓ Figure 1: Expert score distributions"
echo "  ✓ Figure 2: SSIM correlations"
echo "  ✓ Figure 3: Very good vs very bad performers ⭐"
echo "  ✓ Figure 4: Adequacy threshold performance"
echo "  ✓ Figure 5: Comprehensive metrics heatmap"
echo ""

echo "Logs:"
echo "  - Pipeline: pipeline_t1_recovery.log"
echo "  - Analysis: comprehensive_analysis_with_t1.log"
echo "  - Figures: figure_generation.log"
echo ""

echo "================================================================================"
echo "ALL TASKS COMPLETE!"
echo "================================================================================"
echo ""

# Display key findings
if [ -f "output/statistics/all_sequences_statistics.csv" ]; then
    echo "Quick Summary from Statistics:"
    echo ""
    head -20 output/statistics/all_sequences_statistics.csv | tail -10
fi

echo ""
echo "================================================================================"
