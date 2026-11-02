# Repo Hunter — Design Spec

Date: 2026-11-02
Owner: kietlecocodev
Status: Approved; implemented v0.1.0 (see §10 for changes made during build)

## 1. Mục tiêu

Mỗi ngày lúc 10:00 GMT+7, tự động "đi dạo" GitHub, tìm repo có số sao tăng mạnh trong 1 ngày (≥200 sao), lọc ra repo giúp tăng hiệu suất cho team **product > design > dev**, so sánh với các repo tương tự đã có, rồi ghi suggest vào Notion. Mọi bước của mỗi lần chạy được ghi nhật ký vào Notion.

Ngoài phạm vi (YAGNI): giao diện web riêng, gửi Slack, quét repo của org, tự động cài repo.

## 2. Quyết định đã chốt

| Vấn đề | Quyết định |
|---|---|
| Nơi chạy | Cloud routine của Claude Code (`/schedule`), cron `0 3 * * *` UTC (10:00 GMT+7) |
| Nguồn số sao | Kết hợp A + B: GitHub Trending daily + GitHub Search API, cùng một bảng snapshot để tính số sao tăng thật. OSS Insight là dự phòng |
| Kênh nhận | Notion: trang "Repo Hunter" gồm 2 database `Daily Runs` và `Suggestions` |
| Phạm vi check "đã dùng" | Chỉ account `kietlecocodev`: repo đã star, đã fork, và code search trong repo của account |
| Lưu state | Commit vào chính repo `kietlecocodev/repo-hunter` (thư mục `state/`) |

## 3. Notion

- Trang gốc: "Repo Hunter" (private). ID trang và data source nằm trong `config.json` của repo state private, không nằm ở repo này.
- `Daily Runs`
  - Cột: Run (title, `YYYY-MM-DD`), Date, Status (Success/Partial/Failed/No picks), Trigger (Scheduled/Manual), Source (Trending/Search API/Snapshot delta/OSS Insight), Candidates, Over 200, After filters, Already used, Suggested, Errors, Commit.
  - Phần nội dung trang: nhật ký từng bước (xem §6), ghi lại mọi việc đã làm trong lần chạy.
- `Suggestions`
  - Cột: Repo (title `owner/name`), URL, Date, Run (liên kết tới Daily Runs), Team (Product/Design/Dev), Stars today, Total stars, Score, Re-suggest, Similar repos, Verdict (Nên thử/Theo dõi/Bỏ qua), License, Risk (Thấp/Trung bình/Cao), Summary, Feedback (👍/👎/Đã thử, người dùng tự điền).
  - Phần nội dung trang: mô tả, so sánh với các repo tương tự, điểm mạnh/yếu, 5 lý do nên dùng, 5 lý do không nên dùng, kết luận.

## 4. Cấu trúc repo

```
repo-hunter/
  skills/repo-hunter/SKILL.md      # quy trình cho Claude (chạy tay: /repo-hunter)
  scripts/
    fetch_trending.py              # Nguồn A: parse github.com/trending (daily), all + từng ngôn ngữ
    fetch_search.py                # Nguồn B: GitHub Search API
    fetch_ossinsight.py            # Dự phòng
    snapshot.py                    # ghi state/snapshots/YYYY-MM-DD.json, tính delta
    filter.py                      # ngưỡng, luật lặp, lọc rác
    check_used.py                  # star / fork / code search của kietlecocodev
    pipeline.py                    # chạy 1→5, xuất state/runs/YYYY-MM-DD/candidates.json + log.json
  state/
    snapshots/YYYY-MM-DD.json      # {repo: total_stars}
    watchlist.json                 # repo đang theo dõi (tối đa ~2000, bỏ repo không tăng sau 30 ngày)
    suggested.json                 # lịch sử suggest: ngày, stars_today, notion_page_id, feedback
    weights.json                   # trọng số team, cập nhật từ feedback
    runs/YYYY-MM-DD/               # candidates.json, log.json, report.md (dự phòng khi Notion lỗi)
  config.yaml                      # ngưỡng, ngôn ngữ, blocklist, số repo tối đa
  tests/fixtures/                  # HTML trending mẫu, response API mẫu
  tests/
```

Script viết bằng Python 3.11, chỉ dùng thư viện chuẩn + `requests` + `beautifulsoup4` + `pyyaml`. Phần quyết định (lọc, ngưỡng, luật lặp) nằm trong code có test; Claude chỉ làm phần cần phán đoán (phân loại, so sánh, viết lý do).

## 5. Tính "số sao tăng trong ngày" (A + B)

