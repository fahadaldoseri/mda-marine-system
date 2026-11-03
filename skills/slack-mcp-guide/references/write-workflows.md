# Slack write workflows

Inspect live, full definitions with `mcp tool.get` before actual calls, including tools referenced below.
Use this reference for ordering and pitfalls, not as a substitute for those definitions.
Resolve identifiers from authorized context or lookup results; never copy workspace IDs or session identities from documentation.

## Contents

- [Recipients and conversations](#recipients-and-conversations)
- [Messages, drafts, and schedules](#messages-drafts-and-schedules)
- [Canvas](#canvas)
- [Lists](#lists)
- [File uploads](#file-uploads)
- [Contract caveats](#contract-caveats)

## Recipients and conversations

Resolve channels with `slack_search_channels` and people with `slack_search_users`.
When searching channels, supply the required channel types after inspecting that tool's definition.
Disambiguate matching names before writing; do not guess a recipient.

Message, draft, and scheduling tools accept a resolved user ID as `channel_id` for a DM.
File finalization does not accept user IDs; it needs an actual conversation ID.

Use `slack_create_conversation` only when the user allows creating the missing conversation.
Choose exactly one mode:

- Channel: supply `channel_name`; optionally supply `is_private` and invitee `user_ids`.
- DM: omit `channel_name` and supply one user in `user_ids`.
- Group DM: omit `channel_name` and supply two through eight users; the caller joins automatically.

Channel names use lowercase letters and hyphens, with at most 80 characters.
Channels default to public; do not omit `is_private` when the user requests privacy.
Use the returned `channel_id` for subsequent writes.
If channel invitations fail, ask the user to add members through Slack; no separate invite tool exists.

## Messages, drafts, and schedules

Preview message content, recipients, thread targets, and delivery timing unless the user explicitly requests delivery.
Use a chat preview or `slack_send_message_draft`; drafts are workspace writes, not dry runs.
Do not require blanket reconfirmation for routine writes that the user already authorized.
Apply the stricter file-sharing confirmation rule below.

| Intent | Tool | Important distinction |
| --- | --- | --- |
| Send now | `slack_send_message` | Return the resulting message link. |
| Save for review | `slack_send_message_draft` | Saves an attached draft without sending. |
| Deliver later | `slack_schedule_message` | Requires integer `post_at`. |

All three require `channel_id` and `message`.
Use standard Markdown, not Canvas reference syntax.
Sending limits each text element to 5,000 characters; preserve structural pipes in Markdown tables.
For replies, use the parent's timestamp string as `thread_ts`, not a message URL.
Set `reply_broadcast=true` only when the user wants the reply also posted to the channel.
Sending and scheduling support broadcasts; the draft schema does not.

A channel permits only one attached draft.
On `attached_draft_exists`, ask the user to edit or delete the existing draft; do not silently replace it.
When sending, supply `draft_id` only to delete that specific draft after delivery.
Set `unfurl_app_links=true` when installed-app URLs need rich previews.
Sending and scheduling cannot target externally shared Slack Connect channels.

Convert the intended zoned date-time to integer Unix seconds for `post_at`, never milliseconds.
The schedule contract provides no timezone argument; resolve ambiguous local times and daylight-saving transitions before conversion.
Show the timezone in the preview, and recheck the delivery window immediately before scheduling.
The permitted window starts two minutes ahead and ends 120 days ahead.
Scheduled messages cannot be edited through this API; direct users to Slack's “Drafts and sent” interface.

## Canvas

Choose Canvas for free-form prose; choose Lists for repeated items with shared fields.
`slack_create_canvas` requires separate `title` and `content`; do not repeat the title inside the body.
Canvas creation is unavailable on free teams.
Return the created link or the update's `canvas_url`.

Use Canvas-flavored Markdown, which differs from message formatting:

- Reference resolved users as `![](@<user_id>)` and channels as `![](#<channel_id>)`, replacing placeholders with actual IDs.
- Never substitute channel names or message-style angle-bracket mentions.
- Use ordinary Markdown links, images, tables, and headings through `###` only.
- Format key dates as `![](slack_date:YYYY-MM-DD)` without appended date text.
- Keep code blocks, headings, and block quotes outside list items, separated by blank lines.
- Keep nested lists the same type; use inline formatting within list items.
- Limit layouts to three columns; do not put tables or callouts inside layouts.
- Follow the full contract for callouts, quotes, file embeds, Salesforce references, and supported URL schemes.
- Cite sourced claims inline with `[[N]](url)` links when applicable.

Before updating, call `slack_read_canvas` for Markdown and `section_id_mapping`.
Use a mapping from the current or immediately preceding turn; never fabricate section IDs.
Pass `canvas_id` and a nonempty `sections` array to `slack_update_canvas`.
Each operation needs `edit_type` and a mapped `section_id`; provide nonempty `content` unless deleting.
Use `append`, `prepend`, `replace`, or `delete`; prefer `sections` over legacy single-edit fields.
A batch supports at most 100 operations and applies atomically against one snapshot.
Section IDs remain stable within that batch but change after the update; reread before another batch.

Replace the title section with one line containing at most 255 bytes; put body edits in separate operations.
When renaming headings, include the heading marker.
A whole list or checklist forms one section.
Replacing or deleting a heading does not change its following body; move heading and body together when reordering.
Canvas comment annotation IDs are not mapping keys.
For internal links, use the returned Canvas URL with `focus_section_id=<section_id>`; fragment-only anchors are stripped.

## Lists

Create shared-field trackers with `slack_create_list`, even when the user calls them a document or page.
Creation generates internal column keys; do not derive keys from display names.
The first text column becomes primary; missing text columns cause a primary “Task” column to be added.
Omitting columns creates a single “Name” text column.
Creation allows up to 30 columns and 100 choices per select column.
For select options, prefer `{"choices":[{"label":"Ready","value":"ready"}]}`; preserve returned stored values.

After creation, read the schema with `slack_read_list(schema_only=true)` before schema or record writes.
Prefer exact `list_id`; `list_title` uses fuzzy matching and can select a related list.
If an ID lookup fails, providing both fields permits title fallback; verify which list the tool actually resolved.
Use schema keys for `slack_update_list.columns_to_update` and `columns_to_delete`, never display names.
Only owners and co-owners can change columns.
Inspect every operation result: schema updates can partially succeed without aborting other operations.
Reread the schema after column changes before writing dependent records.

Add rows with `slack_add_list_record`, using the `columns` object.
Edit rows with `slack_update_list_record`, using `record_id` and `updated_columns`.
Get existing record IDs from `slack_read_list`'s “Record ID” column; new records return their ID.
Never substitute a row number, title, or list ID for `record_id`.
Record writes accept exact column keys or ASCII case-insensitive display names.
Use keys when display names collide; mixed keys and display names are allowed.
Only supplied columns change during record updates.
Validate types and select options first; blank/null updates can fail rather than clear a value.
Invalid names or rejected values prevent that record write; correct errors before retrying.
Read at most 100 records per page and pass returned `next_cursor` unchanged when locating additional rows.
Do not retry `feature_not_enabled` or missing-scope errors without a capability change.

## File uploads

Follow this sequence: get signed URL → POST exact bytes → finalize.

1. Prepare the final file and measure its exact byte count; `content_length` must be at least one.
2. Call `slack_get_file_upload_url` with `filename` and that `content_length`.
3. Preserve the returned signed URL byte-for-byte; never decode, re-encode, or reconstruct it.
4. POST raw bytes to that URL with matching `Content-Type` and exact `Content-Length`.
5. Verify POST success before calling `slack_complete_file_upload` with the returned `file_id`.

Use binary-safe transfer, such as `curl --data-binary @<path>`, not JSON, text conversion, or a multipart wrapper.
Store the exact URL in a quoted variable to avoid transcription damage.
Do not change the file between measuring and uploading.
Use `snippet_type` for code and `alt_txt` for image accessibility when applicable.
A 401 can mean URL corruption or expiry, approximately one hour later; request a fresh URL instead of reconstructing it.

Before finalization, confirm the sharing destination and any `initial_comment` with the user, as the tool contract requires.
Never infer a destination; omit `channel_id` only when the user wants no sharing.
For sharing, use an encoded public/private channel, DM, or group DM ID, not a channel name or user ID.
Resolve DM IDs through `slack_list_user_channels` with `types="im"`; use `types="mpim"` for group DMs.
Optionally set `thread_ts` for a reply and `title` to override the filename display.
The file remains inaccessible until finalization, and this flow cannot share it again afterward.
Return the resulting file link; reposting that link does not grant access to new recipients.

## Contract caveats

The draft description mentions scheduling through `slack_send_message`, but that schema has no scheduling argument; use `slack_schedule_message`.
List creation describes option arrays, but its JSON schema types `options` as an object; prefer the supported `choices` wrapper.
Canvas update requires `sections` and mapped targets in prose, although schema-required fields are incomplete; follow the stricter workflow.
Definitions inspected on 2026-11-02; no operational behavior was tested.
