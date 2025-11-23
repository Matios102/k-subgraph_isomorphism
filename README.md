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
