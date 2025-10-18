# Ventricle Normalization: Automated Plotting Guide

**Status:** Scripts Ready - Will Auto-Generate After Pipeline Completion

## Automated Workflow

Once the pipeline completes (~20 minutes), the following will happen automatically:

1. **Statistical Comparison** - Calculates improvements in all metrics
2. **Plot Generation** - Creates 7 comprehensive visualization types
3. **Results Summary** - Displays key findings

## Plots That Will Be Generated

### 1. **SUMMARY_normalization_impact.png** (Main Figure)
**16x10 inch comprehensive summary with:**
- Overall metric improvements (bar chart)
- Sample distribution by sequence type (pie chart)
- Before/after scatter plots for T1, T2, and SWI
- Distribution box plots for SSIM, Pearson r, and NCC

**Use this for:** Quick overview, presentations, publications

---

### 2. **scatter_before_after_normalization.png**
**6 scatter plots showing:**
- Each metric (SSIM, Pearson r, NCC, PSNR, MI) before vs after normalization
- Color-coded by sequence type (T1=blue, T2=green, SWI=red)
- Diagonal line shows "no change" baseline
- Points above diagonal = improvement

**Use this for:** Detailed per-metric analysis

---

### 3. **bar_mean_improvements.png**
**Bar charts showing mean changes by sequence type:**
- SSIM improvement for T1, T2, SWI
- Pearson correlation improvement for T1, T2, SWI
- NCC improvement for T1, T2, SWI
- Green bars = improvement, Red bars = decrease
- Value labels on each bar

**Use this for:** Quick comparison across sequences

---

### 4. **heatmap_percent_improvements.png**
**Heatmap showing percentage changes:**
- Rows: T1, T2, SWI sequences
- Columns: SSIM, Pearson r, NCC, PSNR
- Color scale: Red (decrease) → Yellow (no change) → Green (improvement)
- Annotated with exact percentage values

**Use this for:** Identifying which sequences benefit most

---

### 5. **boxplot_[metric]_by_sequence.png** (5 files)
**Box plots for each metric showing:**
- Distribution with/without normalization
- Separate panels for T1, T2, and SWI
- Median, quartiles, and outliers
- Sample sizes displayed

**Metrics plotted:**
- SSIM
- Pearson correlation
- NCC
- PSNR
- Mutual Information

**Use this for:** Statistical comparisons, identifying outliers

---

### 6. **violin_distributions.png**
**Violin plots showing:**
- Full distribution shapes for 4 key metrics
- Split violins: left=without norm, right=with norm
- By sequence type (T1, T2, SWI)

**Use this for:** Understanding distribution changes

---

### 7. **patient_by_patient_pearson.png**
**Individual patient results showing:**
- Bar chart comparing each patient's Pearson correlation
- Grouped by patient ID and sequence type
- Blue bars = without normalization
- Orange bars = with normalization

**Use this for:** Identifying problematic patients, quality control

---

## How to View the Plots

### Automatic Display (Mac)
After pipeline completion, the script will automatically open the summary figure:
```bash
open output/plots/SUMMARY_normalization_impact.png
```

### Manual Viewing
```bash
# View all plots
open output/plots/*.png

# View specific plot
open output/plots/SUMMARY_normalization_impact.png
```

### Jupyter Notebook
```python
from IPython.display import Image, display
import glob

# Display all plots
for plot in glob.glob('output/plots/*.png'):
    print(f"\n{plot}")
    display(Image(filename=plot))
```

## Plot Specifications

**Format:** PNG
**Resolution:** 300 DPI (publication quality)
**Size:** Varies by plot type (optimized for readability)
**Color Scheme:** Seaborn "husl" palette (colorblind-friendly)
**Font:** System default with clear labels

## Expected Results

Based on ventricle normalization, we expect:

### Likely Improvements:
- ✓ **Pearson correlation** - Removes arbitrary intensity scaling
- ✓ **NCC** - Already normalized, but reference point helps
- ✓ **Consistency** - Reduced variance across patients

### Unchanged/Stable:
- **SSIM** - Structure-based, less affected by intensity scaling
- **Mutual Information** - Entropy-based, robust to scaling

### Sequence-Specific:
- **T2-weighted** - Likely largest improvement (ventricles brightest)
- **T1-weighted** - Moderate improvement
- **SWI** - Variable (depends on phase/magnitude differences)

## Statistical Outputs

In addition to plots, the following files will be generated:

**output/statistics/normalization_comparison_[timestamp].csv**
- Row-by-row comparison for each patient/sequence
- Before and after values for all metrics
- Calculated improvements (absolute and percentage)

**comparison_analysis.log**
- Console output with summary statistics
- Mean improvements by sequence type
- Key observations and recommendations

## Running Plots Manually

If needed, you can generate plots independently:

```bash
# After pipeline completes
python scripts/plot_normalization_comparison.py

# Or if comparison already run
python scripts/plot_normalization_comparison.py
```

## Customization

To modify plots, edit `scripts/plot_normalization_comparison.py`:

**Common modifications:**
- Color schemes: Line 13 (`sns.set_palette()`)
- Figure sizes: `figsize=(width, height)` parameters
- DPI: `dpi=300` in `savefig()` calls
- Metrics to plot: `metrics` list in each plotting function

## Current Pipeline Status

**Progress:** 70% complete (11 metrics, 6 patients)
**Estimated completion:** ~20 minutes
**Next steps:** Automatic analysis and plotting

---

**Last Updated:** October 14, 2025 11:25 AM
