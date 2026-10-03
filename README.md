# SafeGrd agent plugins

Plugins that connect AI coding agents to [SafeGrd](https://safegrd.dev). SafeGrd backs up
PostgreSQL, MySQL, MongoDB and SQLite databases, file trees and IMAP mailboxes. Each backup is
encrypted with age before it leaves the host and locked with S3 Object Lock. A Fire Drill
restores it on a schedule to prove it works.

## Claude Code

```text
/plugin marketplace add safegrd/agent-plugins
/plugin install safegrd@safegrd
```

The plugin asks for a personal access token. Create one in the SafeGrd console under
**Tokens** (it starts with `sg_pat_`). To change it later, run `claude plugin configure safegrd`.

With the token, Claude Code can read your organizations, projects, surfaces, snapshots and
Fire Drills. It can also ask for a backup or a drill now. It cannot delete, disable, re-route
or re-key a backup: the server refuses those to a personal access token on every route. The
remote server's tools are listed at
[safegrd.dev/docs/mcp](https://safegrd.dev/docs/mcp).

### Skills

| Skill | What it does |
| :--- | :--- |
| `backup-before-risky-change` | Before a migration, a schema change or a bulk delete, it takes a locked backup, runs a Fire Drill on it, and says whether it is safe to proceed |
| `check-backups` | Reports late backups, failed drills, surfaces never restored, and hosted storage use |
| `setup-safegrd` | Covers installing the CLI on a host, the local MCP server and the guard hook |

### On a host with the SafeGrd CLI

The local server backs up, verifies and restores with that host's config and key. A restore
writes only into a new or empty target.

```sh
claude mcp add safegrd-local -- safegrd mcp
```

The guard hook takes a locked snapshot before a command that can destroy data, such as
`DROP TABLE` or `prisma migrate reset`, and blocks the command if the snapshot fails. It
names the surface a project works on, so it goes in that project's `.claude/settings.json`,
not in this plugin. The `setup-safegrd` skill adds it, and
[safegrd.dev/docs/agents](https://safegrd.dev/docs/agents) has the recipe for Claude Code,
Cursor and Codex.

## Checks

`.github/workflows/check.yml` validates the marketplace and each plugin with
`claude plugin validate --strict`. It also checks that every tool a skill names is served by
the remote server, read from its public
[server card](https://safegrd.dev/.well-known/mcp/server-card.json). The check runs on
every change and daily.

## Licence

MIT. See [LICENSE](LICENSE). The SafeGrd CLI is in
[safegrd/cli](https://github.com/safegrd/cli).
