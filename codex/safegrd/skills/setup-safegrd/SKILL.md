---
name: setup-safegrd
description: Set up SafeGrd for a database, from nothing to a verified backup. Covers signing in, installing the SafeGrd CLI on a host, enrolling the host, the first backup and its restore test, and the local MCP server. Use when the user wants to start protecting a database with SafeGrd. Also adds the experimental guard hook, which takes a locked backup before an agent runs a destructive command, but only when the user asks for it.
---

# Set up SafeGrd

You can take the user from nothing to a backup that has been restored and checked, on the
host you are running on. Four things are the user's own, and you ask for them instead of
doing them: signing in, choosing how the encryption key is managed, paying, and adding a
database that SafeGrd backs up from its own machines. Everything else you run yourself.

Two steps leave something running or configured after this session: the daemon's service
(step 5) and the local MCP server in `~/.codex/config.toml`. Before each one, tell the user what
it writes and where, and go ahead only when they say yes. `safegrd daemon uninstall` removes
the service; the MCP server is one entry to delete.

## The remote server

This plugin connects to `https://safegrd.dev/mcp` by signing the user in: Codex opens
SafeGrd's sign-in page, the user approves for one organization, and the sign-in is listed
under Tokens in the console. If a SafeGrd tool answers `401`, the sign-in was revoked or
expired: ask the user to connect the plugin again. Never ask them for a token in the chat.

## 1. Find out what there is

Call `list_organizations` and `list_surfaces`. If the database the user means is already a
surface with a recent backup and a passed drill, say so and stop: there is nothing to set
up. If the host you are on has the CLI (`safegrd doctor` runs), skip to step 4.

A database with no host of its own (Supabase, Neon, Railway, Render) is backed up from
SafeGrd's machines. Point the user to **Back up on SafeGrd** under Surfaces in the console,
which takes the connection string on SafeGrd's page, never in the chat. Then watch for its
first backup with `list_snapshots` and continue from step 6.

## 2. Install the CLI

Run the installer. In your shell it has no terminal, so it installs the binary and stops
without asking anything:

```sh
curl -fsSL https://safegrd.dev/install.sh | sh
```

It puts `safegrd` in `/usr/local/bin` with sudo, or in `~/.local/bin` without. If the
command is not found afterwards, add `~/.local/bin` to `PATH` for the rest of the session.

## 3. Sign in and enroll the host

Signing in is the user's step. Two ways, and you drive both:

- **A token the user already made** (in `SAFEGRD_TOKEN`, from Tokens in the console):
  `safegrd enroll --token env:SAFEGRD_TOKEN`. Nothing to approve.
- **The browser:** run `safegrd login --no-browser`. It prints a link and a code. Give both to
  the user, tell them to open the link on any device and check that the page shows the same
  code, and wait for the command to finish. Then `safegrd enroll`.

Before `enroll`, ask how the encryption key should be managed. Do not choose for them, and do not
describe either as the weaker choice:

- **SafeGrd-managed key** (the default): SafeGrd keeps the key sealed and releases it only
  to the organization's enrolled hosts, so they can restore even after losing a host.
- **Customer-managed key** (`--key-custody local`): only they can decrypt these backups.
  They keep a copy of the key file somewhere safe.

`enroll` generates the key pair, registers the host and prints its node id. With
`--project <id or slug>` it goes into that project; without, the organization's default.

## 4. Add the database and where backups go

`safegrd init --database-url env:DATABASE_URL` writes the config with the database as its
first surface. Read the URL from the app's environment or `.env`, never type it into the
chat. Storage:

- `--storage hosted`: SafeGrd's locked bucket, on a plan that includes it. Nothing to
  create.
- `--storage s3 --s3-bucket <bucket> --s3-region <region>`: the user's own bucket with
  Object Lock on. The policy and the Terraform for one are at
  `https://safegrd.dev/api/v1/storage/bucket-setup`; the user creates the bucket, you do
  not have the credentials to.

Then `safegrd doctor`. It checks the database account, the client tools (`pg_dump`,
`mysqldump`, `mongodump`) and the storage, and prints what to fix. Fix what you can on the
host; a database account or a bucket is the user's.

## 5. The daemon

`safegrd daemon install` writes a systemd or launchd service that backs up on schedule and
runs Fire Drills. Try it plainly first; if it refuses for want of root, run it with `sudo`
when you can, otherwise `safegrd daemon install --user` for a service that runs at the
user's login. `safegrd daemon status` lists the surfaces it watches and their ids.

## 6. Take the first backup and prove it

`safegrd backup` takes the first backup now. Then prove it restores: `safegrd verify` runs
a Fire Drill of the newest snapshot. Report one fact per line: the surface, the snapshot
id, locked until when, and the drill result. A drill that fails is the thing to fix before
anything else; do not call the setup done.

From a chat without a shell on the host, the same two steps are `request_backup` and
`request_drill`, read back with `list_snapshots` and `list_drills`.

## The local MCP server

On a host with the CLI, the local server backs up, verifies and restores with that host's
config and key. A restore writes only into a new or empty target. Add it to
`~/.codex/config.toml`:

```toml
[mcp_servers.safegrd-local]
command = "safegrd"
args = ["mcp"]
```

## The guard hook (experimental)

Add the hook only when the user asks for it by name or asks for
backups before destructive commands. Do not offer it or add it as part of setup. It goes in
the project's `.codex/hooks.json`; say so and wait for a yes before writing it.

With the hook, Codex takes a locked snapshot before any command that can destroy
data (`DROP`, `TRUNCATE`, `DELETE` without `WHERE`, `dropdb`, `terraform destroy`,
`prisma migrate reset` and others: `safegrd guard --list`). If the snapshot fails or is not
locked, the command is blocked. A command that matches nothing runs with no backup.

A locked snapshot from the last 30 minutes covers a matching command. Without one, the hook
starts a backup and waits up to 20 seconds. If the backup is still running then, the command is
blocked with a message to run it again shortly, and the backup carries on. When you see that
message, wait a minute and run the same command again. It goes through once the snapshot is
locked. After a command goes through, the hook tells you the snapshot id and the restore
command. Pass them on to the user.

It goes in the project, not here, because it names the surface that project works on. Get
the surface id from `safegrd daemon status`, then add this to the project's
`.codex/hooks.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "safegrd guard --hook codex --surface <surface id> || exit 2",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

The `|| exit 2` blocks the command if `safegrd` cannot run at all, for example when it is not
on the `PATH` Codex runs hooks with. Check the hook with
`safegrd guard --matches "DROP TABLE users"`, which takes no backup, and with
`safegrd doctor --agent-proof`, which checks that an agent on this host cannot delete the
backups. Details: https://safegrd.dev/docs/agents.
