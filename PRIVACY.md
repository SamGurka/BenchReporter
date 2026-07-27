# Privacy Policy

Last updated: July 27, 2026

BenchReporter is a Discord bot for fantasy football league updates. This policy explains what information the bot processes and why.

## Information Processed

BenchReporter does not read Discord messages, direct messages, or message content. It is a message-only bot that posts scheduled league and football-news updates.

To operate the bot, the service may process and store:

- Discord bot configuration, including channel IDs and an encrypted bot token.
- Public Sleeper league data used for league updates, such as team display names, roster IDs, player data, matchup results, transactions, and draft records.
- RSS or Atom feed data, including item titles, links, sources, publication dates, and deduplication identifiers.
- Operational records such as post timestamps, error information, and identifiers used to prevent duplicate posts.

BenchReporter does not collect passwords, payment information, direct-message content, or Discord message content.

## How Information Is Used

Information is used only to post scheduled updates, avoid duplicate messages, maintain league history for planned season recaps and awards, and operate or troubleshoot the service.

BenchReporter does not sell personal information or use it for advertising.

## Storage and Retention

The service uses AWS infrastructure, including DynamoDB for bot state and historical league records, SSM Parameter Store for configuration secrets, and CloudWatch for operational logs.

RSS deduplication records are configured to expire after 120 days. League-history records may be retained for the active league season and its end-of-season recap features, unless the service or league integration is removed sooner.

## Third-Party Services

BenchReporter interacts with Discord, Sleeper, AWS, and configured RSS/Atom sources such as RotoWire. Those services handle information under their own terms and privacy policies.

## Data Requests and Contact

For questions, requests to remove league-related records, or privacy concerns, contact Sam at [samagurka@gmail.com](mailto:samagurka@gmail.com).

## Changes

This policy may change as BenchReporter gains features. Material changes will be published in this document with an updated effective date.
