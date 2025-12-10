#!/usr/bin/env python3
"""
Plotter script for k-Subgraph Isomorphism experiments.
Generates visualizations from CSV experiment results.
"""

import argparse
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# ANSI color codes for logging
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log_info(msg: str):
    print(f"{Colors.CYAN}[INFO]{Colors.ENDC} {msg}")

def log_success(msg: str):
    print(f"{Colors.GREEN}[OK]{Colors.ENDC} {msg}")

def log_warning(msg: str):
    print(f"{Colors.YELLOW}[WARN]{Colors.ENDC} {msg}")

def log_error(msg: str):
    print(f"{Colors.RED}[ERROR]{Colors.ENDC} {msg}")

def log_header(msg: str):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{msg.center(60)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}\n")


def load_results(csv_path: str) -> List[dict]:
    """Load results from CSV file."""
    results = []
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            row['nG'] = int(row['nG'])
            row['nH'] = int(row['nH'])
            row['k'] = int(row['k'])
            row['seed'] = int(row['seed'])
            row['time_seconds'] = float(row['time_seconds'])
            row['extension_cost'] = int(row['extension_cost'])
            results.append(row)
    return results


def setup_plot_style():
    """Configure matplotlib style for publication-quality plots."""
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams.update({
        'font.size': 11,
        'axes.labelsize': 12,
        'axes.titlesize': 14,
        'legend.fontsize': 10,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'figure.figsize': (10, 6),
        'figure.dpi': 150,
        'savefig.dpi': 150,
        'savefig.bbox': 'tight',
    })


def plot_accuracy_comparison(results: List[dict], output_dir: str):
    """
    Plot 1: Compare extension costs between exact and approx algorithms.
    Shows scatter plot where each point is a test case with both results.
    """
    log_info("Generating accuracy comparison plot...")
    
    # Group by input file to match exact and approx results
    by_input = defaultdict(dict)
    for r in results:
        if r['status'] == 'success' and r['extension_cost'] >= 0:
            by_input[r['input_file']][r['algorithm']] = r
    
    # Collect paired results
    exact_costs = []
    approx_costs = []
    labels = []
    
    for input_file, algos in by_input.items():
        if 'exact' in algos and 'approx' in algos:
            exact_costs.append(algos['exact']['extension_cost'])
            approx_costs.append(algos['approx']['extension_cost'])
            labels.append(f"G={algos['exact']['nG']}, k={algos['exact']['k']}")
    
    if not exact_costs:
        log_warning("No paired results found for accuracy comparison")
        return
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Create scatter plot
    scatter = ax.scatter(exact_costs, approx_costs, alpha=0.6, s=50, c='steelblue', edgecolors='navy')
    
    # Add diagonal line (perfect accuracy)
    max_val = max(max(exact_costs), max(approx_costs)) * 1.1
    ax.plot([0, max_val], [0, max_val], 'r--', linewidth=2, label='Perfect accuracy (y=x)')
    
    ax.set_xlabel('Exact Algorithm Extension Cost')
    ax.set_ylabel('Approx Algorithm Extension Cost')
    ax.set_title('Accuracy Comparison: Exact vs Approx Algorithm')
    ax.legend()
    ax.set_xlim(0, max_val)
    ax.set_ylim(0, max_val)
    ax.set_aspect('equal')
    
    # Add text annotation
    n_points = len(exact_costs)
    above_line = sum(1 for e, a in zip(exact_costs, approx_costs) if a > e)
    on_line = sum(1 for e, a in zip(exact_costs, approx_costs) if a == e)
    
    text = f"Total: {n_points} test cases\n"
    text += f"Approx optimal: {on_line} ({100*on_line/n_points:.1f}%)\n"
    text += f"Approx suboptimal: {above_line} ({100*above_line/n_points:.1f}%)"
    ax.text(0.05, 0.95, text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    output_path = os.path.join(output_dir, 'accuracy_comparison.png')
    plt.savefig(output_path)
    plt.close()
    log_success(f"Saved: {output_path}")


def plot_time_comparison(results: List[dict], output_dir: str):
    """
    Plot 2: Compare execution times between exact and approx algorithms.
    Log-scale bar chart grouped by G size.
    """
    log_info("Generating time comparison plot...")
    
    # Group times by (nG, algorithm)
    times_by_g = defaultdict(lambda: defaultdict(list))
    
    for r in results:
        if r['status'] == 'success':
            times_by_g[r['nG']][r['algorithm']].append(r['time_seconds'])
    
    # Calculate means for each group
    g_sizes = sorted(times_by_g.keys())
    exact_means = []
    approx_means = []
    exact_stds = []
    approx_stds = []
    
    for g in g_sizes:
        exact_times = times_by_g[g].get('exact', [])
        approx_times = times_by_g[g].get('approx', [])
        
        exact_means.append(np.mean(exact_times) if exact_times else 0)
        approx_means.append(np.mean(approx_times) if approx_times else 0)
        exact_stds.append(np.std(exact_times) if exact_times else 0)
        approx_stds.append(np.std(approx_times) if approx_times else 0)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(g_sizes))
    width = 0.35
    
    # Create bars
    bars1 = ax.bar(x - width/2, exact_means, width, label='Exact', color='coral', 
                   yerr=exact_stds, capsize=3, alpha=0.8)
    bars2 = ax.bar(x + width/2, approx_means, width, label='Approx', color='steelblue',
                   yerr=approx_stds, capsize=3, alpha=0.8)
    
    ax.set_xlabel('Graph G Size (vertices)')
    ax.set_ylabel('Execution Time (seconds) - Log Scale')
    ax.set_title('Execution Time Comparison: Exact vs Approx Algorithm')
    ax.set_xticks(x)
    ax.set_xticklabels(g_sizes)
    ax.legend()
    ax.set_yscale('log')
    ax.yaxis.set_major_formatter(ticker.ScalarFormatter())
    
    # Add value labels on bars
    def autolabel(bars):
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'{height:.3f}s',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom', fontsize=8, rotation=45)
    
    # Only label if not too many bars
    if len(g_sizes) <= 8:
        autolabel(bars1)
        autolabel(bars2)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'time_comparison.png')
    plt.savefig(output_path)
    plt.close()
    log_success(f"Saved: {output_path}")


