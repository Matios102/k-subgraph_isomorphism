#!/usr/bin/env python3
"""
Run experiments comparing exact and approximate k-subgraph isomorphism algorithms.
"""

import subprocess
import time
import os
import csv
import sys
from pathlib import Path
from typing import Optional
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_graphs import (
    generate_test_suite,
    generate_scalability_suite,
    read_graph_from_file,
    read_output_matrix,
    compute_extension_cost
)


# Configuration
EXACT_TIMEOUT = 180  # 3 minutes in seconds
K_VALUES = list(range(1, 11))  # k = 1 to 10
PROJECT_ROOT = Path(__file__).parent.parent
EXECUTABLE = PROJECT_ROOT / "aac"


def build_project() -> bool:
    """Build the C++ project using make."""
    print("Building project...")
    try:
        result = subprocess.run(
            ["make"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            print(f"Build failed: {result.stderr}")
            return False
        print("Build successful!")
        return True
    except subprocess.TimeoutExpired:
        print("Build timed out")
        return False
    except Exception as e:
        print(f"Build error: {e}")
        return False


def run_algorithm(mode: str, k: int, input_path: str, output_path: str, 
                  timeout: Optional[float] = None) -> tuple[Optional[float], bool]:
    """
    Run the algorithm and return (execution_time, success).
    
    Returns:
        (time_seconds, success) - time is None if timed out or failed
    """
    cmd = [str(EXECUTABLE), mode, str(k), input_path, output_path]
    
    start_time = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        end_time = time.perf_counter()
        
        if result.returncode != 0:
            return None, False
        
        return end_time - start_time, True
        
    except subprocess.TimeoutExpired:
        return None, False
    except Exception as e:
        print(f"Error running {mode}: {e}")
        return None, False


def run_single_experiment(input_path: str, k: int, temp_dir: str) -> dict:
    """
    Run both algorithms on a single test case with a specific k value.
    
    Returns:
        Dictionary with timing and accuracy results
    """
    # Read original H for cost computation
    G, H = read_graph_from_file(input_path)
    n_pattern = len(G)
    n_target = len(H)
    
    result = {
        'input_path': input_path,
        'n_pattern': n_pattern,
        'n_target': n_target,
        'k': k,
        'approx_time': None,
        'exact_time': None,
        'approx_cost': None,
        'exact_cost': None,
        'accuracy_ratio': None,
        'exact_timed_out': False
    }
    
    # Create temporary output files
    approx_output = os.path.join(temp_dir, "approx_out.txt")
    exact_output = os.path.join(temp_dir, "exact_out.txt")
    
    # Run approximate algorithm (no timeout - should be fast)
    approx_time, approx_success = run_algorithm(
        "approx", k, input_path, approx_output, timeout=300
    )
    
    if approx_success and os.path.exists(approx_output):
        result['approx_time'] = approx_time
        try:
            approx_H = read_output_matrix(approx_output)
            result['approx_cost'] = compute_extension_cost(H, approx_H)
        except Exception as e:
            print(f"Error reading approx output: {e}")
    
    # Run exact algorithm with timeout
    exact_time, exact_success = run_algorithm(
        "exact", k, input_path, exact_output, timeout=EXACT_TIMEOUT
    )
    
    if exact_success and os.path.exists(exact_output):
        result['exact_time'] = exact_time
        try:
            exact_H = read_output_matrix(exact_output)
            result['exact_cost'] = compute_extension_cost(H, exact_H)
        except Exception as e:
            print(f"Error reading exact output: {e}")
    else:
        result['exact_timed_out'] = True
    
    # Compute accuracy ratio if both succeeded
    if result['approx_cost'] is not None and result['exact_cost'] is not None:
        if result['exact_cost'] > 0:
            result['accuracy_ratio'] = result['approx_cost'] / result['exact_cost']
        elif result['approx_cost'] == 0:
            result['accuracy_ratio'] = 1.0  # Both optimal
        else:
            result['accuracy_ratio'] = float('inf')  # Exact found 0-cost but approx didn't
    
    return result


def run_all_experiments(test_configs: list[dict], k_values: list[int], 
                        output_csv: str, skip_exact_after_timeout: bool = True) -> list[dict]:
    """
    Run experiments on all test cases with all k values.
    
    Args:
        test_configs: List of test case configurations
        k_values: List of k values to test
        output_csv: Path to output CSV file
        skip_exact_after_timeout: If True, skip exact for larger graphs after a timeout
    
    Returns:
        List of all results
    """
    all_results = []
    exact_timeout_threshold = None  # n_target size above which to skip exact
    
    # Create temp directory for outputs
    with tempfile.TemporaryDirectory() as temp_dir:
        total_experiments = len(test_configs) * len(k_values)
        current = 0
        
        # Sort by problem size (target graph size)
        sorted_configs = sorted(test_configs, key=lambda x: x['n_target'])
        
        start_time = time.time()
        
        for config in sorted_configs:
            input_path = config['filepath']
            
            for k in k_values:
                current += 1
                
                # Check if we should skip exact
                skip_exact = (
                    skip_exact_after_timeout and 
                    exact_timeout_threshold is not None and 
                    config['n_target'] > exact_timeout_threshold
                )
                
                # Calculate elapsed time and ETA
                elapsed = time.time() - start_time
                if current > 1:
                    avg_time_per_exp = elapsed / (current - 1)
                    remaining = total_experiments - current
                    eta_seconds = avg_time_per_exp * remaining
                    eta_str = f"ETA: {eta_seconds/60:.1f}min" if eta_seconds > 60 else f"ETA: {eta_seconds:.0f}s"
                else:
                    eta_str = "ETA: calculating..."
                
                skip_str = " [SKIP EXACT]" if skip_exact else ""
                print(f"[{current}/{total_experiments}] {config['filename']} k={k} "
                      f"(n={config['n_pattern']}, m={config['n_target']}){skip_str} - {eta_str}")
                
                if skip_exact:
                    # Only run approx
                    result = run_single_experiment_approx_only(
                        input_path, k, temp_dir, config
                    )
                    print(f"    -> Approx: {result['approx_time']:.4f}s, cost={result['approx_cost']}")
                else:
                    result = run_single_experiment(input_path, k, temp_dir)
                    
                    # Log results
                    approx_str = f"{result['approx_time']:.4f}s" if result['approx_time'] else "FAIL"
                    exact_str = f"{result['exact_time']:.4f}s" if result['exact_time'] else "TIMEOUT"
                    ratio_str = f"{result['accuracy_ratio']:.3f}" if result['accuracy_ratio'] else "N/A"
                    print(f"    -> Approx: {approx_str}, cost={result['approx_cost']} | "
                          f"Exact: {exact_str}, cost={result['exact_cost']} | Ratio: {ratio_str}")
                    
                    # Update timeout threshold if exact timed out
                    if result['exact_timed_out'] and skip_exact_after_timeout:
                        if exact_timeout_threshold is None:
                            exact_timeout_threshold = config['n_target']
                            print(f"    *** Exact algorithm timed out at n_target={exact_timeout_threshold}, "
                                  f"will skip exact for larger graphs ***")
                
                result['example'] = config['filename']
                result['density'] = config.get('density', 0)
                result['max_multiplicity'] = config.get('max_multiplicity', 1)
                
                all_results.append(result)
                
                # Save intermediate results every 50 experiments
                if current % 50 == 0:
                    write_results_csv(all_results, output_csv)
                    print(f"    [Checkpoint saved: {current} results]")
        
        total_time = time.time() - start_time
        print(f"\nTotal experiment time: {total_time/60:.1f} minutes")
    
    # Write final results to CSV
    write_results_csv(all_results, output_csv)
    
    return all_results


def run_single_experiment_approx_only(input_path: str, k: int, temp_dir: str, 
                                       config: dict) -> dict:
    """Run only the approximate algorithm (when exact is skipped)."""
    G, H = read_graph_from_file(input_path)
    n_pattern = len(G)
    n_target = len(H)
    
    result = {
        'input_path': input_path,
        'n_pattern': n_pattern,
        'n_target': n_target,
        'k': k,
        'approx_time': None,
        'exact_time': None,
        'approx_cost': None,
        'exact_cost': None,
        'accuracy_ratio': None,
        'exact_timed_out': True  # Skipped = treated as timeout
    }
    
    approx_output = os.path.join(temp_dir, "approx_out.txt")
    
    approx_time, approx_success = run_algorithm(
        "approx", k, input_path, approx_output, timeout=300
    )
    
    if approx_success and os.path.exists(approx_output):
        result['approx_time'] = approx_time
        try:
            approx_H = read_output_matrix(approx_output)
            result['approx_cost'] = compute_extension_cost(H, approx_H)
        except Exception as e:
            print(f"Error reading approx output: {e}")
    
    return result


def write_results_csv(results: list[dict], output_path: str) -> None:
    """Write results to CSV file."""
    fieldnames = [
        'example', 'n_pattern', 'n_target', 'k', 'density', 'max_multiplicity',
        'approx_time', 'exact_time', 'approx_cost', 'exact_cost', 
        'accuracy_ratio', 'exact_timed_out'
    ]
    
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Results saved to {output_path}")


def main():
    import argparse
    import random
    
    parser = argparse.ArgumentParser(description="Run k-subgraph isomorphism experiments")
    parser.add_argument("--generate", action="store_true",
                        help="Generate new test cases before running")
    parser.add_argument("--num-cases", type=int, default=35,
                        help="Number of test cases to generate")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for test generation")
    parser.add_argument("--k-min", type=int, default=1,
                        help="Minimum k value")
    parser.add_argument("--k-max", type=int, default=10,
                        help="Maximum k value")
    parser.add_argument("--timeout", type=int, default=180,
                        help="Timeout for exact algorithm in seconds")
    parser.add_argument("--output-dir", default="experiments",
                        help="Output directory")
    parser.add_argument("--scalability", action="store_true",
                        help="Include scalability tests")
    parser.add_argument("--use-existing", action="store_true",
                        help="Use existing test cases in generated/ directory")
    
    args = parser.parse_args()
    
    global EXACT_TIMEOUT
    EXACT_TIMEOUT = args.timeout
    
    k_values = list(range(args.k_min, args.k_max + 1))
    
    # Build project first
    if not build_project():
        print("Failed to build project. Exiting.")
        sys.exit(1)
    
    # Check executable exists
    if not EXECUTABLE.exists():
        print(f"Executable not found: {EXECUTABLE}")
        sys.exit(1)
    
    generated_dir = os.path.join(args.output_dir, "generated")
    results_csv = os.path.join(args.output_dir, "results.csv")
    
    # Generate or load test cases
    if args.use_existing:
        # Load existing test cases
        test_configs = []
        for filename in sorted(os.listdir(generated_dir)):
            if filename.endswith('.txt'):
                filepath = os.path.join(generated_dir, filename)
                G, H = read_graph_from_file(filepath)
                test_configs.append({
                    'id': len(test_configs),
                    'filename': filename,
                    'filepath': filepath,
                    'n_pattern': len(G),
                    'n_target': len(H),
                    'density': 0.3,  # Default
                    'max_multiplicity': 2  # Default
                })
        print(f"Loaded {len(test_configs)} existing test cases")
    else:
        random.seed(args.seed)
        
        if args.generate or not os.path.exists(generated_dir):
            print(f"Generating {args.num_cases} test cases...")
            test_configs = generate_test_suite(generated_dir, args.num_cases)
            
            if args.scalability:
                print("Generating scalability test cases...")
                scale_configs = generate_scalability_suite(generated_dir)
                test_configs.extend(scale_configs)
            
            print(f"Generated {len(test_configs)} total test cases")
        else:
            # Load from generated directory
            test_configs = []
            for filename in sorted(os.listdir(generated_dir)):
                if filename.endswith('.txt'):
                    filepath = os.path.join(generated_dir, filename)
                    G, H = read_graph_from_file(filepath)
                    test_configs.append({
                        'id': len(test_configs),
                        'filename': filename,
                        'filepath': filepath,
                        'n_pattern': len(G),
                        'n_target': len(H),
                        'density': 0.3,
                        'max_multiplicity': 2
                    })
            print(f"Loaded {len(test_configs)} test cases from {generated_dir}")
    
    if not test_configs:
        print("No test cases found. Use --generate to create new ones.")
        sys.exit(1)
    
    # Run experiments
    print(f"\nRunning experiments with k in {k_values}...")
    print(f"Exact algorithm timeout: {EXACT_TIMEOUT} seconds")
    print("-" * 60)
    
    results = run_all_experiments(test_configs, k_values, results_csv)
    
    # Print summary
    print("\n" + "=" * 60)
    print("EXPERIMENT SUMMARY")
    print("=" * 60)
    
    total = len(results)
    exact_completed = sum(1 for r in results if r['exact_time'] is not None)
    exact_timed_out = sum(1 for r in results if r['exact_timed_out'])
    
    print(f"Total experiments: {total}")
    print(f"Exact completed: {exact_completed} ({100*exact_completed/total:.1f}%)")
    print(f"Exact timed out/skipped: {exact_timed_out} ({100*exact_timed_out/total:.1f}%)")
    
    # Accuracy statistics (where both completed)
    accuracy_results = [r for r in results if r['accuracy_ratio'] is not None]
    if accuracy_results:
        ratios = [r['accuracy_ratio'] for r in accuracy_results]
        avg_ratio = sum(ratios) / len(ratios)
        max_ratio = max(ratios)
        min_ratio = min(ratios)
        
        print(f"\nAccuracy (approx_cost / exact_cost):")
        print(f"  Average ratio: {avg_ratio:.3f}")
        print(f"  Best ratio: {min_ratio:.3f}")
        print(f"  Worst ratio: {max_ratio:.3f}")
    
    print(f"\nResults saved to: {results_csv}")
    print("Run plot_results.py to generate visualizations.")


if __name__ == "__main__":
    main()
