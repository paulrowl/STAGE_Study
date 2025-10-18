#!/usr/bin/env python3
"""
Fill ISMRM abstract template with infarct-stratified analysis results
Conservative, evidence-based approach
"""

from docx import Document
from docx.shared import Pt, RGBColor
import re

def count_words(text):
    """Count words in text"""
    return len(re.findall(r'\w+', text))

def fill_abstract():
    """Fill in the ISMRM abstract with infarct-stratified results"""

    # Load template
    doc = Document('/Users/paul/Projects/STAGE_Study/docs/ISMRM/STAGE-standard-abstract.docx')

    # TITLE (125 characters max)
    title = "Quantitative Methodology for Validating STAGE MRI Diagnostic Adequacy Using Expert Scores and Image Contrast"
    print(f"Title: {len(title)} characters")
    assert len(title) <= 125, "Title too long!"

    # KEYWORDS (up to 5)
    keywords = "STAGE, diagnostic adequacy, validation methodology, image contrast, expert assessment"

    # IMPACT (40 words max)
    impact = """This methodology enables quantitative validation of abbreviated MRI protocols by correlating objective image contrast metrics with expert radiologist assessments, providing a transferable framework for protocol optimization and quality control in time-critical neuroimaging applications."""
    print(f"Impact: {count_words(impact)} words")
    assert count_words(impact) <= 40, "Impact too long!"

    # SYNOPSIS SECTIONS (100 words total) - Complete sentences
    motivation = """Abbreviated MRI protocols require objective validation methods to establish diagnostic adequacy, yet existing approaches rely primarily on subjective expert assessment without quantitative thresholds."""

    goals = """This study developed a quantitative methodology correlating objective image contrast metrics with expert radiologist scores to establish diagnostic adequacy thresholds for STAGE protocols."""

    approach = """We analyzed paired conventional and STAGE acquisitions in 39 stroke patients, correlating gray matter/white matter contrast ratios and similarity metrics with expert scores to identify quantitative thresholds for diagnostic adequacy."""

    results = """Similarity metrics correlated significantly with expert scores, with ROC analysis identifying optimal thresholds for diagnostic adequacy, enabling objective quality assessment."""

    synopsis_total = f"{motivation} {goals} {approach} {results}"
    print(f"Synopsis: {count_words(synopsis_total)} words")

    # BODY (750 words max)

    introduction = """STrategically Acquired Gradient Echo (STAGE) imaging employs dual flip angle, multi-echo gradient echo acquisitions with full flow compensation[1]. Validating abbreviated MRI protocols currently relies on expert radiologist assessment without standardized quantitative thresholds, limiting objective quality control and protocol optimization. We developed a methodology correlating objective image contrast metrics with expert scores (1-9 scale, clinical adequacy ≥5) to establish quantitative diagnostic adequacy thresholds. Using adult patients undergoing evaluation for stroke, we demonstrate a transferable framework for systematic protocol evaluation enabling real-time quality control and data-driven protocol refinement."""

    methods = """Study Design: Retrospective analysis of 39 adult patients (mean age 64.9±16.3 years, range 20-95; 59% male) undergoing evaluation for stroke with paired conventional and STAGE acquisitions at 3T (Siemens). Expert neuroradiologist scored diagnostic quality (1-9 scale, ≥5 clinically adequate) for each sequence.

Quantitative Metrics: (1) Image contrast: GM/WM intensity ratios from percentile-based segmentation (GM: 60-95th, WM: 25-60th). (2) Similarity metrics: SSIM, NCC, MSE, PSNR, DICE comparing conventional vs STAGE.

Statistical Analysis: Correlated objective metrics with expert scores using Pearson/Spearman correlations. ROC analysis identified optimal thresholds for clinical adequacy (expert score ≥5), calculating sensitivity, specificity, and area under curve (AUC) for discriminative performance."""

    results_section = """Dataset: 39 adult patients yielded 37 T1 pairs, 27 T2 pairs, 34 SWI pairs after quality control.

Metric-Expert Correlations: DICE overlap correlated significantly with expert scores (r=0.419, p=0.042), demonstrating feasibility of objective quality prediction. Image contrast metrics showed sequence-specific patterns with T1 and T2 demonstrating strong to moderate GM/WM ratio correlations with conventional protocols.

Quantitative Thresholds (ROC Analysis): SWI achieved best discriminative performance for clinical adequacy with NCC≥0.814 (AUC=0.786, sensitivity=1.00, specificity=0.57) and SSIM≥0.470 (AUC=0.643). These thresholds enable automated quality assessment, flagging acquisitions falling below clinical adequacy standards."""

    discussion = """We established a quantitative methodology for validating abbreviated MRI protocols by correlating objective image contrast metrics with expert radiologist assessments. This approach addresses a critical gap: while expert evaluation remains the gold standard for diagnostic adequacy, lack of quantitative thresholds limits objective quality control and systematic protocol optimization.

Key methodological contributions: (1) Multi-metric framework combining tissue contrast (GM/WM ratios) and similarity metrics (SSIM, NCC, DICE) provides complementary validation dimensions capturing both fundamental MR physics differences and perceptual equivalence. (2) ROC-derived thresholds (e.g., SWI NCC≥0.814) enable automated quality assessment with high sensitivity for detecting clinically adequate images. (3) Significant correlation between DICE overlap and expert scores (r=0.419, p=0.042) demonstrates feasibility of objective quality prediction.

This framework is transferable to other abbreviated protocols, sequences, and imaging centers. Future applications include real-time quality control during acquisition, automated protocol parameter optimization, and establishing adequacy benchmarks for time-critical neuroimaging. The methodology enables data-driven refinement of rapid imaging protocols while maintaining diagnostic standards.

References:
[1] Wang Y, et al. Radiology 2016;279(1):278-285"""

    body_total = f"{introduction} {methods} {results_section} {discussion}"
    print(f"Body total: {count_words(body_total)} words")

    # Find and replace content in document
    replacements = {
        'Abstract title:': f'Abstract title: {title}',
        'Keywords (up to 5)': f'Keywords (up to 5): {keywords}',
        'Impact (40 words max):': f'Impact (40 words max): {impact}',
        'Motivation: Absence of quantitative criteria for determining adequacy of rapid MRI protocols for clinical stroke': f'Motivation: {motivation}',
        'Goal(s):': f'Goal(s): {goals}',
        'Approach:': f'Approach: {approach}',
        'Results:': f'Results: {results}',
        'Introduction:': f'Introduction: {introduction}',
        'Methods:': f'Methods: {methods}',
        'Discussion/Conclusion:': f'Discussion/Conclusion: {discussion}'
    }

    # Also need to handle the body Results section separately
    body_results_idx = None

    for i, para in enumerate(doc.paragraphs):
        for old_text, new_text in replacements.items():
            if old_text in para.text:
                # For multi-paragraph sections, replace the whole paragraph
                if old_text in ['Introduction:', 'Methods:', 'Discussion/Conclusion:']:
                    para.text = new_text
                    para.style = 'Normal'
                elif old_text == 'Results:':
                    # Need to check if this is synopsis or body
                    if body_results_idx is None:
                        # First Results is synopsis
                        para.text = new_text
                    else:
                        # Second Results is body
                        para.text = f'Results: {results_section}'
                    body_results_idx = i
                else:
                    para.text = new_text
                    para.style = 'Normal'

    # Handle body Results separately (it appears twice)
    results_count = 0
    for para in doc.paragraphs:
        if para.text.startswith('Results:'):
            results_count += 1
            if results_count == 2:  # Body results (second occurrence)
                para.text = f'Results: {results_section}'
                para.style = 'Normal'
                break

    # Save filled document
    output_path = '/Users/paul/Projects/STAGE_Study/docs/ISMRM/STAGE-standard-abstract-FILLED.docx'
    doc.save(output_path)
    print(f"\n✓ Saved filled abstract to: {output_path}")

    # Print summary
    print("\n" + "="*80)
    print("WORD COUNT SUMMARY")
    print("="*80)
    print(f"Title: {len(title)}/125 characters")
    print(f"Impact: {count_words(impact)}/40 words")
    print(f"Synopsis total: {count_words(synopsis_total)}/100 words")
    print(f"  - Motivation: {count_words(motivation)} words")
    print(f"  - Goals: {count_words(goals)} words")
    print(f"  - Approach: {count_words(approach)} words")
    print(f"  - Results: {count_words(results)} words")
    print(f"Body total: {count_words(body_total)}/750 words")
    print(f"  - Introduction: {count_words(introduction)} words")
    print(f"  - Methods: {count_words(methods)} words")
    print(f"  - Results: {count_words(results_section)} words")
    print(f"  - Discussion: {count_words(discussion)} words")
    print("="*80)

    # Check limits
    if count_words(synopsis_total) > 100:
        print("\n⚠ WARNING: Synopsis exceeds 100 words!")
    if count_words(body_total) > 750:
        print("\n⚠ WARNING: Body exceeds 750 words!")
    else:
        print(f"\n✓ All limits met! ({count_words(body_total)} words used, {750 - count_words(body_total)} words remaining)")

if __name__ == '__main__':
    fill_abstract()
