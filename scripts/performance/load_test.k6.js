import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 10 }, // ramp-up to 10 VUs
    { duration: '2m', target: 10 }, // stay at 10 VUs
    { duration: '30s', target: 0 }, // ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests should be < 500ms
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:9696';

export default function () {
  // Simple health check
  let health = http.get(`${BASE_URL}/health`);
  check(health, { 'health status 200': (r) => r.status === 200 });

  // Example API call – replace with a real endpoint as needed
  let res = http.get(`${BASE_URL}/v1/tenants`);
  check(res, {
    'tenants status 200': (r) => r.status === 200,
    'tenants body not empty': (r) => r.body && r.body.length > 2,
  });

  sleep(1);
}
