exports.handler = async function(event) {
  return {
    statusCode: 501,
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      error: 'Simulation backend not implemented in Netlify Functions.',
      message: 'Run Python Cantera simulations with cantera_reactor_suite.py or connect this function to an external API backend.'
    })
  };
};