1. **Nguồn A — Trending**: lấy `https://github.com/trending?since=daily` cho trang "tất cả ngôn ngữ" và các ngôn ngữ trong `config.yaml` (mặc định: python, typescript, javascript, go, rust, swift, kotlin, unknown). Mỗi repo lấy `stars_today` (con số GitHub hiển thị) và tổng số sao.
2. **Nguồn B — Search API**: 2 truy vấn mỗi ngày:
   - `created:>=<hôm nay−30 ngày> stars:>=300 sort:stars` (repo mới tăng nhanh)
   - `pushed:>=<hôm qua> stars:>=1000 sort:updated` (repo cũ đang hoạt động)
   Mỗi truy vấn lấy tối đa 300 kết quả. Repo tìm được sẽ thêm vào `watchlist.json`.
3. **Snapshot**: mỗi ngày ghi tổng số sao của toàn bộ watchlist + repo từ nguồn A. `delta_snapshot = stars(hôm nay) − stars(snapshot gần nhất)`, chia cho số ngày giữa 2 lần nếu snapshot trước cũ hơn 1 ngày.
4. **Số sao tăng trong ngày dùng để xét ngưỡng**:
   - Repo có trong trending → dùng `stars_today` của trending; nếu cũng có snapshot thì ghi cả 2 vào log để đối chiếu.
   - Repo chỉ có trong watchlist → dùng `delta_snapshot`; chỉ hợp lệ khi đã có snapshot từ hôm trước (repo mới vào watchlist phải chờ 1 ngày).
5. **Dự phòng**: nguồn A lỗi hoặc trả 0 repo → gọi OSS Insight trending API (`period=past_24_hours`). Ghi nguồn đã dùng vào cột `Source`.
6. **Ngưỡng**: `stars_today ≥ 200` (đặt trong `config.yaml`).

## 6. Luồng chạy mỗi ngày

Mỗi bước ghi 1 dòng vào `log.json` (thời điểm, bước, số repo vào/ra, ghi chú). Cuối lần chạy, log được ghi vào nội dung trang `Daily Runs`.

1. **Thu thập** — nguồn A + B + snapshot (§5).
2. **Ngưỡng** — giữ repo có `stars_today ≥ 200`.
3. **Lọc rác** — bỏ repo: đã archive; fork; tên/mô tả khớp blocklist (`awesome-`, `tutorial`, `course`, `interview`, `roadmap`, `crypto`, `airdrop`, `game`...); không có license; nghi bơm sao (lấy mẫu 100 stargazer gần nhất, >50% tài khoản tạo <30 ngày, 0 repo public).
4. **Luật lặp** — repo đã có trong `suggested.json`:
   - Trong 14 ngày gần nhất → bỏ, trừ khi `stars_today ≥ 2 ×` lần suggest trước hoặc có release major mới (vX.0.0) sau lần suggest trước → suggest lại, đánh dấu `Re-suggest`.
   - Đã bị đánh 👎 → không bao giờ suggest lại.
5. **Agent check "đã dùng"** (1 subagent) — với mỗi repo còn lại:
   - Có trong danh sách star của `kietlecocodev` → đã dùng.
   - Có fork thuộc `kietlecocodev` → đã dùng.
   - Code search (`user:kietlecocodev "<owner>/<name>"` và tên package) trong `package.json`, `requirements*.txt`, `pyproject.toml`, `go.mod`, `.gitmodules`, `SKILL.md`, `README` → đã integrate.
   - Repo đã dùng → bỏ khỏi danh sách suggest, đếm vào cột `Already used`.
6. **Phân loại & chấm điểm** (Claude) — đọc README, gán Team (Product/Design/Dev) hoặc "Không liên quan" (bỏ). `score = log10(stars_today) × weight_team × fit` với `weight` mặc định product 1.5, design 1.2, dev 1.0, `fit` 0–1 do Claude chấm theo mức hữu ích cho team. Lấy tối đa 6 repo điểm cao nhất.
7. **Agent tìm repo tương tự** (1 subagent mỗi repo, chạy song song) — tìm 2–4 repo cùng chức năng đã có từ trước (GitHub search theo topic/từ khoá, ưu tiên repo >1k sao). So sánh: số sao, mức hoạt động (commit 90 ngày), license, cách cài, tính năng chính. Trả về: điểm mạnh, điểm yếu, 5 lý do nên dùng, 5 lý do không nên dùng, verdict. Mọi nhận định phải có nguồn (link README/release/issue); áp dụng `claim-validator`.
8. **Check an toàn** — license, có cần API key/quyền hệ thống không, commit gần nhất, số maintainer → Risk Thấp/Trung bình/Cao.
9. **Ghi Notion** — tạo trang `Daily Runs` trước, sau đó mỗi repo 1 trang `Suggestions` liên kết về run. Không có repo đạt → Status `No picks`, vẫn ghi đủ số liệu từng bước.
10. **Học từ feedback** — đọc `Suggestions` có Feedback trong 30 ngày: mỗi 👍 tăng weight team đó 0.05, mỗi 👎 giảm 0.05, giới hạn 0.5–2.0. Lưu `weights.json`, đồng bộ Feedback vào `suggested.json`.
11. **Commit state** — commit `state/` với message `chore(state): run YYYY-MM-DD`, push, ghi link commit vào cột `Commit`.

