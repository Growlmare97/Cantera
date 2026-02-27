#!/usr/bin/env python3
"""HTTP API for running Cantera reactor simulations.

Run locally:
    pip install fastapi uvicorn cantera matplotlib numpy pandas
    uvicorn backend_api:app --host 0.0.0.0 --port 9000
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from cantera_reactor_suite import (
    SimulationConfig,
    compare_experiment,
    parse_reactor_specs,
    plot_results,
    run_requested_reactors,
)


class SimulationRequest(BaseModel):
    mechanism: str = "gri30.yaml"
    fuel: str = "CH4:1.0"
    oxidizer: str = "O2:1.0, N2:3.76"
    phi: float = 1.0
    temperature: float = 1000.0
    pressure: float = 101325.0
    reactors: list[str] = Field(default_factory=lambda: [
        "const_volume:adiabatic",
        "const_pressure:adiabatic",
        "cstr:isothermal",
        "pfr_chain:adiabatic",
    ])
    default_energy: str = "adiabatic"
    end_time: float = 0.02
    points: int = 300
    species: list[str] = Field(default_factory=lambda: ["CH4", "O2", "CO2", "H2O", "CO"])
    cstr_residence_time: float = 0.1
    cstr_volume: float = 1e-3
    pfr_segments: int = 100
    pfr_length: float = 1.0
    pfr_velocity: float = 0.5
    experiment_csv_text: str | None = None
    experiment_x_column: str = "time_s"


app = FastAPI(title="Cantera Reactor Suite API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/simulate")
def simulate(payload: SimulationRequest) -> dict[str, Any]:
    try:
        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            config = SimulationConfig(
                mechanism=payload.mechanism,
                fuel=payload.fuel,
                oxidizer=payload.oxidizer,
                phi=payload.phi,
                temperature=payload.temperature,
                pressure=payload.pressure,
                reactors=parse_reactor_specs(payload.reactors, payload.default_energy),
                end_time=payload.end_time,
                points=payload.points,
                species=tuple(payload.species),
                cstr_residence_time=payload.cstr_residence_time,
                cstr_volume=payload.cstr_volume,
                pfr_segments=payload.pfr_segments,
                pfr_length=payload.pfr_length,
                pfr_velocity=payload.pfr_velocity,
                output_dir=output_dir,
            )

            results = run_requested_reactors(config)
            plot_results(results, output_dir)

            fit_metrics = []
            if payload.experiment_csv_text:
                exp_csv_path = output_dir / "experiment.csv"
                exp_csv_path.write_text(payload.experiment_csv_text)
                metrics = compare_experiment(
                    results=results,
                    experiment_csv=exp_csv_path,
                    output_dir=output_dir,
                    x_column=payload.experiment_x_column,
                )
                fit_metrics = metrics.to_dict(orient="records")

            return {
                "results": [
                    {
                        "reactor": result.reactor_label,
                        "rows": result.frame.to_dict(orient="records"),
                    }
                    for result in results
                ],
                "fit_metrics": fit_metrics,
                "artifacts": {
                    "temperature_plot": "temperature_profiles.png",
                    "species_plot": "species_profiles.png",
                },
            }
    except Exception as exc:  # convert runtime errors to API errors
        raise HTTPException(status_code=400, detail=str(exc)) from exc
