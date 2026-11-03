# Read and search

Apply the core skill's access boundaries. Inspect live tool definitions before calls.

## Contents

- [Resolve channels and users](#resolve-channels-and-users)
- [Build a search](#build-a-search)
- [Read messages and threads](#read-messages-and-threads)
- [Read files](#read-files)
- [Report evidence](#report-evidence)

## Resolve channels and users

Use `slack_list_user_channels` for memberships. Use `slack_search_channels` for channel discovery beyond memberships.

Pass `types` explicitly to `slack_list_user_channels`:

- Use `public_channel` for public-only discovery.
- Add `private_channel` only for the requested private scope.
- Add `im` for DMs or `mpim` for group DMs only when needed.
- Set `exclude_archived=true` when archived channels are irrelevant.

Pass `channel_types` explicitly to `slack_search_channels`. This tool accepts public and private channel types, not DM types.

Provide both `keywords` and `natural_language_query` for channel search. The tool description requires them even when the schema marks neither as required.

Use a returned channel ID in subsequent calls. Disambiguate similar channel names before writing.

Use `team_id` on membership listing when targeting a known workspace in a multi-workspace organization. Do not invent workspace IDs.

Remember these membership-list details:

- Archived channels are included by default.
- The default channel types exclude DMs.
- `name_prefix` is case-insensitive.
- `cursor` is ignored when `name_prefix` is set.
- A returned page does not prove the total channel count.

Use `slack_search_users` for names, emails, or profile attributes. Resolve ambiguous users before sending.

Use `slack_read_user_profile` without `user_id` to inspect the current user when necessary. Avoid copying session-specific identity into reusable instructions.

Use `slack_list_channel_members` for channels and group DMs, not one-to-one DMs.

## Build a search

Use `slack_search_public` for public-message search. Obtain explicit consent before `slack_search_public_and_private`.

Limit private search with `channel_types` and `filters` after obtaining consent. The private-search tool defaults to all conversation types.

Separate query fields:

| Field | Put here | Avoid |
|---|---|---|
| `keywords` | Single words or quoted exact phrases | Recipient, channel, or date constraints |
| `filters` | Slack people, channel, date, or content modifiers | Unstructured questions |
| `natural_language_query` | Conversational meaning | Duplicated filter constraints |

Supply at least one keyword or filter. Use `natural_language_query=""` for filter-only requests.

Treat keyword elements as AND conditions. Quote multiword phrases explicitly.

Use supported modifiers such as `in:<#CHANNEL_ID>`, `from:<@USER_ID>`, `on:YYYY-MM-DD`, `after:YYYY-MM-DD`, and `before:YYYY-MM-DD`.

Use `has:file`, `has:link`, or `is:thread` when appropriate. Inspect current tool guidance before adding unfamiliar modifiers.

Treat repeated modifiers as OR conditions, except `with` and `has`, which use AND conditions.

Use `sort="timestamp"` and `sort_dir="desc"` for latest-first results. Use relevance sorting for topical discovery.

Set `only_my_channels=true` only when membership should constrain results. Do not assume all searches default to joined channels.

Use `include_bots=true` when searching expected bot announcements. Bot messages are excluded by default.

Use `response_format="concise"` for discovery. It omits surrounding context even when `include_context=true`.

Retrieve detailed results or the source thread before interpreting a truncated result. Search limits are currently at most 20 results per page.

### Parameter example

Resolve the channel first. Replace `CHANNEL_ID` with the actual returned value; do not send this placeholder.

```json
{
  "keywords": ["launch"],
  "filters": "in:<#CHANNEL_ID> on:2026-11-02",
  "natural_language_query": "Find launch decisions.",
  "content_types": "messages",
  "sort": "timestamp",
  "limit": 5,
  "response_format": "concise",
  "include_context": false
}
```

Resolve relative dates before building filters. State the assumed timezone or ask when the boundary materially affects results.

If a query returns nothing, simplify keywords within the authorized scope. Never expand into private search without consent.

Report no matches for the query and scope. Do not claim that the information does not exist.

## Read messages and threads

Use `slack_read_channel` with a returned `channel_id`. It returns newest messages first.

Use a requested user's `user_id` as `channel_id` for DM history, as supported by the connector.

Pass `oldest` and `latest` when a specific time window is required. Follow cursors to cover that window.

Use `slack_read_thread` with the parent `message_ts` and `channel_id`. A channel read does not replace thread retrieval.

Keep Slack timestamps as exact decimal strings. Do not convert them through floating-point arithmetic.

Inspect detailed message output when concise output omits IDs, reactions, or thread metadata needed for the next call.

Inspect `slack_get_reactions` before making claims about reactions. Do not treat a reaction alone as a formal approval or task assignment.

## Read files

Find file IDs in search results, channel messages, or threads. Pass the actual file ID to `slack_read_file`.

Inspect the returned MIME type. Expect text directly or base64-encoded binary content.

The current file-read limit is 10 MB. Explain unsupported files rather than claiming they were read.

Use `content_types="messages"` for public-only message tests. Do not assume the public-search tool name guarantees a file's source audience.

Inspect live file-search scope descriptions. Current file fields describe files accessible to the acting user.

Check a file's context and audience before using or redistributing it. Apply private-access and disclosure safeguards when relevant.

## Report evidence

Include returned source links when available. Otherwise include channel, author, and timezone-qualified timestamp.

Label translations, excerpts, and summaries correctly. Preserve the original meaning without exposing unrelated personal data.

Distinguish sampled messages from complete coverage. Report pagination, truncation, bot exclusions, permission gaps, and date assumptions when they affect conclusions.

Use facts from sources for owners and deadlines. Label uncertain conclusions as unverified.
