> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Release Process & Health Gating

## Release Strategy
- Prefer blue/green or canary rollouts to scope blast radius.
- Block cutover until `/health` reports `ok: true` and `ready: true` for all services.
- Roll back immediately if health checks regress.

## Release Checklist
+ Run full integration and load tests in staging.
+ Deploy to the canary or blue environment.
+ Monitor health, metrics, and logs for at least 30 minutes.
+ If healthy, route all traffic to the new release.
+ If issues arise, rollback and investigate.
+ Document release outcomes in the changelog and bump versions.

## Automation
- CI/CD pipeline should build, test, deploy, and verify health automatically.
- Configure alerts for failed health checks or SLO violations during rollout.