## 7. Xử lý lỗi

| Lỗi | Cách xử lý |
|---|---|
| Trending đổi HTML / bị chặn | Dùng OSS Insight; Status = Partial |
| Search API hết lượt gọi | Bỏ qua nguồn B hôm đó, vẫn chạy với A + snapshot; ghi Errors |
| Không có token GitHub | Chỉ check star/fork qua API công khai; ghi cảnh báo trong Errors |
| Notion lỗi | Ghi `state/runs/YYYY-MM-DD/report.md`, commit; Status lần chạy sau ghi bù |
| Một subagent so sánh lỗi | Vẫn suggest repo đó, phần so sánh ghi "Chưa so sánh được"; Status = Partial |
| Push state lỗi | Thử lại 1 lần; vẫn lỗi thì ghi Errors trên Notion |

Không bao giờ để lần chạy kết thúc mà không có dòng `Daily Runs`.

## 8. Test

- `fetch_trending`: parse file HTML mẫu (có số có dấu phẩy, repo không có ngôn ngữ).
- `fetch_search`: dùng response mẫu, kiểm tra phân trang và xử lý hết lượt gọi.
- `snapshot`: tính delta khi có/không có snapshot trước, khi khoảng cách >1 ngày.
- `filter`: ngưỡng 200, blocklist, luật lặp 14 ngày, luật 2×, luật 👎.
- `check_used`: star/fork/code search với dữ liệu giả.
- Chạy thử toàn bộ bằng tay (`/repo-hunter --dry-run`): không ghi Notion, in kết quả ra màn hình.

## 9. Cần chuẩn bị khi tạo routine

1. Trên claude.ai bật kết nối Notion và cấp quyền cho trang "Repo Hunter" (MCP Notion trên máy không dùng được từ cloud).
2. Tạo GitHub fine-grained PAT, chỉ quyền đọc (metadata, contents, starring), đặt vào biến môi trường `GH_READ_TOKEN` của routine. Không có token thì chỉ check được star/fork.
3. Routine cần quyền push vào `kietlecocodev/repo-hunter` để commit `state/`.

## 10. Thay đổi trong lúc build (2026-11-02)

| Thay đổi | Lý do |
|---|---|
| Repo `repo-hunter` public + là Claude Code marketplace; config, snapshot, lịch sử chuyển sang repo private `repo-hunter-state` | Người dùng muốn public để cài trên máy khác; kết quả code search có thể lộ tên repo private |
| Bỏ OSS Insight làm dự phòng | API trả `data_quality.status: unavailable` từ 2026-03-01. Khi trending lỗi thì dùng số tăng tính từ snapshot của nguồn B |
| Bỏ lấy mẫu stargazer để phát hiện bơm sao; thay bằng dấu hiệu rẻ (tỷ lệ fork/sao < 1%, ≥3000 sao trong ≤14 ngày), chỉ nâng Risk, không loại | Endpoint stargazers trả 401 (không token) / 404 (có token) khi kiểm tra ngày 2026-11-02 |
| Không có license → không loại, nâng Risk lên Cao (`require_license: false`) | Lần chạy thật loại nhầm `anthropics/skills` |
| Code search tách sang lệnh `verify`, chỉ chạy trên danh sách rút gọn sau khi Claude phân loại | Code search giới hạn 10 lần/phút → chạy cho 29 repo mất ~5 phút; giờ `collect` ~85 giây |
| Python chỉ dùng thư viện chuẩn, test bằng `unittest`, config là `config.json` | Chạy được ở mọi máy/cloud không cần cài thêm |
| Trọng số team tính lại từ đầu mỗi lần (config + toàn bộ feedback) thay vì cộng dồn | Chạy lại không bị cộng trùng |
