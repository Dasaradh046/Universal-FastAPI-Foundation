/**
 * k6 load test for the Universal FastAPI Foundation API.
 *
 * Run with: k6 run tests/performance/k6_load_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 20 },  // ramp up to 20 users
    { duration: '3m', target: 20 },  // stay at 20 users
    { duration: '1m', target: 0 },   // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests under 500ms
    http_req_failed: ['rate<0.05'],   // error rate under 5%
  },
};

const BASE_URL = 'http://localhost:8000';

export default function () {
  // Health check endpoint
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health status is 200': (r) => r.status === 200,
    'health response time < 200ms': (r) => r.timings.duration < 200,
  });

  sleep(0.5);

  // Root endpoint
  const rootRes = http.get(`${BASE_URL}/`);
  check(rootRes, {
    'root status is 200': (r) => r.status === 200,
  });

  sleep(1);
}
