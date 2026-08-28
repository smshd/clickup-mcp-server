# Pip ClickUp comments

## Outbound prefix

All task comments created through this MCP server's `create_task_comment` tool are treated as Pip/Hermes-authored comments and are centrally prefixed before calling ClickUp.

Rendered prefix: `🥑 Pip: `

Implementation detail:
- The avocado is sent as a plain rich-text node: `{ "text": "🥑 " }`.
- `Pip:` is sent as a separate rich-text node with `{ "attributes": { "bold": true } }`.
- The body follows as existing rich-text nodes, or as one plain text node when callers supply `comment_text`.
- The formatter is idempotent: if the visible first nodes already start with `🥑 Pip: `, it does not add another prefix.

Scope:
- Task comments only (`create_task_comment`).
- List comments, threaded replies, updates, task fields/statuses and other ClickUp operations are unchanged.

## Inbound no-seat trigger assessment

ClickUp webhooks support `taskCommentPosted`, but Pip is not a real ClickUp user and cannot be reliably @mentioned without creating a user/seat or changing identity. The safest no-extra-seat trigger for future inbound automation is a narrow text convention on task comments, not a broad automation rule.

Recommended trigger, if/when enabled later:
1. Subscribe only to `taskCommentPosted` and scope the webhook as narrowly as possible, preferably to an internal list or approved workspace area.
2. Trigger only when a non-Pip author posts a task comment whose visible text begins with `@Pip` or `Pip:`.
3. Ignore comments authored by the connected ClickUp user when their visible text begins with `🥑 Pip: `.
4. Store and check ClickUp webhook delivery/event IDs as idempotency keys before acting.
5. Keep actions draft-first or internal-only until John approves the exact write path.

Alternatives assessed:
- Plain-text `@Pip`: readable and easy for humans, but it is not a real ClickUp mention and should be treated as text only.
- `Pip:`: easiest to parse, but more likely to collide with ordinary discussion unless anchored at comment start.
- Assigned-comment convention: useful for human routing, but unreliable for Pip without a real user/seat and risks changing task/comment assignment state.
- Dedicated tag: most reliable for task-level routing after approval, but it mutates task state and is broader than a comment-only trigger.

Material caveat: this task does not enable inbound automation. The recommendation above is design guidance for a later, separately approved narrow route.