def plot_approximation_ratio(results: List[dict], output_dir: str):
    """
    Plot 3: Show approximation ratio (approx_cost / exact_cost) distribution.
    """
    log_info("Generating approximation ratio plot...")
    
    # Group by input file to match exact and approx results
    by_input = defaultdict(dict)
    for r in results:
        if r['status'] == 'success' and r['extension_cost'] >= 0:
            by_input[r['input_file']][r['algorithm']] = r
    
    # Calculate ratios
    ratios = []
    params = []
    
    for input_file, algos in by_input.items():
        if 'exact' in algos and 'approx' in algos:
            exact_cost = algos['exact']['extension_cost']
            approx_cost = algos['approx']['extension_cost']
            
            if exact_cost > 0:
                ratio = approx_cost / exact_cost
            elif approx_cost == 0:
                ratio = 1.0  # Both optimal
            else:
                ratio = float('inf')  # Exact is 0 but approx is not
            
            if ratio != float('inf'):
                ratios.append(ratio)
                params.append({
                    'nG': algos['exact']['nG'],
                    'k': algos['exact']['k'],
                    'density': algos['exact']['density']
                })
    
    if not ratios:
        log_warning("No paired results found for approximation ratio plot")
        return
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Left: Histogram of ratios
    ax1 = axes[0]
    n, bins, patches = ax1.hist(ratios, bins=30, color='steelblue', edgecolor='navy', alpha=0.7)
    ax1.axvline(x=1.0, color='red', linestyle='--', linewidth=2, label='Optimal (ratio=1)')
    ax1.axvline(x=np.mean(ratios), color='orange', linestyle='-', linewidth=2, 
                label=f'Mean ({np.mean(ratios):.2f})')
    ax1.set_xlabel('Approximation Ratio (approx_cost / exact_cost)')
    ax1.set_ylabel('Frequency')
    ax1.set_title('Distribution of Approximation Ratios')
    ax1.legend()
    
    # Right: Ratio vs k value
    ax2 = axes[1]
    k_values = [p['k'] for p in params]
    ax2.scatter(k_values, ratios, alpha=0.5, c='steelblue', edgecolors='navy', s=40)
    
    # Add trend line
    z = np.polyfit(k_values, ratios, 1)
    p = np.poly1d(z)
    k_range = np.linspace(min(k_values), max(k_values), 100)
    ax2.plot(k_range, p(k_range), 'r--', linewidth=2, label=f'Trend line')
    ax2.axhline(y=1.0, color='green', linestyle=':', linewidth=2, label='Optimal')
    
    ax2.set_xlabel('k value')
    ax2.set_ylabel('Approximation Ratio')
    ax2.set_title('Approximation Ratio vs k')
    ax2.legend()
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'approximation_ratio.png')
    plt.savefig(output_path)
    plt.close()
    log_success(f"Saved: {output_path}")
    
    # Print statistics
    log_info(f"Approximation ratio statistics:")
    log_info(f"  Mean: {np.mean(ratios):.3f}")
    log_info(f"  Median: {np.median(ratios):.3f}")
    log_info(f"  Std: {np.std(ratios):.3f}")
    log_info(f"  Min: {min(ratios):.3f}")
    log_info(f"  Max: {max(ratios):.3f}")
    optimal_count = sum(1 for r in ratios if r == 1.0)
    log_info(f"  Optimal solutions: {optimal_count}/{len(ratios)} ({100*optimal_count/len(ratios):.1f}%)")


