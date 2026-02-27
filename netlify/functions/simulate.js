exports.handler = async function(event) {
  const backend = process.env.SIM_BACKEND_URL;

  if (!backend) {
    return {
      statusCode: 500,
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        error: 'SIM_BACKEND_URL is not configured.',
        message: 'Set SIM_BACKEND_URL to your Python backend base URL, e.g. https://your-api.example.com',
      }),
    };
  }

  try {
    const upstream = await fetch(`${backend.replace(/\/$/, '')}/simulate`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: event.body || '{}',
    });

    return {
      statusCode: upstream.status,
      headers: { 'content-type': 'application/json' },
      body: await upstream.text(),
    };
  } catch (error) {
    return {
      statusCode: 502,
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        error: 'Failed to reach simulation backend.',
        detail: String(error),
      }),
    };
  }
};
