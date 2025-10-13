> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Release Process & Health Gating

## Release Strategy
- **Blue/Green or Canary:** Deploy new version to a subset of nodes (canary) or parallel environment (blue/green).
- **Health Checks:** Automated health endpoints (`/health`) must return `ok: true` for all services before traffic cutover.
- **Rollback:** If health checks fail, revert to previous version immediately.

## Release Checklist
1. Run full integration and load tests in staging.
2. Deploy to canary/blue environment.
3. Monitor health, metrics, and logs for 30+ minutes.
4. If healthy, cut over all traffic.
5. If issues, rollback and investigate.
6. Document release in changelog and update version.

## Automation
- Use CI/CD pipeline to automate build, test, deploy, and health verification steps.
- Alert on any failed health check or SLO violation during rollout.