def plot_time_comparison_successful(results: List[dict], output_dir: str):
    """
    Plot: Line graph comparing execution times of exact vs approx,
    only for cases where exact did NOT time out.
    """
    log_info("Generating time comparison (successful exact only) plot...")
    
    # Group by input file to match exact and approx results
    by_input = defaultdict(dict)
    for r in results:
        by_input[r['input_file']][r['algorithm']] = r
    
    # Collect paired results where exact succeeded (no timeout)
    times_by_g = defaultdict(lambda: {'exact': [], 'approx': []})
    
    for input_file, algos in by_input.items():
        if 'exact' in algos and 'approx' in algos:
            exact_r = algos['exact']
            approx_r = algos['approx']
            
            # Only include if exact succeeded (not timeout)
            if exact_r['status'] == 'success' and approx_r['status'] == 'success':
                n_G = exact_r['nG']
                times_by_g[n_G]['exact'].append(exact_r['time_seconds'])
                times_by_g[n_G]['approx'].append(approx_r['time_seconds'])
    
    if not times_by_g:
        log_warning("No paired successful results found for time comparison")
        return
    
    g_sizes = sorted(times_by_g.keys())
    exact_means = [np.mean(times_by_g[g]['exact']) for g in g_sizes]
    approx_means = [np.mean(times_by_g[g]['approx']) for g in g_sizes]
    exact_stds = [np.std(times_by_g[g]['exact']) for g in g_sizes]
    approx_stds = [np.std(times_by_g[g]['approx']) for g in g_sizes]
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Left: Linear scale line plot
    ax1 = axes[0]
    ax1.errorbar(g_sizes, exact_means, yerr=exact_stds, marker='o', capsize=5,
                 color='coral', linewidth=2, markersize=8, label='Exact')
    ax1.errorbar(g_sizes, approx_means, yerr=approx_stds, marker='s', capsize=5,
                 color='steelblue', linewidth=2, markersize=8, label='Approx')
    
    ax1.fill_between(g_sizes, 
                     [m - s for m, s in zip(exact_means, exact_stds)],
                     [m + s for m, s in zip(exact_means, exact_stds)],
                     alpha=0.15, color='coral')
    ax1.fill_between(g_sizes, 
                     [m - s for m, s in zip(approx_means, approx_stds)],
                     [m + s for m, s in zip(approx_means, approx_stds)],
                     alpha=0.15, color='steelblue')
    
    ax1.set_xlabel('Graph G Size (vertices)')
    ax1.set_ylabel('Execution Time (seconds)')
    ax1.set_title('Execution Time: Exact vs Approx (Successful Exact Only)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(g_sizes)
    
    # Right: Log scale for better visibility of differences
    ax2 = axes[1]
    ax2.semilogy(g_sizes, exact_means, marker='o', color='coral', 
                 linewidth=2, markersize=8, label='Exact')
    ax2.semilogy(g_sizes, approx_means, marker='s', color='steelblue',
                 linewidth=2, markersize=8, label='Approx')
    
    ax2.set_xlabel('Graph G Size (vertices)')
    ax2.set_ylabel('Execution Time (seconds) - Log Scale')
    ax2.set_title('Execution Time (Log Scale)')
    ax2.legend()
    ax2.grid(True, alpha=0.3, which='both')
    ax2.set_xticks(g_sizes)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'time_comparison_successful.png')
    plt.savefig(output_path)
    plt.close()
    log_success(f"Saved: {output_path}")
    
    # Print speedup statistics
    log_info("Speedup statistics (exact_time / approx_time):")
    for g in g_sizes:
        exact_mean = np.mean(times_by_g[g]['exact'])
        approx_mean = np.mean(times_by_g[g]['approx'])
        if approx_mean > 0:
            speedup = exact_mean / approx_mean
            log_info(f"  G={g}: exact={exact_mean:.4f}s, approx={approx_mean:.4f}s, speedup={speedup:.2f}x")


