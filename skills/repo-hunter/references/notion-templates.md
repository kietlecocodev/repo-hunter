# Notion page templates

Notion-flavored Markdown. Do not repeat the title in the body.

## Suggestion page

```markdown
> <Summary — 1–2 câu>

**<stars_today> sao trong ngày** (nguồn: <Trending|Snapshot>) · <stars> sao tổng · <language> · License: <license> · Rủi ro: <Risk>
<if resuggest>Đã suggest trước đó — suggest lại vì: <repeat_reason></if>

## So với các repo tương tự
| Repo | Sao | Push gần nhất | License | Định vị |
|---|---|---|---|---|
| <similar rows> |

### Điểm mạnh
- …
### Điểm yếu
- …

## 5 lý do nên dùng
1. …
## 5 lý do không nên dùng
1. …

## Kết luận: <Verdict>
<verdict_reason>

## Rủi ro
- <risk reasons, farm_signals if any>

<details>
<summary>Nguồn</summary>

- <urls>
</details>
```

## Run page

```markdown
**Trạng thái:** <Status> · **Nguồn:** <sources> · **Trigger:** <Scheduled|Manual>

## Phễu
| Bước | Vào | Ra | Ghi chú |
|---|---|---|---|
| <one row per step in log.json steps + classify + already-used agent + compare> |

## Đã suggest
- <owner/name> — <Team> — <stars_today> sao — <Verdict>

## Bị loại
- Lọc rác: <repo: lý do>
- Luật lặp: <repo: lý do>
- Đã dùng: <repo: lý do>
- Không liên quan / fit thấp: <repo: lý do>

## Nhật ký hành động
- HH:MM — <step> — <result>

## Lỗi
- <errors or "Không có">
```
