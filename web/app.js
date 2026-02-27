const commandOut = document.getElementById('commandOut');

document.getElementById('buildCmd').addEventListener('click', () => {
  const mechanism = document.getElementById('mechanism').value.trim();
  const fuel = document.getElementById('fuel').value.trim();
  const oxidizer = document.getElementById('oxidizer').value.trim();
  const phi = document.getElementById('phi').value.trim();
  const temperature = document.getElementById('temperature').value.trim();
  const pressure = document.getElementById('pressure').value.trim();
  const species = document.getElementById('species').value.split(',').map(s => s.trim()).filter(Boolean);
  const reactors = document.getElementById('reactors').value.trim();

  const cmd = [
    'python cantera_reactor_suite.py',
    mechanism,
    `--fuel "${fuel}"`,
    `--oxidizer "${oxidizer}"`,
    `--phi ${phi}`,
    `--temperature ${temperature}`,
    `--pressure ${pressure}`,
    `--reactors ${reactors}`,
    `--species ${species.join(' ')}`,
    '--output-dir outputs'
  ].join(' \\\n  ');

  commandOut.textContent = cmd;
});

let parsedRows = [];
let columns = [];

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines[0].split(',').map(h => h.trim());
  const rows = lines.slice(1).map(line => {
    const cells = line.split(',');
    const row = {};
    headers.forEach((h, i) => row[h] = Number(cells[i]));
    return row;
  });
  return { headers, rows };
}

function loadSelectors(headers) {
  const xSel = document.getElementById('xCol');
  const ySel = document.getElementById('yCol');
  xSel.innerHTML = '';
  ySel.innerHTML = '';
  headers.forEach((h) => {
    const xOpt = document.createElement('option'); xOpt.value = h; xOpt.textContent = h;
    const yOpt = document.createElement('option'); yOpt.value = h; yOpt.textContent = h;
    xSel.appendChild(xOpt); ySel.appendChild(yOpt);
  });
  if (headers.includes('time_s')) xSel.value = 'time_s';
  if (headers.includes('temperature_K')) ySel.value = 'temperature_K';
}

document.getElementById('csvFile').addEventListener('change', async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  const text = await file.text();
  const parsed = parseCSV(text);
  columns = parsed.headers;
  parsedRows = parsed.rows;
  loadSelectors(columns);
});

document.getElementById('plotBtn').addEventListener('click', () => {
  if (!parsedRows.length) return;
  const x = document.getElementById('xCol').value;
  const y = document.getElementById('yCol').value;

  Plotly.newPlot('plot', [{
    x: parsedRows.map(r => r[x]),
    y: parsedRows.map(r => r[y]),
    mode: 'lines+markers',
    line: { color: '#60a5fa' }
  }], {
    paper_bgcolor: '#1e293b',
    plot_bgcolor: '#0b1220',
    font: { color: '#e2e8f0' },
    title: `${y} vs ${x}`,
    xaxis: { title: x },
    yaxis: { title: y }
  }, { responsive: true });
});
