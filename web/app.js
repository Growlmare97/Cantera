const commandOut = document.getElementById('commandOut');
const statusOut = document.getElementById('statusOut');
const reactorSelect = document.getElementById('reactorSelect');
const xSel = document.getElementById('xCol');
const ySel = document.getElementById('yCol');

let resultMap = new Map();

function getInputs() {
  return {
    apiBase: document.getElementById('apiBase').value.trim(),
    mechanism: document.getElementById('mechanism').value.trim(),
    fuel: document.getElementById('fuel').value.trim(),
    oxidizer: document.getElementById('oxidizer').value.trim(),
    phi: Number(document.getElementById('phi').value),
    temperature: Number(document.getElementById('temperature').value),
    pressure: Number(document.getElementById('pressure').value),
    species: document.getElementById('species').value.split(',').map(s => s.trim()).filter(Boolean),
    reactors: document.getElementById('reactors').value.trim().split(/\s+/).filter(Boolean),
  };
}

function setStatus(message) {
  statusOut.textContent = `Status: ${message}`;
}

function buildCliCommand(inputs) {
  return [
    'python cantera_reactor_suite.py',
    inputs.mechanism,
    `--fuel "${inputs.fuel}"`,
    `--oxidizer "${inputs.oxidizer}"`,
    `--phi ${inputs.phi}`,
    `--temperature ${inputs.temperature}`,
    `--pressure ${inputs.pressure}`,
    `--reactors ${inputs.reactors.join(' ')}`,
    `--species ${inputs.species.join(' ')}`,
    '--output-dir outputs'
  ].join(' \\\n  ');
}

function loadSelectorsForRows(rows) {
  const columns = rows.length ? Object.keys(rows[0]) : [];
  xSel.innerHTML = '';
  ySel.innerHTML = '';

  columns.forEach((c) => {
    const xOpt = document.createElement('option');
    xOpt.value = c;
    xOpt.textContent = c;
    xSel.appendChild(xOpt);

    const yOpt = document.createElement('option');
    yOpt.value = c;
    yOpt.textContent = c;
    ySel.appendChild(yOpt);
  });

  if (columns.includes('time_s')) xSel.value = 'time_s';
  if (columns.includes('distance_m')) xSel.value = 'distance_m';
  if (columns.includes('temperature_K')) ySel.value = 'temperature_K';
}

function populateReactors(results) {
  reactorSelect.innerHTML = '';
  resultMap = new Map(results.map(r => [r.reactor, r.rows]));
  results.forEach((r) => {
    const opt = document.createElement('option');
    opt.value = r.reactor;
    opt.textContent = r.reactor;
    reactorSelect.appendChild(opt);
  });
  if (results.length) {
    loadSelectorsForRows(results[0].rows);
  }
}

document.getElementById('buildCmd').addEventListener('click', () => {
  const inputs = getInputs();
  commandOut.textContent = buildCliCommand(inputs);
});

reactorSelect.addEventListener('change', () => {
  const rows = resultMap.get(reactorSelect.value) || [];
  loadSelectorsForRows(rows);
});

document.getElementById('runSim').addEventListener('click', async () => {
  const inputs = getInputs();
  commandOut.textContent = buildCliCommand(inputs);
  setStatus('running...');

  const payload = {
    mechanism: inputs.mechanism,
    fuel: inputs.fuel,
    oxidizer: inputs.oxidizer,
    phi: inputs.phi,
    temperature: inputs.temperature,
    pressure: inputs.pressure,
    species: inputs.species,
    reactors: inputs.reactors,
  };

  try {
    const response = await fetch(`${inputs.apiBase}/simulate`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Simulation failed');
    }

    populateReactors(data.results || []);
    setStatus(`completed (${(data.results || []).length} reactor result sets)`);
  } catch (err) {
    setStatus(`error: ${err.message}`);
  }
});

document.getElementById('plotBtn').addEventListener('click', () => {
  const rows = resultMap.get(reactorSelect.value) || [];
  if (!rows.length) {
    setStatus('no simulation results to plot');
    return;
  }

  const x = xSel.value;
  const y = ySel.value;
  Plotly.newPlot('plot', [{
    x: rows.map(r => r[x]),
    y: rows.map(r => r[y]),
    mode: 'lines',
    line: { color: '#60a5fa' },
    name: reactorSelect.value,
  }], {
    paper_bgcolor: '#1e293b',
    plot_bgcolor: '#0b1220',
    font: { color: '#e2e8f0' },
    title: `${reactorSelect.value}: ${y} vs ${x}`,
    xaxis: { title: x },
    yaxis: { title: y },
  }, { responsive: true });
});
