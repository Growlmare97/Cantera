# Cantera Reactor Suite

A toolkit for combustion studies with Cantera YAML mechanisms:

- **Python CLI** for reactor simulation (batch CV/CP, CSTR, PFR-chain)
- **Reactor energy mode control** (`adiabatic` or `isothermal`) per reactor
- **Plots and CSV outputs** for temperature/composition
- **Experimental fit workflow** with RMSE metrics
- **Netlify-ready web UI** for easier configuration and local data plotting

## 1) Python CLI

### Install

```bash
pip install cantera matplotlib numpy pandas
```

### Usage

```bash
python cantera_reactor_suite.py gri30.yaml \
  --fuel "CH4:1.0" \
  --oxidizer "O2:1.0, N2:3.76" \
  --phi 1.0 \
  --temperature 1000 \
  --pressure 101325 \
  --reactors const_volume:adiabatic const_pressure:adiabatic cstr:isothermal pfr_chain:adiabatic \
  --species CH4 O2 CO2 H2O CO OH \
  --output-dir outputs
```

### Reactor energy property (new)

You can now specify energy behavior per reactor:

- `adiabatic` → solves energy equation (`energy=on`)
- `isothermal` → keeps temperature fixed (`energy=off`)

Examples:

```bash
--reactors const_volume:isothermal cstr:adiabatic
```

Or use a default:

```bash
--default-energy isothermal --reactors const_volume const_pressure cstr
```

### Experimental fitting

Use a CSV with an x-axis (`time_s` or `distance_m`) and overlapping observables (`temperature_K`, `X_CO2`, ...):

```bash
python cantera_reactor_suite.py gri30.yaml \
  --experiment-csv my_experiment.csv \
  --experiment-x-column time_s
```

Outputs:

- Per-reactor CSV result files
- `temperature_profiles.png`
- `species_profiles.png`
- `experiment_fit_metrics.csv` (if experiment provided)

## 2) Web UI (Netlify-ready)

A polished static UI is included in `web/`:

- Build CLI command from form inputs
- Configure reactor/energy combinations visually
- Upload result CSV files and plot any columns instantly

### Local preview

```bash
python -m http.server 8080 -d web
```

Then open `http://localhost:8080`.

### Deploy on Netlify

This repo includes `netlify.toml` with:

- publish directory: `web`
- `/api/*` redirect to `/.netlify/functions/simulate`

The sample Netlify function currently returns `501` and serves as a backend hook point. You can connect it to an external Python API if you want cloud simulation execution while keeping Netlify for the frontend hosting.
