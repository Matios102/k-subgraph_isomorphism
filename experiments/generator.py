#!/usr/bin/env python3
"""
Generator script for k-Subgraph Isomorphism experiments.
Creates random directed multigraphs for testing exact and approx algorithms.
"""

import argparse
import os
import random
import sys
from pathlib import Path

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

def log_header(msg: str):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{msg.center(60)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

def log_progress(current: int, total: int, desc: str = ""):
    bar_len = 40
    filled = int(bar_len * current / total)
    bar = '█' * filled + '░' * (bar_len - filled)
    pct = 100 * current / total
    print(f"\r{Colors.BLUE}[PROGRESS]{Colors.ENDC} {bar} {pct:5.1f}% ({current}/{total}) {desc}", end='', flush=True)
    if current == total:
        print()


def generate_random_multigraph(n: int, density: float, max_multiplicity: int = 3, seed: int = None) -> list:
    """
    Generate a random directed multigraph as an adjacency matrix.
    
    Args:
        n: Number of vertices
        density: Edge density (0.0 to 1.0)
        max_multiplicity: Maximum edge multiplicity (for multigraph)
        seed: Random seed for reproducibility
    
    Returns:
        n x n adjacency matrix with edge multiplicities
    """
    if seed is not None:
        random.seed(seed)
    
    adj = [[0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            if i != j and random.random() < density:
                # Random multiplicity from 1 to max_multiplicity
                adj[i][j] = random.randint(1, max_multiplicity)
    
    return adj


def write_graph_file(filepath: str, adj_G: list, adj_H: list):
    """Write two graphs to a file in the expected format."""
    with open(filepath, 'w') as f:
        # Write graph G
        n_G = len(adj_G)
        f.write(f"{n_G}\n")
        for row in adj_G:
            f.write(" ".join(map(str, row)) + "\n")
        
        # Write graph H
        n_H = len(adj_H)
        f.write(f"{n_H}\n")
        for row in adj_H:
            f.write(" ".join(map(str, row)) + "\n")


def generate_test_cases(output_dir: str, 
                        g_sizes_small: list,
                        g_sizes_large: list,
                        h_ratios: list,
                        k_values: list,
                        densities: dict,
                        seeds_per_config: int,
                        max_multiplicity: int):
    """Generate all test case files."""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Calculate total number of files to generate
    total_small = len(g_sizes_small) * len(h_ratios) * len(k_values) * len(densities) * seeds_per_config
    total_large = len(g_sizes_large) * len(h_ratios) * len(k_values) * len(densities) * seeds_per_config
    total = total_small + total_large
    
    log_info(f"Will generate {total} test files:")
    log_info(f"  - Small graphs (G: {g_sizes_small}): {total_small} files")
    log_info(f"  - Large graphs (G: {g_sizes_large}): {total_large} files")
    log_info(f"  - H/G ratios: {h_ratios}")
    log_info(f"  - k values: {k_values}")
    log_info(f"  - Densities: {densities}")
    log_info(f"  - Seeds per config: {seeds_per_config}")
    
    count = 0
    all_g_sizes = g_sizes_small + g_sizes_large
    
    for n_G in all_g_sizes:
        for ratio in h_ratios:
            n_H = max(n_G + 1, int(n_G * ratio))  # H must be larger than G
            
            for k in k_values:
                for density_name, density_val in densities.items():
                    for seed in range(seeds_per_config):
                        count += 1
                        
                        # Generate filename with all parameters
                        filename = f"g{n_G}_h{n_H}_k{k}_d{density_name}_s{seed}.txt"
                        filepath = os.path.join(output_dir, filename)
                        
                        # Use combined seed for reproducibility
                        combined_seed = hash((n_G, n_H, k, density_name, seed)) % (2**31)
                        
                        # Generate graphs
                        adj_G = generate_random_multigraph(n_G, density_val, max_multiplicity, combined_seed)
                        adj_H = generate_random_multigraph(n_H, density_val, max_multiplicity, combined_seed + 1)
                        
                        # Write to file
                        write_graph_file(filepath, adj_G, adj_H)
                        
                        log_progress(count, total, f"Created: {filename}")
    
    log_success(f"Generated {count} test files in '{output_dir}'")


def main():
    parser = argparse.ArgumentParser(
        description="Generate test cases for k-Subgraph Isomorphism experiments",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-o", "--output-dir",
        default="inputs",
        help="Output directory for generated files"
    )
    parser.add_argument(
        "--g-small",
        type=int,
        nargs="+",
        default=[2, 3, 4, 5, 6],
        help="Small G sizes (for exact vs approx comparison)"
    )
    parser.add_argument(
        "--g-large",
        type=int,
        nargs="+",
        default=[7, 8, 9, 10, 12, 15],
        help="Large G sizes (for approx-only timing)"
    )
    parser.add_argument(
        "--h-ratios",
        type=float,
        nargs="+",
        default=[1.5, 2.0, 2.5, 3.0, 4.0],
        help="H size ratios (H_size = G_size * ratio)"
    )
    parser.add_argument(
        "--k-values",
        type=int,
        nargs="+",
        default=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        help="Values of k to test"
    )
    parser.add_argument(
        "--densities",
        type=str,
        nargs="+",
        default=["sparse", "medium", "dense"],
        choices=["sparse", "medium", "dense"],
        help="Graph density levels"
    )
    parser.add_argument(
        "--seeds",
        type=int,
        default=3,
        help="Number of random seeds per configuration"
    )
    parser.add_argument(
        "--max-multiplicity",
        type=int,
        default=3,
        help="Maximum edge multiplicity for multigraphs"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: reduced configurations for testing"
    )
    
    args = parser.parse_args()
    
    log_header("k-Subgraph Isomorphism Test Generator")
    
    # Density mapping
    density_map = {
        "sparse": 0.2,
        "medium": 0.5,
        "dense": 0.8
    }
    densities = {k: density_map[k] for k in args.densities}
    
    # Quick mode for testing
    if args.quick:
        log_warning("Quick mode enabled - reduced configurations")
        args.g_small = [3, 4, 5]
        args.g_large = [7, 8]
        args.h_ratios = [2.0, 3.0]
        args.k_values = [1, 3, 5]
        args.seeds = 2
    
    # Resolve output directory relative to script location
    script_dir = Path(__file__).parent
    output_dir = script_dir / args.output_dir
    
    generate_test_cases(
        output_dir=str(output_dir),
        g_sizes_small=args.g_small,
        g_sizes_large=args.g_large,
        h_ratios=args.h_ratios,
        k_values=args.k_values,
        densities=densities,
        seeds_per_config=args.seeds,
        max_multiplicity=args.max_multiplicity
    )
    
    log_header("Generation Complete")


if __name__ == "__main__":
    main()

