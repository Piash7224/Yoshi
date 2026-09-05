const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://127.0.0.1:8000';

async function aiPost(endpoint, payload) {
  let response;
  try {
    response = await fetch(`${AI_SERVICE_URL}${endpoint}`, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload), signal: AbortSignal.timeout(150000),
    });
  } catch (error) {
    throw Object.assign(new Error(`AI service unavailable: ${error.message}`), { status: 503 });
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw Object.assign(new Error(data.detail || `AI service returned ${response.status}`), { status: response.status });
  return data;
}

module.exports = { aiPost };
