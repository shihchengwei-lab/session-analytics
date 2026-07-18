# session-analytics

[English](README.md) · **繁體中文**

一個 [Agent Skill](https://agentskills.io)，讓 AI coding agent 持續改進你們的協作方式——定位是**自我優化的 harness 技能**：每個 agent 分析**自己這套工具**最近 7 天的本地 session 紀錄，把你真正在用的路徑加粗、沒在用的剪枝，並在模型更換後重新驗證自己過去給的建議——讓整套設定持續進步，而不是越堆越多。只讀本機資料、不上傳任何東西；分析樣本會經過你的 agent 的模型 context——跟你平常使用該 agent 的每一場對話是同一個信任邊界。

為什麼是 7 天：拉長到一個月的全景會混入早已被修正的舊行為；滾動一週讓訊號聚焦在*現在的你*。隨時都能跑——一個自然的節奏是在每週用量重置前，拿剩餘額度跑一次回顧。

## 兩種模式

- **查詢**：「這週哪些 session 失敗了？」「我的成功率？」「比較我的實驗跑次」——或不帶問題直接呼叫，得到一頁式週總覽，結尾附有憑有據的建議。
- **週回顧**：總覽之外，在三條戰線上提出證據綁定的改動：
  - **規則區塊**：維護在工具設定檔（`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`）裡，硬上限 10 條單行規則，每條帶著證據與日期；每週整塊重新推導——留任／改寫（規則在了、摩擦還是發生）／合併（重疊）／退役（連續兩週乾淨＝畢業）——所以它會自我重構而不是堆積。模型更換會讓舊證據貶值：只在前一個模型下確認過的規則要重新驗證，不自動留任
  - **機制優於文字規則**：hook、環境變數、權限設定能機械化解決的摩擦，就提設定檔 diff、不再多寫一條規則；機制上線後，被它取代的文字規則同一輪退役
  - **Skill 衛生，雙向進行**：把已安裝的 skill 對照實際呼叫次數（模型主動呼叫與使用者手打都算）。熱路徑得到去摩擦提案（更利的觸發描述、權限 allowlist）；從沒被呼叫的列為停用候選——並有防誤判保護：新裝的不判、ambient 型 plugin（statusline、hook、MCP）的價值不長在呼叫次數上，不用次數判它們
  - agent 會展示完整 diff，**你核准之後才寫入**；標記範圍外的內容永遠不碰

## 報告長什麼樣

來自一次真實跑次（專案名已通用化）：

```
Window: 2026-07-11 → 2026-07-18 · thin sample: 5 sessions, 3 with quality assessments
  (raw logs show 10 sessions in this window — /insights artifacts lag; re-run /insights for full coverage)
Outcomes (assessed only): 2 fully_achieved · 1 mostly_achieved
Top frictions: wrong_approach ×4 · buggy_code ×1 · excessive_changes ×1
Volume: ~100 h open-session span (not active time) · 855k output tokens
        top projects: game-project, dotfiles, guardrails-lab
Notable: no failed or stalled session in the assessed set this week
Suggestions:
  1. All 4 wrong_approach marks sit in game-project (07-11 + 07-15 — both sessions still landed):
     the agent gets there after rework. Try opening those sessions with a one-line goal +
     constraints statement; check next week whether the count drops.
  2. Thin sample (5 sessions) — widen the window or re-run /insights before reading trends.
```

（報告本文以 agent 的工作語言輸出；此處保留實際樣貌。重點特徵：樣本太薄會先自首、涵蓋範圍先講、每條建議都綁著它的證據。）

## 各工具資料來源

| 工具 | 來源 | 成本 |
|---|---|---|
| Claude Code（品質資料） | `~/.claude/usage-data`（需先跑過 `/insights`） | 預先算好——讀取不花分析成本 |
| Claude Code（機械資料） | `~/.claude/projects` 原始紀錄，內附抽取器——零設定、隨時最新、含每個 skill 的呼叫次數 | 只取 metadata＋樣本 |
| OpenAI Codex | `~/.codex/sessions/**.jsonl`，內附抽取器 | 只取 metadata＋樣本 |
| 其他工具 | 照 `references/generic.md` 的程序 | 取決於有什麼紀錄 |

## 前置需求

- agent 執行環境要有 Python 3
- Claude Code：成敗／摩擦評估需要至少跑過一次 `/insights`；純機械資料零設定即可用。Codex：要有既存的 session 紀錄

## 不做的事（Non-goals）

內附的資料層是刻意做到最小的零依賴備援，不是產品。這個 skill 不會再長出：新的 agent parser、session 資料庫或搜尋索引、dashboard／UI、token 成本試算。成熟的本地工具已經把這些做得很好（見下）；這個 skill 真正的工作是決策層——把 session 證據轉成少量、有界、可撤銷、經你核准的 harness 改動。

## 先行者與互通（Prior art & interoperability）

- [AgentsView](https://github.com/kenn-io/agentsview) —— 本地優先的 session 搜尋／分析，支援 20+ 種 agent（SQLite、skill 使用趨勢、session 型態分類）。如果它已經在索引你的 session，機械資料建議直接以它為源：照 `references/generic.md` 的程序從它的統計輸出建立資料集（欄位對映未實測——涵蓋範圍照實說）。
- [ccusage](https://github.com/ccusage/ccusage) —— 橫跨十多種 agent CLI 的 token／用量報表；用量數字同理。
- Retrospective 類 skill（[glebis/claude-skills](https://github.com/glebis/claude-skills)、[session-retrospective](https://github.com/accidentalrebel/claude-skill-session-retrospective)、[reflect](https://github.com/hansvangent/reflect-skill-claude)）—— 單場或單日的回顧迴圈，更新 skill 或 `CLAUDE.md`。本 skill 的差異在：滾動一週的窗口、機械＋品質評估並用的證據基礎、以及由機械防護把關的有上限自我重構規則區塊。

## 現況

早期版本。分析路徑已用真實資料測過（Claude Code 的產物與原始紀錄；Codex 紀錄到資料層），skill 衛生流程也對 28 天的真實 session 做過 dry-run——它的防誤判規則每一條都來自那次實跑抓到的誤報。週迴圈的跨週行為——規則在連續回顧中被改寫、合併、退役——已寫成規格但還沒在實戰中跑過，且規則區塊的寫入永遠需要你核准。請把它當成一個你會盯著看的 v0，不是自動駕駛。

## 安裝

直接 clone 進跨工具 skills 目錄：

```
git clone https://github.com/shihchengwei-lab/session-analytics ~/.agents/skills/session-analytics
```

或手動複製資料夾。SKILL.md 格式是開放標準（Claude Code、Codex CLI、Gemini CLI、Cursor 等都支援）：

| 工具 | 使用者層級位置 |
|---|---|
| 跨工具（Codex CLI、Gemini CLI…） | `~/.agents/skills/session-analytics/` |
| Claude Code | `~/.claude/skills/session-analytics/`（或從上面那個位置連結過來） |
| Gemini CLI | `~/.gemini/skills/session-analytics/`（也會讀 `~/.agents/skills/`） |

在 Claude Code：`/session-analytics [問題]`。在 Codex CLI：`$session-analytics [問題]`。或直接講白話——「weekly review」「幫我改進工作流程」「分析我的 session」。

## 開發

抽取器的煙霧測試跑在合成 log 上、只用標準函式庫：`python -m pytest tests/`（或 `python -m unittest discover tests`）。

## 注意事項

- 紀錄格式是各工具未文件化的內部格式（schema 為 2026-07 觀察所得）；工具改版可能讓抽取失效——skill 被指示遇到對不上就明說，而不是硬套舊 schema。
- 品質欄位（成敗、摩擦）是模型的判斷、不是絕對事實；紀錄裡沒有這類欄位的（Codex），判斷來自抽樣證據並標記為推論。
- 覆蓋率天生是部分的；每份報告都會先說明自己涵蓋了什麼。
- 合併後的資料含有你的 prompt 與專案路徑——輸出請視為私人資料。