def plot_time_comparison_by_h(results: List[dict], output_dir: str):
    """
    Plot: Line graph comparing execution times of exact vs approx by H size,
    only for cases where exact did NOT time out.
    """
    log_info("Generating time comparison by H size plot...")
    
    # Group by input file to match exact and approx results
    by_input = defaultdict(dict)
    for r in results:
        by_input[r['input_file']][r['algorithm']] = r
    
    # Collect paired results where exact succeeded (no timeout)
    times_by_h = defaultdict(lambda: {'exact': [], 'approx': []})
    
    for input_file, algos in by_input.items():
        if 'exact' in algos and 'approx' in algos:
            exact_r = algos['exact']
            approx_r = algos['approx']
            
            # Only include if exact succeeded (not timeout)
            if exact_r['status'] == 'success' and approx_r['status'] == 'success':
                n_H = exact_r['nH']
                times_by_h[n_H]['exact'].append(exact_r['time_seconds'])
                times_by_h[n_H]['approx'].append(approx_r['time_seconds'])
    
    if not times_by_h:
        log_warning("No paired successful results found for time comparison by H")
        return
    
    h_sizes = sorted(times_by_h.keys())
    exact_means = [np.mean(times_by_h[h]['exact']) for h in h_sizes]
    approx_means = [np.mean(times_by_h[h]['approx']) for h in h_sizes]
    exact_stds = [np.std(times_by_h[h]['exact']) for h in h_sizes]
    approx_stds = [np.std(times_by_h[h]['approx']) for h in h_sizes]
    
    # Count samples per H
    sample_counts = [len(times_by_h[h]['exact']) for h in h_sizes]
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Left: Linear scale line plot
    ax1 = axes[0]
    ax1.errorbar(h_sizes, exact_means, yerr=exact_stds, marker='o', capsize=5,
                 color='coral', linewidth=2, markersize=8, label='Exact')
    ax1.errorbar(h_sizes, approx_means, yerr=approx_stds, marker='s', capsize=5,
                 color='steelblue', linewidth=2, markersize=8, label='Approx')
    
    ax1.fill_between(h_sizes, 
                     [m - s for m, s in zip(exact_means, exact_stds)],
                     [m + s for m, s in zip(exact_means, exact_stds)],
                     alpha=0.15, color='coral')
    ax1.fill_between(h_sizes, 
                     [m - s for m, s in zip(approx_means, approx_stds)],
                     [m + s for m, s in zip(approx_means, approx_stds)],
                     alpha=0.15, color='steelblue')
    
    ax1.set_xlabel('Graph H Size (vertices)')
    ax1.set_ylabel('Execution Time (seconds)')
    ax1.set_title('Execution Time by H Size (Successful Exact Only)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(h_sizes)
    
    # Add sample count annotations
    for i, (h, count) in enumerate(zip(h_sizes, sample_counts)):
        ax1.annotate(f'n={count}', (h, exact_means[i]), textcoords="offset points",
                     xytext=(0, 10), ha='center', fontsize=8, color='gray')
    
    # Right: Log scale for better visibility of differences
    ax2 = axes[1]
    ax2.semilogy(h_sizes, exact_means, marker='o', color='coral', 
                 linewidth=2, markersize=8, label='Exact')
    ax2.semilogy(h_sizes, approx_means, marker='s', color='steelblue',
                 linewidth=2, markersize=8, label='Approx')
    
    ax2.set_xlabel('Graph H Size (vertices)')
    ax2.set_ylabel('Execution Time (seconds) - Log Scale')
    ax2.set_title('Execution Time by H Size (Log Scale)')
    ax2.legend()
    ax2.grid(True, alpha=0.3, which='both')
    ax2.set_xticks(h_sizes)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'time_comparison_by_h.png')
    plt.savefig(output_path)
    plt.close()
    log_success(f"Saved: {output_path}")
    
    # Print statistics
    log_info("Time comparison by H size:")
    for h in h_sizes:
        exact_mean = np.mean(times_by_h[h]['exact'])
        approx_mean = np.mean(times_by_h[h]['approx'])
        count = len(times_by_h[h]['exact'])
        if approx_mean > 0:
            speedup = exact_mean / approx_mean
            log_info(f"  H={h}: exact={exact_mean:.4f}s, approx={approx_mean:.4f}s, speedup={speedup:.1f}x (n={count})")


