# 執行摘要 — 加密貨幣市場儀表板

**作業：** Deployment of a Dashboard with its own Data Pipeline
**線上應用：** <https://crypto-dashboard-dm9wvnvtvq8pexhlkyqbyj.streamlit.app/>

---

## 專案概述

本專案建置並部署了一個加密貨幣市場儀表板，後端搭配一條全自動的資料管線（ETL）。系統每 15 分鐘從三個公開 API 蒐集市場資料，經清洗後寫入雲端 PostgreSQL 資料庫；前端 Streamlit 網頁應用再從資料庫讀取，呈現互動式視覺化圖表。整個系統部署於雲端，透過公開網址即可存取，無需本機運行。

---

## 系統架構

```
[CoinGecko API]          ┐
[Alternative.me API]     ├─► GitHub Actions (排程) ─► ETL 腳本 ─► Supabase PostgreSQL ─► Streamlit Cloud
[Blockchain.com API]     ┘
```

| 層級 | 技術 | 角色 |
|---|---|---|
| 排程 | GitHub Actions (cron) | 每 15 分鐘觸發 ETL |
| 資料來源 | CoinGecko、Alternative.me、Blockchain.com | 價格、情緒、鏈上資料 |
| ETL | Python（`requests`、`tenacity`） | 抓取、清洗、去重、寫入 |
| 資料庫 | Supabase PostgreSQL | 永久儲存（3 張資料表） |
| 前端 | Streamlit + Plotly | 互動式網頁介面 |
| 部署 | Streamlit Cloud | 公開網址託管 |

---

## 資料管線（ETL）

三個獨立的 API 來源由同一支 ETL 腳本處理，並透過 GitHub Actions 排程執行：

- **CoinGecko** → `prices` 表 — 市值前十大幣種的收盤價、成交量、市值與漲跌幅，每 15 分鐘一筆快照；以 `(coin_id, bucket_time)` 唯一鍵防止重複。
- **Alternative.me** → `fear_greed` 表 — 每日恐懼貪婪指數（0–100）；以 `recorded_at` 為唯一鍵。
- **Blockchain.com** → `onchain` 表 — 每日比特幣鏈上指標：活躍地址數、交易筆數、估計轉帳金額（USD）；以 `(metric, recorded_at)` 為唯一鍵。

資料清洗包含型別轉換、空值過濾，並採用 upsert（衝突即更新）邏輯，使重複執行具備冪等性（idempotent），不會產生重複資料。關鍵來源（CoinGecko）失敗時 ETL 會明確報錯；情緒與鏈上資料為輔助來源，失敗時記錄警告並繼續執行。

---

## 資料更新機制

| 機制 | 觸發方式 | 頻率 |
|---|---|---|
| GitHub Actions 排程 | 自動 | 每 15 分鐘 |
| 儀表板「重新整理」按鈕 | 使用者手動 | 隨點隨更新（清除快取） |

排程是主要的資料寫入路徑；為避免對輔助來源過度呼叫，ETL 會先檢查資料庫中當日資料是否已存在，僅在缺漏或過期時才抓取每日來源。前端按鈕則清除 Streamlit 的查詢快取，讓使用者立即看到管線已寫入的最新資料。

---

## 儀表板視覺化

Streamlit 應用提供四個互動區塊：

1. **市場快覽卡片** — 比特幣、以太幣即時價格與 24 小時漲跌、前十大市值總和、恐懼貪婪指數。
2. **價格走勢圖** — TradingView 風格的價格折線搭配成交量柱狀圖；成交量依當日漲跌以紅綠區分，價格軸置於右側，可切換幣種與 7 天 / 30 天 / 90 天時間範圍。圖表會依範圍自動調整解析度：**7 天內顯示小時級日內資料、30/90 天收斂為日線**，讓高頻更新在短期圖上真正可見、長期圖又保持易讀。
3. **市場情緒** — 恐懼貪婪指數圓形儀表盤（含指針）與近 30 天趨勢折線。
4. **鏈上數據** — 比特幣網路指標折線圖，可切換活躍地址數、交易筆數、估計轉帳金額三種指標。

所有圖表皆以 Plotly 繪製，支援滑鼠懸停提示、垂直十字準線、縮放與平移。時間一律以台北時間（UTC+8）顯示，介面全面中文化。
