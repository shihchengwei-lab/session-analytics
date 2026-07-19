# session-analytics

[English](README.md) · **繁體中文**

一個 [Agent Skill](https://agentskills.io)，讓 AI coding agent 持續改進你們的協作方式——定位是**自我優化的 harness 技能**：每個 agent 分析**自己這套工具**最近 7 天的本地 session 紀錄，把你真正在用的路徑加粗、沒在用的剪枝，並在模型更換後重新驗證自己過去給的建議——讓整套設定持續進步，而不是越堆越多。只讀本機資料、不上傳任何東西；分析樣本會經過你的 agent 的模型 context——跟你平常使用該 agent 的每一場對話是同一個信任邊界。

為什麼是 7 天：拉長到一個月的全景會混入早已被修正的舊行為；滾動一週讓訊號聚焦在*現在的你*。隨時都能跑——一個自然的節奏是在每週用量重置前，拿剩餘額度跑一次回顧。

## 兩種模式

- **查詢**：「這週哪些 session 失敗了？」「我的成功率？」「比較我的實驗跑次」——或不帶問題直接呼叫，得到一頁式週總覽，結尾附有憑有據的建議。查詢模式只報告，什麼都不改。
- **週回顧**：總覽之外，在三條戰線上提出證據綁定的改動：
  - **規則區塊**：維護在工具設定檔（`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`）裡，一段註解標記圍起來的區塊，硬上限 10 條單行規則（首次安裝 3 條），每條帶著證據與日期；每週整塊重新推導——留任／改寫（規則在了、摩擦還是發生）／合併（重疊）／退役（連續兩週乾淨＝畢業）——所以它會自我重構而不是堆積。模型更換會讓舊證據貶值：只在前一個模型下確認過的規則要重新驗證，不自動留任
  - **機制優於文字規則**：hook、環境變數、權限設定能機械化解決的摩擦，就提設定檔 diff、不再多寫一條規則；機制上線後，被它取代的文字規則同一輪退役。提案若要*新建*東西，必須先爬找輪子階梯：採用 → 設定 → 只抽需要的 → 照設計寫小的 → 說明理由後才准從零建
  - **Skill 衛生，雙向進行**：把已安裝的 skill 對照實際呼叫次數（模型主動呼叫與使用者手打都算）。熱路徑得到去摩擦提案（更利的觸發描述、權限 allowlist）；從沒被呼叫的列為停用候選——並有防誤判保護：新裝的不判、ambient 型 plugin（statusline、hook、MCP）的價值不長在呼叫次數上，不用次數判它們

  規則區塊是這個 skill 唯一會動手編輯的檔案，寫入由三層機制把關：每個提案必須先通過機械驗證器（標記邊界位元組級比對、規則數上限）才有資格給你看 diff；**你核准之後才寫入**；若裝了選配的寫入時 hook，驗證器在寫入當下會再跑一次，就算流程漏跑了驗證，不合格的寫入也會被機械擋下。整塊移除（解除安裝）是允許的，但需要明確確認。標記內你手寫的規則原樣保留；標記外的內容永遠不碰。

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

## 專案結構

| 路徑 | 角色 |
|---|---|
| `SKILL.md` | agent 遵循的指示——五階段流程：判斷需求、建資料集、分析、報告、套用（僅週回顧） |
| `references/claude-code.md`、`codex.md`、`generic.md` | 各工具指南：紀錄放在哪、每個欄位是什麼意思、這份資料答得了與答不了哪些問題 |
| `scripts/extract_claude_raw.py` | 把 Claude Code 原始 session 紀錄（`~/.claude/projects`）壓縮成每個 session 一行 JSON |
| `scripts/extract_codex.py` | Codex 版（`~/.codex/sessions`） |
| `scripts/merge_facets.py` | 合併 Claude Code `/insights` 產物（session metadata＋品質評估）成單一資料集 |
| `scripts/validate_rules_block.py` | 規則區塊的機械閘門：標記邊界位元組級比對、規則數上限，以結束碼強制 |
| `scripts/guard_rules_block.py` | 選配的寫入時 hook：攔截 agent 對設定檔的編輯，在寫入落地前先跑驗證器 |
| `tests/` | 29 個測試，跑在合成紀錄與設定檔上、只用標準函式庫——涵蓋抽取器、驗證器、hook |

所有腳本只用 Python 標準函式庫——零依賴、不開任何網路連線。

## 資料來源

| 工具 | 來源 | 成本 |
|---|---|---|
| Claude Code（品質資料） | `~/.claude/usage-data`（需先跑過 `/insights`） | 預先算好——讀取不花分析成本 |
| Claude Code（機械資料） | `~/.claude/projects` 原始紀錄，內附抽取器——零設定、隨時最新、含每個 skill 的呼叫次數 | 只取 metadata＋樣本 |
| OpenAI Codex | `~/.codex/sessions/**.jsonl`，內附抽取器 | 只取 metadata＋樣本 |
| 其他工具 | 照 `references/generic.md` 的程序 | 取決於有什麼紀錄 |

抽取器對每個 session 記錄：時間戳與時長、專案路徑與 git 分支、模型名稱、工具／skill／子代理／斜線指令的呼叫次數、輸出 token 總量（主對話與子代理分開計），以及至多 5 則你的 prompt、每則截斷到 200 字元——這份樣本是資料集裡唯一一段你親手寫的內容。完整逐字稿永遠不會被複製出來；那是成本邊界。

如果紀錄檔存在、內容卻一筆都認不得（工具改版後紀錄格式變更的典型徵兆），抽取器會大聲說出來——Claude Code 版直接拒寫資料集；Codex 版輸出還能用的部分並在 stderr 警告——讓 schema 壞掉讀起來是「抽取壞了」，而不是「你這週沒用過」。

## 隱私與成本

- 一切在本機執行；腳本不開任何網路連線。分析本身是你的 agent 做的，它檢視的統計數字與 prompt 樣本會進入模型 context、跟任何對話內容一樣傳到模型供應商——跟你平常的 session 是同一個信任邊界，沒有新增、也沒有更小。
- 資料集檔案寫在暫存目錄，內含你的 prompt 與專案路徑——請視為私人資料，不要大量貼到公開場合。
- 一次典型執行讀的是壓縮資料集、不是逐字稿，花費跟一輪普通對話同量級。唯一昂貴的操作——深讀單一 session 的完整紀錄——需要你在被告知會花實際 token 之後明確同意。

## 前置需求

- agent 執行環境要有 Python 3
- Claude Code：成敗／摩擦評估需要至少跑過一次 `/insights`；純機械資料零設定即可用。Codex：要有既存的 session 紀錄

## 不做的事（Non-goals）

內附的資料層是刻意做到最小的零依賴備援，不是產品。這個 skill 不會再長出：新的 agent parser、session 資料庫或搜尋索引、dashboard／UI、token 成本試算。成熟的本地工具已經把這些做得很好（見下）；這個 skill 真正的工作是決策層——把 session 證據轉成少量、有界、可撤銷、經你核准的 harness 改動。

## 先行者與互通（Prior art & interoperability）

- [AgentsView](https://github.com/kenn-io/agentsview) —— 本地優先的 session 搜尋／分析，支援 20+ 種 agent（SQLite、skill 使用趨勢、session 型態分類）。如果它已經在索引你的 session，機械資料建議直接以它為源：照 `references/generic.md` 的程序從它的統計輸出建立資料集（欄位對映未實測——涵蓋範圍照實說）。
- [ccusage](https://github.com/ccusage/ccusage) —— 橫跨十多種 agent CLI 的 token／用量報表；用量數字同理。
- Claude Code 官方的 `/checkup`（`/doctor` 的別名，v2.1.186+）—— 隨叫隨用的設定健檢：安裝診斷、CLAUDE.md 瘦身、找出沒在用的 skill／MCP server／plugin 並對照 context 成本。它看的是設定的當下狀態；「沒在用」的判斷依據官方沒有文件化（2026-07 時點），所以本 skill 的衛生盤點保留自己的呼叫次數證據，把 `/checkup` 當交叉核對、不當替代。
- Retrospective 類 skill（[glebis/claude-skills](https://github.com/glebis/claude-skills)、[session-retrospective](https://github.com/accidentalrebel/claude-skill-session-retrospective)、[reflect](https://github.com/hansvangent/reflect-skill-claude)）—— 單場或單日的回顧迴圈，更新 skill 或 `CLAUDE.md`。本 skill 的差異在：滾動一週的窗口、機械＋品質評估並用的證據基礎、以及由機械防護把關的有上限自我重構規則區塊。

## 現況

早期版本。分析路徑已用真實資料測過（Claude Code 的產物與原始紀錄；Codex 紀錄到資料層），skill 衛生流程也對 28 天的真實 session 做過 dry-run——它的防誤判規則每一條都來自那次實跑抓到的誤報。寫入時 hook 已實戰驗證過：一次破壞標記的編輯在真實 session 中被當場擋下。週迴圈的跨週行為——規則在連續回顧中被改寫、合併、退役——已寫成規格但還沒在實戰中跑過，且規則區塊的寫入永遠需要你核准。請把它當成一個你會盯著看的 v0，不是自動駕駛。

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

在 Claude Code：`/session-analytics [問題]`。在 Codex CLI：`$session-analytics [問題]`。或直接講白話——「weekly review」「幫我改進工作流程」「分析我的 session」。不呼叫就什麼都不會執行；下面兩個選配會改變這一點，所以做成可自選加裝。

### 選配：寫入時防護 hook（Claude Code）

在 agent 每一次改檔時機械強制規則區塊的契約：非設定檔在檔名檢查後直接放行；碰到區塊的編輯重跑驗證器、不合格就擋下；整塊移除會跳確認。每次編輯增加約 0.1–0.3 秒的 Python 啟動時間，且為故障放行（fail-open）設計——hook 自己壞掉時編輯照常進行，壞掉的閘門不會把你鎖在自己的設定檔外。加進 `~/.claude/settings.json` 的 hooks，路徑改成你的安裝位置：

```json
"PreToolUse": [
  {
    "matcher": "Edit|Write",
    "hooks": [
      {
        "type": "command",
        "command": "python /absolute/path/to/session-analytics/scripts/guard_rules_block.py",
        "timeout": 10
      }
    ]
  }
]
```

其他工具沒有標準 hook 系統；驗證器仍會在流程內執行，只是少了這道機械後盾。

### 選配：每週排程

用工具的排程器（例如 Claude Code desktop 的 scheduled tasks）每週以「weekly review」呼叫本 skill，並指示排程執行只走到報告＋提案為止——核准永遠在你在場時進行，不在無人值守時發生。

skill 沒辦法自己叫醒自己：沒有觸發，迴圈就靜默停擺，所以排程要配一個不依賴它的提醒（固定的行事曆事件就行）。就算迴圈真的斷了，下一次回顧——不管隔多久——會把 skill 自己的閒置當成「節奏斷了、該重新接上」，而不是「沒在用、該退役」。

## 開發

測試跑在合成紀錄與設定檔上、只用標準函式庫：`python -m pytest tests/`（或 `python -m unittest discover tests`）。涵蓋抽取器、驗證器、hook。沒有設 CI——改完請自己跑。

## 注意事項

- 紀錄格式是各工具未文件化的內部格式（schema 為 2026-07 觀察所得）；工具改版可能讓抽取失效——skill 被指示遇到對不上就明說，而不是硬套舊 schema。
- 品質欄位（成敗、摩擦）是模型的判斷、不是絕對事實；紀錄裡沒有這類欄位的（Codex），判斷來自抽樣證據並標記為推論。
- 覆蓋率天生是部分的；每份報告都會先說明自己涵蓋了什麼。
- skill 的觸發（明打 `/session-analytics` 之外）是 agent 對觸發描述的判斷——不是機械保證。
- 防護 hook 只守兩種標準編輯工具；agent 若改用原始 shell 指令寫檔可以繞過。它的定位是接住失誤，不是擋住蓄意繞道。
