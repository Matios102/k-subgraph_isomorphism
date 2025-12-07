#!/usr/bin/env python3
"""
Generate visualizations from experiment results.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path


def load_results(csv_path: str) -> pd.DataFrame:
    """Load results from CSV file."""
    df = pd.read_csv(csv_path)
    return df


def plot_runtime_comparison(df: pd.DataFrame, output_dir: str) -> None:
    """
    Plot 1: Runtime comparison between approx and exact algorithms.
    Only includes cases where both completed.
    """
    # Filter to cases where both completed
    both_completed = df[(df['approx_time'].notna()) & (df['exact_time'].notna())]
    
    if both_completed.empty:
        print("No cases where both algorithms completed - skipping runtime comparison")
        return
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 1a: Scatter plot approx vs exact time
    ax1 = axes[0]
    ax1.scatter(both_completed['exact_time'], both_completed['approx_time'], 
                alpha=0.6, c=both_completed['k'], cmap='viridis')
    
    # Add diagonal line (y = x)
    max_time = max(both_completed['exact_time'].max(), both_completed['approx_time'].max())
    ax1.plot([0, max_time], [0, max_time], 'r--', label='y = x')
    
    ax1.set_xlabel('Exact Algorithm Time (s)', fontsize=12)
    ax1.set_ylabel('Approx Algorithm Time (s)', fontsize=12)
    ax1.set_title('Runtime: Approx vs Exact', fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Add colorbar for k values
    scatter = ax1.scatter(both_completed['exact_time'], both_completed['approx_time'], 
                          alpha=0.6, c=both_completed['k'], cmap='viridis')
    plt.colorbar(scatter, ax=ax1, label='k value')
    
    # Plot 1b: Bar chart of average times by target size
    ax2 = axes[1]
    
    # Group by target size
    size_groups = both_completed.groupby('n_target').agg({
        'approx_time': 'mean',
        'exact_time': 'mean'
    }).reset_index()
    
    x = np.arange(len(size_groups))
    width = 0.35
    
    bars1 = ax2.bar(x - width/2, size_groups['approx_time'], width, 
                    label='Approx', color='steelblue')
    bars2 = ax2.bar(x + width/2, size_groups['exact_time'], width, 
                    label='Exact', color='darkorange')
    
    ax2.set_xlabel('Target Graph Size (vertices)', fontsize=12)
    ax2.set_ylabel('Average Time (s)', fontsize=12)
    ax2.set_title('Average Runtime by Graph Size', fontsize=14)
    ax2.set_xticks(x)
    ax2.set_xticklabels(size_groups['n_target'])
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'runtime_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir}/runtime_comparison.png")


def plot_accuracy_analysis(df: pd.DataFrame, output_dir: str) -> None:
    """
    Plot 2: Accuracy ratio analysis (approx_cost / exact_cost).
    """
    # Filter to cases with accuracy ratio
    has_accuracy = df[df['accuracy_ratio'].notna() & (df['accuracy_ratio'] < float('inf'))]
    
    if has_accuracy.empty:
        print("No accuracy data available - skipping accuracy analysis")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot 2a: Histogram of accuracy ratios
    ax1 = axes[0, 0]
    ax1.hist(has_accuracy['accuracy_ratio'], bins=30, edgecolor='black', alpha=0.7)
    ax1.axvline(x=1.0, color='red', linestyle='--', linewidth=2, label='Optimal (ratio=1)')
    ax1.axvline(x=has_accuracy['accuracy_ratio'].mean(), color='green', linestyle='--', 
                linewidth=2, label=f'Mean ({has_accuracy["accuracy_ratio"].mean():.2f})')
    ax1.set_xlabel('Accuracy Ratio (approx_cost / exact_cost)', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.set_title('Distribution of Accuracy Ratios', fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2b: Accuracy ratio by k value
    ax2 = axes[0, 1]
    k_accuracy = has_accuracy.groupby('k')['accuracy_ratio'].agg(['mean', 'std', 'min', 'max'])
    k_accuracy = k_accuracy.reset_index()
    
    ax2.errorbar(k_accuracy['k'], k_accuracy['mean'], yerr=k_accuracy['std'], 
                 fmt='o-', capsize=5, capthick=2, linewidth=2, markersize=8)
    ax2.axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='Optimal')
    ax2.set_xlabel('k value', fontsize=12)
    ax2.set_ylabel('Average Accuracy Ratio', fontsize=12)
    ax2.set_title('Accuracy Ratio vs k', fontsize=14)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 2c: Accuracy ratio by target graph size
    ax3 = axes[1, 0]
    size_accuracy = has_accuracy.groupby('n_target')['accuracy_ratio'].agg(['mean', 'std'])
    size_accuracy = size_accuracy.reset_index()
    
    ax3.errorbar(size_accuracy['n_target'], size_accuracy['mean'], yerr=size_accuracy['std'],
                 fmt='s-', capsize=5, capthick=2, linewidth=2, markersize=8, color='darkorange')
    ax3.axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='Optimal')
    ax3.set_xlabel('Target Graph Size (vertices)', fontsize=12)
    ax3.set_ylabel('Average Accuracy Ratio', fontsize=12)
    ax3.set_title('Accuracy Ratio vs Graph Size', fontsize=14)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 2d: Box plot of accuracy by k
    ax4 = axes[1, 1]
    k_values = sorted(has_accuracy['k'].unique())
    box_data = [has_accuracy[has_accuracy['k'] == k]['accuracy_ratio'].values for k in k_values]
    
    bp = ax4.boxplot(box_data, labels=k_values, patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor('lightblue')
    ax4.axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='Optimal')
    ax4.set_xlabel('k value', fontsize=12)
    ax4.set_ylabel('Accuracy Ratio', fontsize=12)
    ax4.set_title('Accuracy Ratio Distribution by k', fontsize=14)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'accuracy_analysis.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir}/accuracy_analysis.png")


def plot_scalability(df: pd.DataFrame, output_dir: str) -> None:
    """
    Plot 3: Scalability analysis - how time grows with problem size.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 3a: Approx time vs target size (log scale)
    ax1 = axes[0]
    
    approx_data = df[df['approx_time'].notna()]
    
    # Average time by target size
    approx_by_size = approx_data.groupby('n_target')['approx_time'].mean().reset_index()
    
    ax1.plot(approx_by_size['n_target'], approx_by_size['approx_time'], 
             'o-', linewidth=2, markersize=8, label='Approx', color='steelblue')
    
    # Also plot exact if available
    exact_data = df[df['exact_time'].notna()]
    if not exact_data.empty:
        exact_by_size = exact_data.groupby('n_target')['exact_time'].mean().reset_index()
        ax1.plot(exact_by_size['n_target'], exact_by_size['exact_time'], 
                 's-', linewidth=2, markersize=8, label='Exact', color='darkorange')
    
    ax1.set_xlabel('Target Graph Size (vertices)', fontsize=12)
    ax1.set_ylabel('Average Time (s)', fontsize=12)
    ax1.set_title('Scalability: Time vs Graph Size', fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale('log')
    
    # Plot 3b: Time vs k for different graph sizes
    ax2 = axes[1]
    
    # Select a few representative target sizes
    target_sizes = sorted(df['n_target'].unique())
    if len(target_sizes) > 5:
        # Pick 5 evenly spaced sizes
        indices = np.linspace(0, len(target_sizes)-1, 5, dtype=int)
        selected_sizes = [target_sizes[i] for i in indices]
    else:
        selected_sizes = target_sizes
    
    colors = plt.cm.viridis(np.linspace(0, 1, len(selected_sizes)))
    
    for size, color in zip(selected_sizes, colors):
        size_data = approx_data[approx_data['n_target'] == size]
        if not size_data.empty:
            k_time = size_data.groupby('k')['approx_time'].mean().reset_index()
            ax2.plot(k_time['k'], k_time['approx_time'], 
                     'o-', linewidth=2, markersize=6, color=color, label=f'n={size}')
    
    ax2.set_xlabel('k value', fontsize=12)
    ax2.set_ylabel('Average Approx Time (s)', fontsize=12)
    ax2.set_title('Approx Time vs k (by Graph Size)', fontsize=14)
    ax2.legend(title='Target Size')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'scalability.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir}/scalability.png")


def plot_cost_comparison(df: pd.DataFrame, output_dir: str) -> None:
    """
    Plot 4: Direct cost comparison between algorithms.
    """
    # Filter to cases where both costs are available
    both_costs = df[(df['approx_cost'].notna()) & (df['exact_cost'].notna())]
    
    if both_costs.empty:
        print("No cost comparison data available - skipping")
        return
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 4a: Scatter of approx_cost vs exact_cost
    ax1 = axes[0]
    ax1.scatter(both_costs['exact_cost'], both_costs['approx_cost'], 
                alpha=0.6, c=both_costs['n_target'], cmap='plasma')
    
    # Diagonal line
    max_cost = max(both_costs['exact_cost'].max(), both_costs['approx_cost'].max())
    ax1.plot([0, max_cost], [0, max_cost], 'r--', linewidth=2, label='y = x (optimal)')
    
    ax1.set_xlabel('Exact Cost (edges added)', fontsize=12)
    ax1.set_ylabel('Approx Cost (edges added)', fontsize=12)
    ax1.set_title('Cost Comparison: Approx vs Exact', fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    scatter = ax1.scatter(both_costs['exact_cost'], both_costs['approx_cost'], 
                          alpha=0.6, c=both_costs['n_target'], cmap='plasma')
    plt.colorbar(scatter, ax=ax1, label='Target Size')
    
    # Plot 4b: Average costs by k
    ax2 = axes[1]
    k_costs = both_costs.groupby('k').agg({
        'approx_cost': 'mean',
        'exact_cost': 'mean'
    }).reset_index()
    
    x = np.arange(len(k_costs))
    width = 0.35
    
    ax2.bar(x - width/2, k_costs['approx_cost'], width, label='Approx', color='steelblue')
    ax2.bar(x + width/2, k_costs['exact_cost'], width, label='Exact', color='darkorange')
    
    ax2.set_xlabel('k value', fontsize=12)
    ax2.set_ylabel('Average Cost (edges added)', fontsize=12)
    ax2.set_title('Average Cost by k', fontsize=14)
    ax2.set_xticks(x)
    ax2.set_xticklabels(k_costs['k'])
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'cost_comparison.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir}/cost_comparison.png")


def plot_summary_statistics(df: pd.DataFrame, output_dir: str) -> None:
    """
    Plot 5: Summary statistics and heatmaps.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 5a: Heatmap of average accuracy ratio by (n_target, k)
    ax1 = axes[0]
    
    has_accuracy = df[df['accuracy_ratio'].notna() & (df['accuracy_ratio'] < float('inf'))]
    
    if not has_accuracy.empty:
        pivot = has_accuracy.pivot_table(
            values='accuracy_ratio', 
            index='n_target', 
            columns='k', 
            aggfunc='mean'
        )
        
        im = ax1.imshow(pivot.values, aspect='auto', cmap='RdYlGn_r')
        ax1.set_xticks(range(len(pivot.columns)))
        ax1.set_xticklabels(pivot.columns)
        ax1.set_yticks(range(len(pivot.index)))
        ax1.set_yticklabels(pivot.index)
        ax1.set_xlabel('k value', fontsize=12)
        ax1.set_ylabel('Target Graph Size', fontsize=12)
        ax1.set_title('Accuracy Ratio Heatmap\n(lower is better)', fontsize=14)
        plt.colorbar(im, ax=ax1, label='Avg Accuracy Ratio')
    else:
        ax1.text(0.5, 0.5, 'No accuracy data', ha='center', va='center', fontsize=14)
        ax1.set_title('Accuracy Ratio Heatmap', fontsize=14)
    
    # Plot 5b: Timeout rate by target size
    ax2 = axes[1]
    
    timeout_by_size = df.groupby('n_target').agg({
        'exact_timed_out': 'mean'
    }).reset_index()
    timeout_by_size['exact_timed_out'] *= 100  # Convert to percentage
    
    ax2.bar(range(len(timeout_by_size)), timeout_by_size['exact_timed_out'], 
            color='coral', edgecolor='black')
    ax2.set_xticks(range(len(timeout_by_size)))
    ax2.set_xticklabels(timeout_by_size['n_target'], rotation=45)
    ax2.set_xlabel('Target Graph Size', fontsize=12)
    ax2.set_ylabel('Timeout Rate (%)', fontsize=12)
    ax2.set_title('Exact Algorithm Timeout Rate by Graph Size', fontsize=14)
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'summary_statistics.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir}/summary_statistics.png")


def generate_all_plots(csv_path: str, output_dir: str) -> None:
    """Generate all plots from results CSV."""
    print(f"Loading results from {csv_path}...")
    df = load_results(csv_path)
    
    print(f"Loaded {len(df)} experiment results")
    print(f"Unique test cases: {df['example'].nunique()}")
    print(f"k values: {sorted(df['k'].unique())}")
    print(f"Target sizes: {sorted(df['n_target'].unique())}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("\nGenerating plots...")
    plot_runtime_comparison(df, output_dir)
    plot_accuracy_analysis(df, output_dir)
    plot_scalability(df, output_dir)
    plot_cost_comparison(df, output_dir)
    plot_summary_statistics(df, output_dir)
    
    print(f"\nAll plots saved to {output_dir}/")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate plots from experiment results")
    parser.add_argument("--results", default="experiments/results.csv",
                        help="Path to results CSV file")
    parser.add_argument("--output-dir", default="experiments/plots",
                        help="Output directory for plots")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.results):
        print(f"Results file not found: {args.results}")
        print("Run run_experiments.py first to generate results.")
        return
    
    generate_all_plots(args.results, args.output_dir)


if __name__ == "__main__":
    main()