def plot_scaling_analysis(results: List[dict], output_dir: str):
    """
    Plot 4: Show how execution time scales with graph size for approx algorithm.
    Useful for understanding polynomial complexity behavior.
    """
    log_info("Generating scaling analysis plot...")
    
    # Group approx times by nG
    times_by_g = defaultdict(list)
    for r in results:
        if r['algorithm'] == 'approx' and r['status'] == 'success':
            times_by_g[r['nG']].append(r['time_seconds'])
    
    if not times_by_g:
        log_warning("No approx results found for scaling analysis")
        return
    
    g_sizes = sorted(times_by_g.keys())
    means = [np.mean(times_by_g[g]) for g in g_sizes]
    stds = [np.std(times_by_g[g]) for g in g_sizes]
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Left: Linear scale
    ax1 = axes[0]
    ax1.errorbar(g_sizes, means, yerr=stds, marker='o', capsize=5, 
                 color='steelblue', linewidth=2, markersize=8)
    ax1.fill_between(g_sizes, 
                     [m - s for m, s in zip(means, stds)],
                     [m + s for m, s in zip(means, stds)],
                     alpha=0.2, color='steelblue')
    ax1.set_xlabel('Graph G Size (vertices)')
    ax1.set_ylabel('Execution Time (seconds)')
    ax1.set_title('Approx Algorithm: Time vs Graph Size (Linear)')
    ax1.grid(True, alpha=0.3)
    
    # Right: Log-log scale to identify polynomial degree
    ax2 = axes[1]
    ax2.loglog(g_sizes, means, marker='o', color='steelblue', linewidth=2, markersize=8, label='Measured')
    
    # Fit polynomial in log space
    log_g = np.log(g_sizes)
    log_t = np.log(means)
    coeffs = np.polyfit(log_g, log_t, 1)
    degree = coeffs[0]
    
    # Plot fitted line
    fit_times = np.exp(coeffs[1]) * np.array(g_sizes) ** degree
    ax2.loglog(g_sizes, fit_times, 'r--', linewidth=2, 
               label=f'Fit: O(n^{degree:.2f})')
    
    ax2.set_xlabel('Graph G Size (vertices)')
    ax2.set_ylabel('Execution Time (seconds)')
    ax2.set_title('Approx Algorithm: Time vs Graph Size (Log-Log)')
    ax2.legend()
    ax2.grid(True, alpha=0.3, which='both')
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'scaling_analysis.png')
    plt.savefig(output_path)
    plt.close()
    log_success(f"Saved: {output_path}")
    
    log_info(f"Estimated complexity: O(n^{degree:.2f})")


