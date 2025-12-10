#!/usr/bin/env python3
"""
Experimenter script for k-Subgraph Isomorphism experiments.
Runs exact and approx algorithms on generated test cases and records results.
"""

import argparse
import csv
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

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

def log_progress(current: int, total: int, desc: str = ""):
    bar_len = 40
    filled = int(bar_len * current / total)
    bar = '█' * filled + '░' * (bar_len - filled)
    pct = 100 * current / total
    print(f"\r{Colors.BLUE}[PROGRESS]{Colors.ENDC} {bar} {pct:5.1f}% ({current}/{total}) {desc}", end='', flush=True)
    if current == total:
        print()


def parse_filename(filename: str) -> Optional[dict]:
    """
    Parse parameters from filename.
    Expected format: g{nG}_h{nH}_k{k}_d{density}_s{seed}.txt
    """
    pattern = r'g(\d+)_h(\d+)_k(\d+)_d(\w+)_s(\d+)\.txt'
    match = re.match(pattern, filename)
    if not match:
        return None
    
    return {
        'nG': int(match.group(1)),
        'nH': int(match.group(2)),
        'k': int(match.group(3)),
        'density': match.group(4),
        'seed': int(match.group(5))
    }


def estimate_exact_complexity(nG: int, nH: int, k: int) -> float:
    """
    Estimate exact algorithm complexity.
    
    The exact algorithm:
    1. Enumerates all injective mappings from G to H: P(nH, nG) = nH! / (nH-nG)!
    2. For each k-multicombination of mappings, computes extension cost
    
    Total combinations: C(mappings + k - 1, k)
    """
    # Number of injective mappings from G to H
    mappings = math.perm(nH, nG)
    
    # k-multicombinations with repetition: C(n+k-1, k) where n = mappings
    combinations = math.comb(mappings + k - 1, k)
    
    return float(combinations)


def read_graph_from_file(filepath: str) -> Tuple[list, list]:
    """Read the two graphs from an input file."""
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    idx = 0
    
    # Read G
    n_G = int(lines[idx])
    idx += 1
    adj_G = []
    for i in range(n_G):
        row = list(map(int, lines[idx].split()))
        adj_G.append(row)
        idx += 1
    
    # Read H
    n_H = int(lines[idx])
    idx += 1
    adj_H = []
    for i in range(n_H):
        row = list(map(int, lines[idx].split()))
        adj_H.append(row)
        idx += 1
    
    return adj_G, adj_H


def parse_output_matrix(output: str, n: int) -> Optional[list]:
    """Parse output matrix from algorithm stdout."""
    lines = [line.strip() for line in output.strip().split('\n') if line.strip()]
    
    if len(lines) != n:
        return None
    
    matrix = []
    for line in lines:
        try:
            row = list(map(int, line.split()))
            if len(row) != n:
                return None
            matrix.append(row)
        except ValueError:
            return None
    
    return matrix


def calculate_extension_cost(original_H: list, extended_H: list) -> int:
    """Calculate the sum of added edges (extension cost)."""
    n = len(original_H)
    cost = 0
    for i in range(n):
        for j in range(n):
            diff = extended_H[i][j] - original_H[i][j]
            if diff > 0:
                cost += diff
    return cost


def run_algorithm(binary_path: str, mode: str, k: int, input_path: str, 
                  timeout: float) -> Tuple[Optional[str], float, str]:
    """
    Run the algorithm and return (output, time, status).
    
    Returns:
        output: stdout from algorithm (or None on failure)
        time: execution time in seconds
        status: "success", "timeout", or "error"
    """
    cmd = [binary_path, mode, str(k), input_path]
    
    start_time = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        elapsed = time.perf_counter() - start_time
        
        if result.returncode != 0:
            return None, elapsed, f"error: {result.stderr.strip()}"
        
        return result.stdout, elapsed, "success"
    
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start_time
        return None, elapsed, "timeout"
    
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        return None, elapsed, f"error: {str(e)}"


def load_existing_results(csv_path: str) -> set:
    """Load already processed (input_file, algorithm) pairs for resume capability."""
    processed = set()
    if os.path.exists(csv_path):
        with open(csv_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row['input_file'], row['algorithm'])
                processed.add(key)
    return processed


