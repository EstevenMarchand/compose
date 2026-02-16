const request = require('supertest');
const app = require('./app');

test('Debe responder con Hola Docker', async () => {
  const response = await request(app).get('/');
  expect(response.text).toBe('Hola Docker');
});