def plot_time_by_density(results: List[dict], output_dir: str):
    """
    Plot 5: Show execution time breakdown by graph density.
    """
    log_info("Generating time by density plot...")
    
    # Group by (density, algorithm)
    times_by_density = defaultdict(lambda: defaultdict(list))
    
    for r in results:
        if r['status'] == 'success':
            times_by_density[r['density']][r['algorithm']].append(r['time_seconds'])
    
    if not times_by_density:
        log_warning("No results found for density analysis")
        return
    
    densities = sorted(times_by_density.keys())
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(densities))
    width = 0.35
    
    exact_means = [np.mean(times_by_density[d].get('exact', [0])) for d in densities]
    approx_means = [np.mean(times_by_density[d].get('approx', [0])) for d in densities]
    
    bars1 = ax.bar(x - width/2, exact_means, width, label='Exact', color='coral', alpha=0.8)
    bars2 = ax.bar(x + width/2, approx_means, width, label='Approx', color='steelblue', alpha=0.8)
    
    ax.set_xlabel('Graph Density')
    ax.set_ylabel('Mean Execution Time (seconds)')
    ax.set_title('Execution Time by Graph Density')
    ax.set_xticks(x)
    ax.set_xticklabels([d.capitalize() for d in densities])
    ax.legend()
    ax.set_yscale('log')
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'time_by_density.png')
    plt.savefig(output_path)
    plt.close()
    log_success(f"Saved: {output_path}")


def plot_cost_by_k(results: List[dict], output_dir: str):
    """
    Plot 6: Show how extension cost changes with k value.
    """
    log_info("Generating cost by k plot...")
    
    # Group by (k, algorithm)
    costs_by_k = defaultdict(lambda: defaultdict(list))
    
    for r in results:
        if r['status'] == 'success' and r['extension_cost'] >= 0:
            costs_by_k[r['k']][r['algorithm']].append(r['extension_cost'])
    
    if not costs_by_k:
        log_warning("No results found for cost by k analysis")
        return
    
    k_values = sorted(costs_by_k.keys())
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot exact and approx means with error bars
    exact_means = [np.mean(costs_by_k[k].get('exact', [])) if costs_by_k[k].get('exact') else np.nan for k in k_values]
    approx_means = [np.mean(costs_by_k[k].get('approx', [])) if costs_by_k[k].get('approx') else np.nan for k in k_values]
    exact_stds = [np.std(costs_by_k[k].get('exact', [])) if costs_by_k[k].get('exact') else 0 for k in k_values]
    approx_stds = [np.std(costs_by_k[k].get('approx', [])) if costs_by_k[k].get('approx') else 0 for k in k_values]
    
    ax.errorbar(k_values, exact_means, yerr=exact_stds, marker='o', capsize=5,
                color='coral', linewidth=2, markersize=8, label='Exact')
    ax.errorbar(k_values, approx_means, yerr=approx_stds, marker='s', capsize=5,
                color='steelblue', linewidth=2, markersize=8, label='Approx')
    
    ax.set_xlabel('k value')
    ax.set_ylabel('Mean Extension Cost')
    ax.set_title('Extension Cost vs k Value')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, 'cost_by_k.png')
    plt.savefig(output_path)
    plt.close()
    log_success(f"Saved: {output_path}")


