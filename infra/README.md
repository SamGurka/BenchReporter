# AWS Infrastructure

This SAM stack creates the shared DynamoDB state table plus all four production Lambdas (RSS news, standout free agents, weekly roundup, and trade watch), their EventBridge Scheduler jobs, and per-function CloudWatch failure alarms.

The table uses a composite `pk`/`sk` key, on-demand billing, encryption at rest, point-in-time recovery, and a `ttl` attribute for expiring dedupe records.

## First Deployment

Prerequisites:

- AWS CLI authenticated to the account that will own the bot
- AWS SAM CLI installed

Copy the tracked example to your ignored local configuration file, then choose a region and stack name:

```powershell
Copy-Item infra\samconfig.example.toml infra\samconfig.toml
```

Build a deployable Lambda artifact from `pyproject.toml`, then deploy:

```powershell
sam build --template-file infra\template.yaml
sam deploy --config-file infra\samconfig.toml
```

The stack output `BotStateTableName` is the value Lambda functions receive through `DYNAMODB_TABLE_NAME`. The RSS function is configured to poll Rotowire's NFL feed by default.

## Planned Parameter Store Paths

The RSS deployment will read these values from SSM Parameter Store rather than source control:

```text
/benchreporter/dev/discord-bot-token
/benchreporter/dev/discord-channel-espn-news-feed
/benchreporter/dev/discord-channel-standout-free-agents
/benchreporter/dev/discord-channel-last-week-tldr
/benchreporter/dev/discord-channel-trade-block
/benchreporter/dev/sleeper-league-id
```

`discord-bot-token` should be a `SecureString`. The channel ID may be an ordinary `String` parameter. Create both before deployment:

```powershell
aws ssm put-parameter --name /benchreporter/dev/discord-bot-token --type SecureString --value '<bot-token>' --overwrite
aws ssm put-parameter --name /benchreporter/dev/discord-channel-espn-news-feed --type String --value '<channel-id>' --overwrite
aws ssm put-parameter --name /benchreporter/dev/discord-channel-standout-free-agents --type String --value '<channel-id>' --overwrite
aws ssm put-parameter --name /benchreporter/dev/discord-channel-last-week-tldr --type String --value '<channel-id>' --overwrite
aws ssm put-parameter --name /benchreporter/dev/discord-channel-trade-block --type String --value '<channel-id>' --overwrite
aws ssm put-parameter --name /benchreporter/dev/sleeper-league-id --type String --value '1385331497866625024' --overwrite
```

The Lambda reads these parameters at invocation time. The bot token is not stored in the template or Lambda environment variables.

The weekly roundup runs Tuesday at 8:00 AM and standout-free-agents runs Tuesday at 9:00 AM, both America/Chicago and both targeting Sleeper's completed week. Trade watch polls every 15 minutes but its deployed handler exits outside the regular season. Each Lambda surfaces invocation or Discord delivery failures as a Lambda error, which drives its CloudWatch alarm. Alarms intentionally have no notification action in the template; attach an approved SNS/PagerDuty destination at deployment time if alert delivery is required.
