# AWS Infrastructure

This SAM stack creates the shared DynamoDB state table, the RSS news-feed Lambda, and its 15-minute EventBridge Scheduler job.

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
```

`discord-bot-token` should be a `SecureString`. The channel ID may be an ordinary `String` parameter. Create both before deployment:

```powershell
aws ssm put-parameter --name /benchreporter/dev/discord-bot-token --type SecureString --value '<bot-token>' --overwrite
aws ssm put-parameter --name /benchreporter/dev/discord-channel-espn-news-feed --type String --value '<channel-id>' --overwrite
```

The Lambda reads these parameters at invocation time. The bot token is not stored in the template or Lambda environment variables.