def generate_summary_stats(results: List[dict], output_dir: str):
    """Generate summary statistics text file."""
    log_info("Generating summary statistics...")
    
    summary_path = os.path.join(output_dir, 'summary_stats.txt')
    
    with open(summary_path, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("k-Subgraph Isomorphism Experiment Summary\n")
        f.write("=" * 60 + "\n\n")
        
        # Overall counts
        total = len(results)
        exact_count = sum(1 for r in results if r['algorithm'] == 'exact')
        approx_count = sum(1 for r in results if r['algorithm'] == 'approx')
        success_count = sum(1 for r in results if r['status'] == 'success')
        timeout_count = sum(1 for r in results if 'timeout' in r['status'])
        
        f.write(f"Total experiments: {total}\n")
        f.write(f"  - Exact: {exact_count}\n")
        f.write(f"  - Approx: {approx_count}\n")
        f.write(f"  - Successful: {success_count}\n")
        f.write(f"  - Timeouts: {timeout_count}\n\n")
        
        # Time statistics
        f.write("Execution Time Statistics:\n")
        f.write("-" * 40 + "\n")
        
        for algo in ['exact', 'approx']:
            times = [r['time_seconds'] for r in results 
                     if r['algorithm'] == algo and r['status'] == 'success']
            if times:
                f.write(f"\n{algo.upper()}:\n")
                f.write(f"  Mean: {np.mean(times):.6f}s\n")
                f.write(f"  Median: {np.median(times):.6f}s\n")
                f.write(f"  Std: {np.std(times):.6f}s\n")
                f.write(f"  Min: {min(times):.6f}s\n")
                f.write(f"  Max: {max(times):.6f}s\n")
        
        # Cost comparison
        f.write("\n\nExtension Cost Comparison:\n")
        f.write("-" * 40 + "\n")
        
        by_input = defaultdict(dict)
        for r in results:
            if r['status'] == 'success' and r['extension_cost'] >= 0:
                by_input[r['input_file']][r['algorithm']] = r
        
        paired = [(algos['exact']['extension_cost'], algos['approx']['extension_cost'])
                  for algos in by_input.values()
                  if 'exact' in algos and 'approx' in algos]
        
        if paired:
            exact_costs, approx_costs = zip(*paired)
            optimal = sum(1 for e, a in paired if e == a)
            
            f.write(f"\nPaired comparisons: {len(paired)}\n")
            f.write(f"Approx matches exact: {optimal} ({100*optimal/len(paired):.1f}%)\n")
            
            ratios = [a/e if e > 0 else (1.0 if a == 0 else float('inf')) 
                      for e, a in paired]
            finite_ratios = [r for r in ratios if r != float('inf')]
            if finite_ratios:
                f.write(f"\nApproximation Ratio:\n")
                f.write(f"  Mean: {np.mean(finite_ratios):.3f}\n")
                f.write(f"  Median: {np.median(finite_ratios):.3f}\n")
                f.write(f"  Max: {max(finite_ratios):.3f}\n")
    
    log_success(f"Saved: {summary_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate plots from k-Subgraph Isomorphism experiment results",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-r", "--results-dir",
        default="results",
        help="Directory containing CSV results"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="plots",
        help="Output directory for plots"
    )
    parser.add_argument(
        "-c", "--csv-file",
        default="results.csv",
        help="CSV filename within results directory"
    )
    parser.add_argument(
        "--plots",
        nargs="+",
        default=["all"],
        choices=["all", "accuracy", "time", "time_success", "time_by_h", "ratio", "scaling", "density", "cost_k"],
        help="Which plots to generate"
    )
    
    args = parser.parse_args()
    
    log_header("k-Subgraph Isomorphism Plotter")
    
    # Resolve paths relative to script location
    script_dir = Path(__file__).parent
    results_dir = script_dir / args.results_dir
    output_dir = script_dir / args.output_dir
    csv_path = results_dir / args.csv_file
    
    # Check CSV exists
    if not csv_path.exists():
        log_error(f"Results file not found: {csv_path}")
        log_info("Please run experimenter.py first")
        sys.exit(1)
    
    os.makedirs(output_dir, exist_ok=True)
    
    log_info(f"Loading results from: {csv_path}")
    results = load_results(str(csv_path))
    log_info(f"Loaded {len(results)} experiment results")
    
    # Setup matplotlib style
    setup_plot_style()
    
    # Determine which plots to generate
    plots_to_generate = args.plots
    if "all" in plots_to_generate:
        plots_to_generate = ["accuracy", "time", "time_success", "time_by_h", "ratio", "scaling", "density", "cost_k"]
    
    # Generate requested plots
    if "accuracy" in plots_to_generate:
        plot_accuracy_comparison(results, str(output_dir))
    
    if "time" in plots_to_generate:
        plot_time_comparison(results, str(output_dir))
    
    if "time_success" in plots_to_generate:
        plot_time_comparison_successful(results, str(output_dir))
    
    if "time_by_h" in plots_to_generate:
        plot_time_comparison_by_h(results, str(output_dir))
    
    if "ratio" in plots_to_generate:
        plot_approximation_ratio(results, str(output_dir))
    
    if "scaling" in plots_to_generate:
        plot_scaling_analysis(results, str(output_dir))
    
    if "density" in plots_to_generate:
        plot_time_by_density(results, str(output_dir))
    
    if "cost_k" in plots_to_generate:
        plot_cost_by_k(results, str(output_dir))
    
    # Always generate summary
    generate_summary_stats(results, str(output_dir))
    
    log_header("Plotting Complete")
    log_info(f"All plots saved to: {output_dir}")


if __name__ == "__main__":
    main()

