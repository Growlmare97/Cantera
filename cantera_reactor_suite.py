#!/usr/bin/env python3
"""Run common Cantera combustion reactor models and plot results.

Features:
- Loads Cantera YAML mechanism files
- Simulates several reactor types (batch CV/CP, CSTR, PFR approximation)
- Plots temperature and species composition trajectories
- Compares simulation output against experimental data from CSV
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cantera as ct
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


@dataclass
class SimulationConfig:
    mechanism: str
    fuel: str
    oxidizer: str
    phi: float
    temperature: float
    pressure: float
    reactor_types: tuple[str, ...]
    end_time: float
    points: int
    species: tuple[str, ...]
    cstr_residence_time: float
    cstr_volume: float
    pfr_segments: int
    pfr_length: float
    pfr_velocity: float
    output_dir: Path


@dataclass
class ReactorResult:
    reactor_type: str
    frame: pd.DataFrame


def build_gas(config: SimulationConfig) -> ct.Solution:
    gas = ct.Solution(config.mechanism)
    gas.set_equivalence_ratio(config.phi, fuel=config.fuel, oxidizer=config.oxidizer)
    gas.TP = config.temperature, config.pressure
    return gas


def run_const_volume_batch(config: SimulationConfig) -> ReactorResult:
    gas = build_gas(config)
    reactor = ct.IdealGasReactor(gas, energy="on")
    network = ct.ReactorNet([reactor])

    times = np.linspace(0.0, config.end_time, config.points)
    rows = []
    for time_s in times:
        network.advance(time_s)
        rows.append(extract_state(time_s, reactor.thermo, config.species))

    return ReactorResult("const_volume", pd.DataFrame(rows))


def run_const_pressure_batch(config: SimulationConfig) -> ReactorResult:
    gas = build_gas(config)
    reactor = ct.IdealGasConstPressureReactor(gas, energy="on")
    network = ct.ReactorNet([reactor])

    times = np.linspace(0.0, config.end_time, config.points)
    rows = []
    for time_s in times:
        network.advance(time_s)
        rows.append(extract_state(time_s, reactor.thermo, config.species))

    return ReactorResult("const_pressure", pd.DataFrame(rows))


def run_cstr(config: SimulationConfig) -> ReactorResult:
    feed = build_gas(config)
    reactor_gas = build_gas(config)

    tank = ct.Reservoir(feed)
    env = ct.Reservoir(reactor_gas)
    reactor = ct.IdealGasReactor(reactor_gas, volume=config.cstr_volume, energy="on")

    mdot = reactor.mass / config.cstr_residence_time
    ct.MassFlowController(tank, reactor, mdot=mdot)
    ct.PressureController(reactor, env, primary=None, K=1e-5)
    network = ct.ReactorNet([reactor])

    times = np.linspace(0.0, config.end_time, config.points)
    rows = []
    for time_s in times:
        network.advance(time_s)
        rows.append(extract_state(time_s, reactor.thermo, config.species))

    return ReactorResult("cstr", pd.DataFrame(rows))


def run_pfr_chain(config: SimulationConfig) -> ReactorResult:
    base = build_gas(config)

    dz = config.pfr_length / config.pfr_segments
    segment_time = dz / max(config.pfr_velocity, 1e-12)

    rows = []
    cumulative_time = 0.0
    for segment in range(config.pfr_segments + 1):
        rows.append(extract_state(cumulative_time, base, config.species) | {"distance_m": segment * dz})

        reactor = ct.IdealGasReactor(base, energy="on")
        network = ct.ReactorNet([reactor])
        network.advance(segment_time)
        base = reactor.thermo
        cumulative_time += segment_time

    return ReactorResult("pfr_chain", pd.DataFrame(rows))


def extract_state(time_s: float, gas: ct.Solution, species: Iterable[str]) -> dict[str, float]:
    state = {
        "time_s": time_s,
        "temperature_K": gas.T,
        "pressure_Pa": gas.P,
    }
    for name in species:
        if name not in gas.species_names:
            raise ValueError(f"Requested species '{name}' is not present in the mechanism")
        state[f"X_{name}"] = gas[name].X[0]
    return state


def run_requested_reactors(config: SimulationConfig) -> list[ReactorResult]:
    runners = {
        "const_volume": run_const_volume_batch,
        "const_pressure": run_const_pressure_batch,
        "cstr": run_cstr,
        "pfr_chain": run_pfr_chain,
    }

    results = []
    for reactor_type in config.reactor_types:
        if reactor_type not in runners:
            raise ValueError(f"Unknown reactor type '{reactor_type}'")
        results.append(runners[reactor_type](config))
    return results


def plot_results(results: list[ReactorResult], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    fig_t, ax_t = plt.subplots(figsize=(10, 6))
    fig_x, ax_x = plt.subplots(figsize=(10, 6))

    for result in results:
        frame = result.frame
        x_axis = frame["distance_m"] if "distance_m" in frame else frame["time_s"]
        x_label = "Distance (m)" if "distance_m" in frame else "Time (s)"

        ax_t.plot(x_axis, frame["temperature_K"], label=result.reactor_type)

        for col in [c for c in frame.columns if c.startswith("X_")]:
            ax_x.plot(x_axis, frame[col], label=f"{result.reactor_type}:{col}")

        result.frame.to_csv(output_dir / f"{result.reactor_type}_results.csv", index=False)

    ax_t.set_xlabel(x_label)
    ax_t.set_ylabel("Temperature (K)")
    ax_t.set_title("Temperature profile")
    ax_t.legend()
    ax_t.grid(True, alpha=0.3)
    fig_t.tight_layout()
    fig_t.savefig(output_dir / "temperature_profiles.png", dpi=150)

    ax_x.set_xlabel(x_label)
    ax_x.set_ylabel("Mole fraction")
    ax_x.set_title("Species composition profiles")
    ax_x.legend(ncol=2, fontsize=8)
    ax_x.grid(True, alpha=0.3)
    fig_x.tight_layout()
    fig_x.savefig(output_dir / "species_profiles.png", dpi=150)

    plt.close(fig_t)
    plt.close(fig_x)


def compare_experiment(
    results: list[ReactorResult],
    experiment_csv: Path,
    output_dir: Path,
    x_column: str,
) -> pd.DataFrame:
    exp = pd.read_csv(experiment_csv)
    if x_column not in exp.columns:
        raise ValueError(f"Experimental file must contain x-column '{x_column}'")

    rows = []
    for result in results:
        sim = result.frame.copy()
        sim_x = "distance_m" if "distance_m" in sim.columns else "time_s"

        common_columns = [
            col for col in exp.columns if col in sim.columns and col not in {x_column, sim_x}
        ]
        if not common_columns:
            continue

        sim_interp = {x_column: exp[x_column].values}
        for col in common_columns:
            sim_interp[col] = np.interp(exp[x_column].values, sim[sim_x].values, sim[col].values)

        sim_interp_df = pd.DataFrame(sim_interp)

        for col in common_columns:
            rmse = np.sqrt(np.mean((exp[col].values - sim_interp_df[col].values) ** 2))
            rows.append(
                {
                    "reactor_type": result.reactor_type,
                    "observable": col,
                    "rmse": rmse,
                }
            )

    metrics = pd.DataFrame(rows)
    metrics.to_csv(output_dir / "experiment_fit_metrics.csv", index=False)
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mechanism", help="Path to Cantera YAML mechanism file")
    parser.add_argument("--fuel", default="CH4:1.0", help="Fuel composition")
    parser.add_argument("--oxidizer", default="O2:1.0, N2:3.76", help="Oxidizer composition")
    parser.add_argument("--phi", type=float, default=1.0, help="Equivalence ratio")
    parser.add_argument("--temperature", type=float, default=1000.0, help="Initial temperature (K)")
    parser.add_argument("--pressure", type=float, default=ct.one_atm, help="Initial pressure (Pa)")
    parser.add_argument(
        "--reactors",
        nargs="+",
        default=["const_volume", "const_pressure", "cstr", "pfr_chain"],
        choices=["const_volume", "const_pressure", "cstr", "pfr_chain"],
        help="Reactor models to run",
    )
    parser.add_argument("--end-time", type=float, default=0.02, help="Final simulation time (s)")
    parser.add_argument("--points", type=int, default=300, help="Number of output points")
    parser.add_argument(
        "--species",
        nargs="+",
        default=["CH4", "O2", "CO2", "H2O", "CO"],
        help="Species to store and plot",
    )
    parser.add_argument("--cstr-residence-time", type=float, default=0.1, help="CSTR residence time (s)")
    parser.add_argument("--cstr-volume", type=float, default=1e-3, help="CSTR reactor volume (m^3)")
    parser.add_argument("--pfr-segments", type=int, default=100, help="Number of PFR chain segments")
    parser.add_argument("--pfr-length", type=float, default=1.0, help="PFR length (m)")
    parser.add_argument("--pfr-velocity", type=float, default=0.5, help="PFR axial velocity (m/s)")
    parser.add_argument("--output-dir", default="outputs", help="Output directory")
    parser.add_argument("--experiment-csv", help="Experimental CSV data for mechanism fit")
    parser.add_argument(
        "--experiment-x-column",
        default="time_s",
        help="x-axis column in experimental data (e.g., time_s or distance_m)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SimulationConfig(
        mechanism=args.mechanism,
        fuel=args.fuel,
        oxidizer=args.oxidizer,
        phi=args.phi,
        temperature=args.temperature,
        pressure=args.pressure,
        reactor_types=tuple(args.reactors),
        end_time=args.end_time,
        points=args.points,
        species=tuple(args.species),
        cstr_residence_time=args.cstr_residence_time,
        cstr_volume=args.cstr_volume,
        pfr_segments=args.pfr_segments,
        pfr_length=args.pfr_length,
        pfr_velocity=args.pfr_velocity,
        output_dir=Path(args.output_dir),
    )

    results = run_requested_reactors(config)
    plot_results(results, config.output_dir)

    if args.experiment_csv:
        metrics = compare_experiment(
            results=results,
            experiment_csv=Path(args.experiment_csv),
            output_dir=config.output_dir,
            x_column=args.experiment_x_column,
        )
        if metrics.empty:
            print("No overlapping columns between simulation and experimental data.")
        else:
            print("Mechanism fit metrics (RMSE):")
            print(metrics.sort_values(["observable", "reactor_type"]).to_string(index=False))

    print(f"Results stored in {config.output_dir}")


if __name__ == "__main__":
    main()
