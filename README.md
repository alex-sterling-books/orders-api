# orders-api

Companion lab code for *Practical AWS DevOps Agent: A Hands-On Guide to Investigating Incidents and Improving Reliability on AWS* by Alex Sterling.

Northwind and its Orders API are fictional. The code, checks, alarms, and templates are real and run in your own AWS account.

## Before you start

- Use a test account you control, in `us-east-1`.
- Set a budget first: `LIMIT_USD=25 EMAIL=you@example.com make budget`
- Clean up at the end of every session: `make destroy`

The labs create billable AWS resources. You are responsible for any charges.

## Quick start

```bash
make test && make lint
make deploy ALARM_EMAIL=you@example.com
make smoke
```

Appendix A of the book lists every file, script, and command by chapter.

## Secrets

The only secret is the Agent Space webhook signing secret. `scripts/store-webhook.sh` saves it in AWS Systems Manager Parameter Store. Never commit keys. Anything you keep locally belongs in a gitignored `.env` file.

## License

MIT. See `LICENSE`.
