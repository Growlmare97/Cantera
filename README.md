# Cantera Reactor Suite

A toolkit for combustion studies with Cantera YAML mechanisms:

- **Python CLI** for reactor simulation (batch CV/CP, CSTR, PFR-chain)
- **Reactor energy mode control** (`adiabatic` or `isothermal`) per reactor
- **Plots and CSV outputs** for temperature/composition
- **Experimental fit workflow** with RMSE metrics
- **Web UI that can now run simulations** via backend API
- **Netlify-ready frontend** with function proxy support

## 1) Run it locally (step-by-step)

## Step 1 — Install dependencies

```bash
pip install cantera matplotlib numpy pandas fastapi uvicorn
```

## Step 2 — Start the backend API (this executes Cantera)

```bash
uvicorn backend_api:app --host 0.0.0.0 --port 9000
```

Health check:

```bash
curl http://localhost:9000/health
```

## Step 3 — Start the web UI

```bash
python -m http.server 8080 -d web
```

Open `http://localhost:8080`.

## Step 4 — Run simulation from the UI

1. Set **Backend API URL** to `http://localhost:9000`.
2. Fill mechanism/fuel/oxidizer/species/reactors.
3. Click **Run simulation**.
4. Choose reactor + x/y columns.
5. Click **Plot selected reactor**.

The UI now calls `POST /simulate` on the backend and loads results in-browser.

---

## 2) Python CLI usage (direct run)

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

### Reactor energy property

- `adiabatic` → solves energy equation (`energy=on`)
- `isothermal` → keeps temperature fixed (`energy=off`)

Examples:

```bash
--reactors const_volume:isothermal cstr:adiabatic
```

or

```bash
--default-energy isothermal --reactors const_volume const_pressure cstr
```

### Experimental fitting

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

---

## 3) Netlify deployment

`netlify.toml` publishes `web/` and routes `/api/*` to Netlify function `simulate`.

The Netlify function now proxies requests to your Python backend URL set in env var:

- `SIM_BACKEND_URL=https://your-backend.example.com`

So Netlify hosts frontend + proxy, while Cantera execution runs in your Python backend environment.
