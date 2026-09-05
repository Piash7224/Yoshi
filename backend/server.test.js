const test = require('node:test');
const assert = require('node:assert/strict');

test('health endpoint reports database state', async () => {
  const { app } = require('./server');
  const server = app.listen(0);
  try {
    const { port } = server.address();
    const response = await fetch(`http://127.0.0.1:${port}/api/health`);
    const body = await response.json();
    assert.equal(response.status, 200);
    assert.equal(body.status, 'ok');
    assert.equal(body.database, 'disconnected');
  } finally { server.close(); }
});
