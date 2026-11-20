# Supported JSON Formats

## 1. DeepSeek

The root object contains chat metadata and a `messages` array.
Each message holds a `fragments` array with the following types:

| Fragment type | Purpose                          | In Markdown        |
|---------------|----------------------------------|--------------------|
| `REQUEST`     | User message                     | always             |
| `RESPONSE`    | Assistant reply                  | always             |
| `TOOL_SEARCH` | Search queries and results       | only with option   |
| `READ_LINK`   | Links read by the model          | only with option   |

### Structure example

```json
{
  "id": "e82fc8c4-...",
  "title": "Chat title",
  "inserted_at": "2026-11-17T07:22:59.502Z",
  "updated_at": "2026-11-17T08:34:14.915Z",
  "messages": [
    {
      "role": "USER",
      "inserted_at": "2026-11-17T08:10:10.758Z",
      "fragments": [
        { "type": "REQUEST",  "content": "user question" },
        { "type": "RESPONSE", "content": "assistant reply" }
      ]
    }
  ]
}
```

## 2. Qwen

The root may be a **list** or a dict wrapped as `{"data": [...]}`.
Messages live in `data[0].chat.history.messages` — a **dictionary** keyed by
UUID; the order is restored via the `parentId` → `childrenIds` chain starting
from the root node (`parentId: null`).

Each node contains a `content_list` array with phases:

| Phase              | Purpose                            | In Markdown      |
|--------------------|------------------------------------|------------------|
| `answer`           | Main reply text                    | always           |
| `thinking_summary` | Summarized model reasoning         | only with option |
| `code_interpreter` | Code and interpreter output        | **never**        |

### Structure example

```json
{
  "success": true,
  "data": [
    {
      "id": "c3757c21-...",
      "title": "Chat title",
      "created_at": 1794909502,
      "updated_at": 1794921174,
      "chat": {
        "history": {
          "messages": {
            "<uuid>": {
              "role": "user",
              "content": "message text",
              "parentId": null,
              "childrenIds": ["<uuid-2>"],
              "timestamp": 1794909501
            },
            "<uuid-2>": {
              "role": "assistant",
              "content_list": [
                { "phase": "answer", "content": "reply text" },
                { "phase": "code_interpreter", "extra": { "...": "..." } },
                { "phase": "thinking_summary", "extra": { "summary_thought": { "content": ["..."] } } }
              ],
              "parentId": "<uuid>",
              "childrenIds": []
            }
          }
        }
      }
    }
  ]
}
```

## Notes

- Timestamps: DeepSeek uses ISO-8601 (`inserted_at`),
  Qwen uses Unix timestamps in seconds (`timestamp`, `created_at`).
- Empty phases and phases without text are ignored.
- Technical messages such as `Tool code_interpreter does not exists.`
  never reach the output, even with service blocks enabled.