def run_experiments(inputs_dir: str, outputs_dir: str, results_dir: str,
                    binary_path: str, exact_timeout: float, approx_timeout: float,
                    max_exact_g_size: int, resume: bool, adaptive_skip: bool):
    """Run all experiments and save results to CSV."""
    
    os.makedirs(outputs_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    
    csv_path = os.path.join(results_dir, "results.csv")
    
    # Get list of input files - sort by complexity to process easier cases first
    input_files = sorted([f for f in os.listdir(inputs_dir) if f.endswith('.txt')])
    
    # Sort by estimated complexity (lowest first) for adaptive skip to work effectively
    def get_complexity(filename):
        params = parse_filename(filename)
        if not params:
            return float('inf')
        return estimate_exact_complexity(params['nG'], params['nH'], params['k'])
    input_files.sort(key=get_complexity)
    
    if not input_files:
        log_error(f"No input files found in '{inputs_dir}'")
        return
    
    log_info(f"Found {len(input_files)} input files")
    
    # Load existing results for resume
    processed = set()
    if resume and os.path.exists(csv_path):
        processed = load_existing_results(csv_path)
        log_info(f"Resume mode: {len(processed)} results already recorded")
    
    # Prepare CSV
    fieldnames = ['input_file', 'nG', 'nH', 'k', 'density', 'seed', 
                  'algorithm', 'time_seconds', 'extension_cost', 'status']
    
    # Open CSV in append mode if resuming, else write mode
    write_header = not (resume and os.path.exists(csv_path))
    csv_file = open(csv_path, 'a' if resume else 'w', newline='')
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    
    if write_header:
        writer.writeheader()
    
    # Adaptive skip tracking: minimum complexity that caused timeout for each algorithm
    # If exact times out at complexity X, skip all cases with complexity >= X
    timeout_complexity_threshold = {
        'exact': float('inf'),
        'approx': float('inf')
    }
    
    # Count total experiments
    total_experiments = 0
    for f in input_files:
        params = parse_filename(f)
        if params:
            # Count exact + approx (exact only if G is small enough)
            if params['nG'] <= max_exact_g_size:
                total_experiments += 2
            else:
                total_experiments += 1
    
    # Subtract already processed
    if resume:
        already_done = len(processed)
        log_info(f"Experiments to run: {total_experiments - already_done} (skipping {already_done})")
    
    if adaptive_skip:
        log_info("Adaptive skip enabled: will skip higher complexity cases after timeouts")
    
    completed = 0
    skipped = 0
    adaptive_skipped = 0
    
    for input_file in input_files:
        params = parse_filename(input_file)
        if not params:
            log_warning(f"Skipping file with invalid name: {input_file}")
            continue
        
        input_path = os.path.join(inputs_dir, input_file)
        
        # Read original H for cost calculation
        try:
            _, original_H = read_graph_from_file(input_path)
        except Exception as e:
            log_error(f"Failed to read {input_file}: {e}")
            continue
        
        n_H = len(original_H)
        n_G = params['nG']
        
        # Determine which algorithms to run
        algorithms = ['approx']
        if n_G <= max_exact_g_size:
            algorithms.insert(0, 'exact')  # Run exact first
        
        for algo in algorithms:
            key = (input_file, algo)
            if key in processed:
                skipped += 1
                continue
            
            # Calculate complexity for this case
            complexity = estimate_exact_complexity(n_G, params['nH'], params['k'])
            
            # Adaptive skip: if complexity >= threshold from a previous timeout, skip it
            if adaptive_skip and complexity >= timeout_complexity_threshold[algo]:
                adaptive_skipped += 1
                # Still record the skip in CSV
                row = {
                    'input_file': input_file,
                    'nG': n_G,
                    'nH': params['nH'],
                    'k': params['k'],
                    'density': params['density'],
                    'seed': params['seed'],
                    'algorithm': algo,
                    'time_seconds': '0',
                    'extension_cost': -1,
                    'status': f'complexity_skip (complexity={complexity:.2e}, threshold={timeout_complexity_threshold[algo]:.2e})'
                }
                writer.writerow(row)
                csv_file.flush()
                continue
            
            completed += 1
            timeout = exact_timeout if algo == 'exact' else approx_timeout
            
            log_progress(completed + skipped + adaptive_skipped, total_experiments, 
                        f"{algo}:{input_file[:30]}...")
            
            # Run algorithm
            output, elapsed, status = run_algorithm(
                binary_path, algo, params['k'], input_path, timeout
            )
            
            # Track timeouts for adaptive skip - record complexity threshold
            if adaptive_skip and status == 'timeout':
                if complexity < timeout_complexity_threshold[algo]:
                    timeout_complexity_threshold[algo] = complexity
                    log_warning(f"\n{algo} timed out at complexity={complexity:.2e} (G={n_G}, H={params['nH']}, k={params['k']})")
                    log_warning(f"Will skip cases with complexity >= {complexity:.2e}")
            
            # Calculate extension cost if successful
            extension_cost = -1
            if status == "success" and output:
                result_matrix = parse_output_matrix(output, n_H)
                if result_matrix:
                    extension_cost = calculate_extension_cost(original_H, result_matrix)
                    
                    # Save output file
                    output_filename = f"{input_file[:-4]}_{algo}.out"
                    output_path = os.path.join(outputs_dir, output_filename)
                    with open(output_path, 'w') as f:
                        f.write(output)
            
            # Write result row
            row = {
                'input_file': input_file,
                'nG': n_G,
                'nH': params['nH'],
                'k': params['k'],
                'density': params['density'],
                'seed': params['seed'],
                'algorithm': algo,
                'time_seconds': f"{elapsed:.6f}",
                'extension_cost': extension_cost,
                'status': status
            }
            writer.writerow(row)
            csv_file.flush()  # Ensure data is written
    
    csv_file.close()
    
    print()  # New line after progress bar
    log_success(f"Completed {completed} experiments, skipped {skipped} (resume), adaptive skipped {adaptive_skipped}")
    log_success(f"Results saved to: {csv_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run k-Subgraph Isomorphism experiments",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-i", "--inputs-dir",
        default="inputs",
        help="Directory containing input files"
    )
    parser.add_argument(
        "-o", "--outputs-dir",
        default="outputs",
        help="Directory for algorithm outputs"
    )
    parser.add_argument(
        "-r", "--results-dir",
        default="results",
        help="Directory for CSV results"
    )
    parser.add_argument(
        "-b", "--binary",
        default="../aac",
        help="Path to the aac binary"
    )
    parser.add_argument(
        "--exact-timeout",
        type=float,
        default=240.0,
        help="Timeout in seconds for exact algorithm"
    )
    parser.add_argument(
        "--approx-timeout",
        type=float,
        default=240.0,
        help="Timeout in seconds for approx algorithm"
    )
    parser.add_argument(
        "--max-exact-g",
        type=int,
        default=6,
        help="Maximum G size for running exact algorithm"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous run (skip already processed inputs)"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Start fresh (overwrite existing results)"
    )
    parser.add_argument(
        "--adaptive-skip",
        action="store_true",
        default=True,
        help="Skip higher complexity cases after timeout (enabled by default)"
    )
    parser.add_argument(
        "--no-adaptive-skip",
        action="store_true",
        help="Disable adaptive skip - try all cases even after timeouts"
    )
    
    args = parser.parse_args()
    
    log_header("k-Subgraph Isomorphism Experimenter")
    
    # Resolve paths relative to script location
    script_dir = Path(__file__).parent
    inputs_dir = script_dir / args.inputs_dir
    outputs_dir = script_dir / args.outputs_dir
    results_dir = script_dir / args.results_dir
    binary_path = (script_dir / args.binary).resolve()
    
    # Check binary exists
    if not binary_path.exists():
        log_error(f"Binary not found: {binary_path}")
        log_info("Please build the project first with 'make'")
        sys.exit(1)
    
    # Check inputs directory exists
    if not inputs_dir.exists():
        log_error(f"Inputs directory not found: {inputs_dir}")
        log_info("Please run generator.py first")
        sys.exit(1)
    
    log_info(f"Binary: {binary_path}")
    log_info(f"Inputs: {inputs_dir}")
    log_info(f"Outputs: {outputs_dir}")
    log_info(f"Results: {results_dir}")
    log_info(f"Exact timeout: {args.exact_timeout}s")
    log_info(f"Approx timeout: {args.approx_timeout}s")
    log_info(f"Max G size for exact: {args.max_exact_g}")
    
    # Determine resume mode
    resume = not args.no_resume  # Default to resume
    if args.no_resume:
        log_warning("Starting fresh - existing results will be overwritten")
    else:
        log_info("Resume mode enabled (use --no-resume to start fresh)")
    
    # Determine adaptive skip mode
    adaptive_skip = not args.no_adaptive_skip  # Default to enabled
    if args.no_adaptive_skip:
        log_warning("Adaptive skip disabled - will try all cases even after timeouts")
    else:
        log_info("Adaptive skip enabled - will skip higher complexity cases after timeouts")
    
    run_experiments(
        inputs_dir=str(inputs_dir),
        outputs_dir=str(outputs_dir),
        results_dir=str(results_dir),
        binary_path=str(binary_path),
        exact_timeout=args.exact_timeout,
        approx_timeout=args.approx_timeout,
        max_exact_g_size=args.max_exact_g,
        resume=resume,
        adaptive_skip=adaptive_skip
    )
    
    log_header("Experiments Complete")


if __name__ == "__main__":
    main()

