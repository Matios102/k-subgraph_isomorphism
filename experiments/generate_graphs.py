#!/usr/bin/env python3
"""
Generate random multigraph test cases for k-subgraph isomorphism experiments.
"""

import random
import os
from pathlib import Path


def generate_multigraph(n: int, density: float = 0.3, max_multiplicity: int = 2) -> list[list[int]]:
    """
    Generate a random multigraph as an adjacency matrix.
    
    Args:
        n: Number of vertices
        density: Probability of an edge existing between any two vertices
        max_multiplicity: Maximum edge multiplicity (1 = simple graph)
    
    Returns:
        n x n adjacency matrix where A[i][j] = edge multiplicity from i to j
    """
    A = [[0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            if i != j and random.random() < density:
                A[i][j] = random.randint(1, max_multiplicity)
    
    return A


def write_test_case(filepath: str, G: list[list[int]], H: list[list[int]]) -> None:
    """
    Write a test case (pattern G, target H) to file in the expected format.
    
    Format:
        n_G
        <n_G x n_G adjacency matrix>
        n_H
        <n_H x n_H adjacency matrix>
    """
    with open(filepath, 'w') as f:
        # Write pattern graph G
        n_G = len(G)
        f.write(f"{n_G}\n")
        for row in G:
            f.write(" ".join(map(str, row)) + "\n")
        
        # Write target graph H
        n_H = len(H)
        f.write(f"{n_H}\n")
        for row in H:
            f.write(" ".join(map(str, row)) + "\n")


def generate_test_suite(output_dir: str, num_cases: int = 35) -> list[dict]:
    """
    Generate a suite of test cases with varying parameters.
    
    Returns:
        List of metadata dicts for each generated test case
    """
    os.makedirs(output_dir, exist_ok=True)
    
    test_configs = []
    
    # Configuration ranges
    # Pattern sizes: small (3-8) to keep exact algorithm tractable
    pattern_sizes = [3, 4, 5, 6, 7, 8, 9, 10]
    # Target sizes: varying from small to large
    target_sizes = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 20, 25, 30, 40, 50]
    # Densities
    densities = [0.2, 0.3, 0.4, 0.5, 0.6]
    # Multiplicities
    multiplicities = [1, 2, 3, 4]
    
    case_id = 0
    
    # Generate diverse test cases
    for _ in range(num_cases):
        n_pattern = random.choice(pattern_sizes)
        # Target must be >= pattern
        valid_targets = [t for t in target_sizes if t >= n_pattern]
        n_target = random.choice(valid_targets)
        
        density = random.choice(densities)
        max_mult = random.choice(multiplicities)
        
        # Generate graphs
        G = generate_multigraph(n_pattern, density, max_mult)
        H = generate_multigraph(n_target, density, max_mult)
        
        # Save test case
        filename = f"test_{case_id:03d}_n{n_pattern}_m{n_target}_d{int(density*100)}_mult{max_mult}.txt"
        filepath = os.path.join(output_dir, filename)
        write_test_case(filepath, G, H)
        
        test_configs.append({
            'id': case_id,
            'filename': filename,
            'filepath': filepath,
            'n_pattern': n_pattern,
            'n_target': n_target,
            'density': density,
            'max_multiplicity': max_mult
        })
        
        case_id += 1
    
    return test_configs


def generate_scalability_suite(output_dir: str) -> list[dict]:
    """
    Generate test cases specifically for scalability analysis.
    Fixed pattern size, varying target sizes.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    test_configs = []
    case_id = 1000  # Start from 1000 to distinguish from regular tests
    
    # Fixed small pattern for tractable exact computation
    n_pattern = 4
    density = 0.4
    max_mult = 2
    
    # Varying target sizes for scalability
    for n_target in [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80]:
        G = generate_multigraph(n_pattern, density, max_mult)
        H = generate_multigraph(n_target, density, max_mult)
        
        filename = f"scale_{case_id:04d}_n{n_pattern}_m{n_target}.txt"
        filepath = os.path.join(output_dir, filename)
        write_test_case(filepath, G, H)
        
        test_configs.append({
            'id': case_id,
            'filename': filename,
            'filepath': filepath,
            'n_pattern': n_pattern,
            'n_target': n_target,
            'density': density,
            'max_multiplicity': max_mult
        })
        
        case_id += 1
    
    return test_configs


def read_graph_from_file(filepath: str) -> tuple[list[list[int]], list[list[int]]]:
    """
    Read a test case file and return (G, H) adjacency matrices.
    """
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    idx = 0
    
    # Read G
    n_G = int(lines[idx])
    idx += 1
    G = []
    for i in range(n_G):
        row = list(map(int, lines[idx].split()))
        G.append(row)
        idx += 1
    
    # Read H
    n_H = int(lines[idx])
    idx += 1
    H = []
    for i in range(n_H):
        row = list(map(int, lines[idx].split()))
        H.append(row)
        idx += 1
    
    return G, H


def read_output_matrix(filepath: str) -> list[list[int]]:
    """
    Read an output adjacency matrix from file.
    """
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    matrix = []
    for line in lines:
        row = list(map(int, line.split()))
        matrix.append(row)
    
    return matrix


def compute_extension_cost(original_H: list[list[int]], extended_H: list[list[int]]) -> int:
    """
    Compute the cost of extension = total edges added.
    """
    n = len(original_H)
    cost = 0
    for i in range(n):
        for j in range(n):
            cost += extended_H[i][j] - original_H[i][j]
    return cost


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate multigraph test cases")
    parser.add_argument("--output-dir", default="experiments/generated",
                        help="Output directory for test cases")
    parser.add_argument("--num-cases", type=int, default=35,
                        help="Number of random test cases to generate")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    parser.add_argument("--scalability", action="store_true",
                        help="Also generate scalability test suite")
    
    args = parser.parse_args()
    
    random.seed(args.seed)
    
    print(f"Generating {args.num_cases} random test cases...")
    configs = generate_test_suite(args.output_dir, args.num_cases)
    print(f"Generated {len(configs)} test cases in {args.output_dir}/")
    
    if args.scalability:
        print("Generating scalability test suite...")
        scale_configs = generate_scalability_suite(args.output_dir)
        print(f"Generated {len(scale_configs)} scalability test cases")
    
    # Print summary
    print("\nTest case summary:")
    for config in configs[:5]:
        print(f"  {config['filename']}: pattern={config['n_pattern']}, target={config['n_target']}")
    if len(configs) > 5:
        print(f"  ... and {len(configs) - 5} more")
