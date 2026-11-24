---
name: jira
description: Jira operations — sprint board, my issues, create/update/close/link issues. Triggers on sprint, issues, create, update, close, link, or any ACM-xxx mention.
allowed-tools: [Bash, Read, Write, Edit, Grep, Glob, WebFetch]
---

# Jira

Bundled scripts for common Jira workflows. Each operation is a single script call.

Set `SKILL_DIR` in the shell to the absolute parent directory of the loaded `SKILL.md`, not the current working directory or a host-provided variable. Invoke the bundled [scripts](scripts/) without changing the working directory.

## sprint — List my current sprint issues

```bash
"$SKILL_DIR/scripts/sprint.sh" [board_id]
```

Outputs a markdown table directly, grouped by status (New -> In Progress -> Closed) with columns: Type, Pri, Key (markdown links), Title, SP, Activity, Components, Versions, Labels. Print the output as-is. Collapse bulk CVE vulnerabilities into a summary row.

## issues — List all my assigned issues

```bash
"$SKILL_DIR/scripts/issues.sh" [extra_jql_filter]
```

Lists all issues assigned to current user, excluding Closed and Backlog by default. Supports optional extra JQL filter (e.g. `"project = ACM"`, `"component = 'Global Hub'"`).

Outputs a markdown table directly, grouped by status (New -> In Progress -> Resolved) with columns: Type, Pri, Key (markdown links), Title, SP, Activity, Components, Versions. Keys prefixed with pin emoji indicate issues in the current active sprint. Print the output as-is. Collapse bulk CVE vulnerabilities into a summary row.

## create — Create a new issue

```bash
"$SKILL_DIR/scripts/create.sh" "<summary>" [type=Task] [priority=Major] [sp=3] [parent=ACM-xxx] [component=Global Hub] [sprint=current] [activity=Product / Portfolio Work]
```

Defaults: project=ACM, component=Global Hub, assignee=current user, type=Task.

**Before creating an issue, always offer the user the Activity Type choices**, using a question tool if available or listing them in chat. Wait for the user to choose or explicitly skip this optional field. Valid values: `Product / Portfolio Work`, `Quality / Stability / Reliability`, `Security & Compliance`, `Incidents & Support`, `Future Sustainability`, `Associate Wellness & Development`.

## update — Update issue fields

```bash
"$SKILL_DIR/scripts/update.sh" <KEY> <field=value> [field=value ...]
```

| Field | Example |
|-------|---------|
| status | `status=Closed` |
| sp | `sp=3` |
| priority | `priority=Major` |
| activity | `activity=Product / Portfolio Work` |
| component | `component=Global Hub` |
| parent | `parent=ACM-30822` |
| sprint | `sprint=current` |
| assignee | `assignee=-1` (-1 = current user) |
| link | `link=https://github.com/.../pull/42` |

All fields run in parallel. Custom field IDs resolved dynamically.

Activity Type values: `Associate Wellness & Development`, `Future Sustainability`, `Incidents & Support`, `Quality / Stability / Reliability`, `Security & Compliance`, `Product / Portfolio Work`

## link — Link issue to URL or set parent

```bash
"$SKILL_DIR/scripts/link.sh" <KEY> <URL_OR_ISSUE_KEY> [custom_title]
```

Auto-detects URL type for title: GitHub PR -> `PR #N - repo`, GitLab MR -> `MR !N - repo`, Google Drive -> `Google Drive`, Blog -> `Blog: slug`. If target is an issue key, sets it as parent instead.

## jira-ops CLI — Direct Jira API operations

The `jira-ops` CLI is bundled at `scripts/jira-ops`. Use it for any operation not covered by the high-level scripts above.

```bash
# Issue operations
"$SKILL_DIR/scripts/jira-ops" issue get <key> [fields]
"$SKILL_DIR/scripts/jira-ops" issue search <jql> [fields] [max]
"$SKILL_DIR/scripts/jira-ops" issue create <json-payload>
"$SKILL_DIR/scripts/jira-ops" issue update <key> <json-payload>
"$SKILL_DIR/scripts/jira-ops" issue delete <key>
"$SKILL_DIR/scripts/jira-ops" issue get-field <key> <field-name>
"$SKILL_DIR/scripts/jira-ops" issue set-field <key> <field-name> <val>
"$SKILL_DIR/scripts/jira-ops" issue transition <key> <status>
"$SKILL_DIR/scripts/jira-ops" issue transitions <key>
"$SKILL_DIR/scripts/jira-ops" issue link <type> <from> <to>
"$SKILL_DIR/scripts/jira-ops" issue comment <key> <text>
"$SKILL_DIR/scripts/jira-ops" issue comment-delete <key> <comment-id>
"$SKILL_DIR/scripts/jira-ops" issue remote-link <key> <url> <title>

# Sprint / Board
"$SKILL_DIR/scripts/jira-ops" board list <project> [max]
"$SKILL_DIR/scripts/jira-ops" sprint list <board-id>
"$SKILL_DIR/scripts/jira-ops" sprint issues <sprint-id> [fields] [max]
"$SKILL_DIR/scripts/jira-ops" sprint move <sprint-id> <keys...>

# Custom field mapping
"$SKILL_DIR/scripts/jira-ops" field discover
"$SKILL_DIR/scripts/jira-ops" field search <pattern>
"$SKILL_DIR/scripts/jira-ops" field get <name>

# Global flag: --json outputs raw JSON
"$SKILL_DIR/scripts/jira-ops" --json issue get ACM-123
```

## jira-ops.sh Library — For custom scripts

Source [scripts/jira-ops.sh](scripts/jira-ops.sh) to use library functions directly. See [references/api-reference.md](references/api-reference.md) for the full function reference (CRUD, search, transitions, ADF builders, sprint operations, URL title detection).

```bash
source "$SKILL_DIR/scripts/jira-ops.sh"
jira_search 'project = ACM AND status = Open'
ISSUE_KEY=$(jira_create_issue "$payload") || exit 1
jira_transition "$ISSUE_KEY" "In Progress"
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_USER` | Yes | Atlassian account email |
| `JIRA_API_TOKEN` | Yes | API token (not password) |
| `JIRA_BASE_URL` | Yes | e.g. `https://your-domain.atlassian.net` |
| `JIRA_AUTH_TYPE` | No | `basic-header` (default), `basic`, `bearer` |

## Key Reminders

- Auth: Basic Auth with API tokens. Default `basic-header` works through corporate proxies
- Description/comments require ADF JSON — use `adf_*` builder functions in library mode
- Epic parent: use `parent` field, not legacy custom fields
- Sprint: cannot be set via REST API PUT — use `jira-ops sprint move` or `jira_move_to_sprint`
- Search: uses `/rest/api/3/search/jql` (GET), not the deprecated POST endpoint
- Custom fields: run `jira-ops field discover` once, then use `jira-ops field get "Story Points"` to look up IDs
