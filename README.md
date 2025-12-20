## Build

```bash
make
```

## Usage

```bash
./aac [exact|approx] k input_path [output_path]
```

- `exact` or `approx`: choose algorithm mode
- `k`: positive integer
- `input_path`: path to input file containing two graphs
- `output_path`: optional output file (stdout if omitted)

## Example

```bash
./aac exact 5 examples/example4_multigraph.txt examples/example4.out
```

## Experiments

The `experiments/` folder contains Python scripts for benchmarking and comparing the exact and approx algorithms.

### Scripts

```bash
# Generate input files
uv run python experiments/generator.py

# Run experiments
uv run python experiments/experimentor.py

# Plot charts
uv run python experiments/plotter.py
```

### Output Structure

```
experiments/
├── inputs/           # Generated test graphs
├── outputs/          # Algorithm output matrices
├── results/          # results.csv
└── plots/            # PNG visualizations + summary_stats.txt
```

### g++ compilation command
g++ -std=c++20 -Wall -Iinclude -static-libgcc -static-libstdc++ src/approx.cpp src/exact.cpp src/io.cpp src/main.cpp -o aac.exe