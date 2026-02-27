# Cantera Reactor Suite

A command-line tool to load **Cantera YAML** reaction mechanisms and run common combustion reactor models:

- Constant-volume batch reactor
- Constant-pressure batch reactor
- CSTR (well-stirred reactor)
- PFR (approximated as a chain of stirred reactors)

It also plots:

- Temperature profiles
- Species mole-fraction profiles

And it can compare simulation results against experimental data using RMSE.

## Requirements

Install Python dependencies:

```bash
pip install cantera matplotlib numpy pandas
```

## Usage

```bash
python cantera_reactor_suite.py gri30.yaml \
  --fuel "CH4:1.0" \
  --oxidizer "O2:1.0, N2:3.76" \
  --phi 1.0 \
  --temperature 1000 \
  --pressure 101325 \
  --reactors const_volume const_pressure cstr pfr_chain \
  --species CH4 O2 CO2 H2O CO OH \
  --output-dir outputs
```

### Add experimental data fitting

Prepare a CSV containing an x-axis column (`time_s` or `distance_m`) and any overlapping result columns (for example `temperature_K`, `X_CO2`, `X_CO`).

Example:

```csv
time_s,temperature_K,X_CO2
0.000,1000,0.00
0.005,1200,0.02
0.010,1550,0.06
```

Run with fitting enabled:

```bash
python cantera_reactor_suite.py gri30.yaml \
  --experiment-csv my_experiment.csv \
  --experiment-x-column time_s
```

The script writes:

- Per-reactor CSV result files
- `temperature_profiles.png`
- `species_profiles.png`
- `experiment_fit_metrics.csv` (if experimental data is supplied)

## Notes

- The PFR model is a practical approximation via a reactor chain.
- Choose species that exist in your mechanism file.
- For high-temperature ignition problems, refine `--points` and `--end-time` for better resolution.
