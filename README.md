# ActiFlow

ActiFlow 是活動建立、公開招募、線上報名與主辦方審核平台。本 repository 是 FastAPI 後端；前端位於 `actiflow-frontend`。

## 系統如何運作

```text
Next.js 前端
    ├─ 公開活動列表與活動詳情
    ├─ 會員登入、報名與報名紀錄
    └─ 主辦單位及系統管理後台
             │
             ▼
FastAPI API（Cookie/JWT 驗證與 RBAC）
    ├─ PostgreSQL / Neon：帳號、活動、報名、權限及媒體 URL
    ├─ Cloudflare R2：頭像、活動封面與其他圖片檔案
    └─ Resend：驗證信及通知信
```

主要流程：

1. 主辦單位建立活動、設定欄位、容量、日期與報名截止時間。
2. 活動發布後出現在公開活動列表；歷史活動由 API 在資料庫查詢階段分流。
3. 訪客查看活動，登入會員可送出報名資料。
4. 後端檢查活動狀態、截止時間、容量與重複報名，再建立 submission。
5. 主辦單位在後台檢視、審核及匯出報名資料。
6. 會員可在「我的報名」查看狀態與單筆詳情。
7. 圖片由前端透過短效 presigned URL 直接上傳 R2；資料庫只保存永久公開 URL。

## 角色與權限

ActiFlow 將權限拆成「網站層級」與「活動單位層級」，不使用單一角色階級。
同一位使用者可以是網站會員，同時擔任某個活動單位的管理員，並在另一個
活動單位中只是會員。

```text
網站層級
├── 網站系統管理員
├── 網站會員
└── 訪客

活動單位層級
├── owner（對外顯示：活動單位管理員）
├── admin（對外顯示：活動單位管理員）
└── member（對外顯示：活動單位會員）
```

### 對外角色

| 對外名稱 | 內部角色 | 權限範圍 |
| --- | --- | --- |
| 網站系統管理員 | `super_admin` | 整個 ActiFlow 平台 |
| 活動單位管理員 | `owner` / `admin` | 指定活動單位 |
| 活動單位會員 | `member` | 指定活動單位 |
| 網站會員 | 無特殊 membership | 自己的帳號與報名 |
| 訪客 | 未登入 | 公開內容 |

### 網站系統管理員

網站系統管理員是最高平台權限，可以：

- 管理網站會員及平台角色
- 審核、停用及恢復活動單位
- 查看全平台活動與報名狀況
- 強制下架違規活動
- 管理非敏感網站設定
- 查看管理操作 Audit Log

網站系統管理員不會自動成為所有活動單位的 `owner`，也不應透過主辦後台
冒用活動單位管理員身分。平台介入操作使用獨立管理 API，並保存 Audit Log。
後台及 API 不得顯示密碼、付款機密、Neon、JWT、R2 或 Email Secret。

### 活動單位管理員

`owner` 與 `admin` 對外均顯示為「活動單位管理員」，但保留以下內部差異：

| 能力 | `owner` | `admin` |
| --- | --- | --- |
| 建立、修改及發布活動 | 是 | 是 |
| 管理活動欄位與範本 | 是 | 是 |
| 查看、審核及匯出報名 | 是 | 是 |
| 管理一般成員 | 是 | 是 |
| 指派或移除管理員 | 是 | 否 |
| 轉移單位擁有權 | 是 | 否 |
| 解散活動單位 | 是 | 否 |

`admin` 不可移除 `owner`、修改 owner 角色或轉移擁有權。

### 活動單位會員

`member` 採最小權限，預設可以進入所屬單位並查看被授權的工作內容，但不可以：

- 建立、發布或修改活動
- 查看完整報名者敏感資料
- 審核、拒絕、刪除或匯出報名
- 管理其他活動單位成員

若日後有明確需求，再加入 `editor`、`reviewer`、`checkin_staff` 或 `viewer`
等細分角色；在後端 guard 與測試完成以前，不賦予這些預留角色管理權限。

### 網站會員

網站會員可以：

- 管理自己的基本資料、密碼、頭像與通知偏好
- 瀏覽及報名活動
- 查看或依活動規則取消自己的報名
- 上傳自己的報名附件
- 申請成立活動單位

網站會員不能進入未加入的活動單位後台，也不能查看其他會員或其他報名者資料。

### 訪客

訪客可以查看公開活動、近期／歷史活動、公開活動單位資訊，以及註冊或登入。
免費活動可依產品策略允許訪客以 Email 報名並完成 Email 驗證；需要付款或長期
管理的報名流程建議要求登入。

### 多重身分範例

```text
某位使用者（網站會員）
├── 河濱路跑協會：owner
└── 攝影學會：member
```

權限必須根據目前操作的資源範圍判斷：

- 進入網站管理後台：檢查有效的 system membership。
- 進入活動單位後台：以 URL 中的 `organizer_uuid` 查詢該單位 membership。
- 查看個人帳號或報名：檢查目前登入者 `user_uuid`。
- 查看公開活動：不需要 membership。

### 權限判斷原則

- 身分驗證使用 HttpOnly Cookie 中的 access token。
- Token 主要識別 user；敏感權限必須回資料庫查詢最新 membership。
- 不信任前端傳入的角色、user UUID 或 organizer UUID。
- 停用、暫停或刪除的 membership 不得取得管理權限。
- 單筆會員及報名資料必須驗證 owner，不能只依 URL 判斷。
- 敏感操作必須要求確認、保存原因並寫入 Audit Log。
- 總管理員測試密碼只可放在本機 `.env`，不得寫入 README 或提交 Git。

## 活動生命週期

| 狀態 | 說明 |
| --- | --- |
| `draft` | 草稿，不出現在公開活動列表 |
| `published` | 已發布，可在符合日期條件時公開顯示 |
| `closed` | 已關閉，不接受新報名 |

公開列表支援：

```text
GET /public/events?period=upcoming
GET /public/events?period=past
GET /public/events?period=all
```

- `upcoming`：尚未結束或正在進行的活動
- `past`：已結束活動
- `all`：保留完整列表及相容性

即使使用者直接進入過期活動報名網址，後端仍會再次驗證截止時間與容量；前端停用按鈕只是操作體驗，不是安全邊界。

## 圖片與 Cloudflare R2

目前圖片上傳流程：

1. 登入者向 `POST /uploads/images/presign` 提供 MIME、大小與用途。
2. 後端驗證檔案類型與大小，產生 5 分鐘有效的 presigned PUT URL。
3. 瀏覽器直接把檔案上傳 R2，R2 金鑰不會離開後端。
4. 前端將 R2 公開 URL 寫入對應資料。

限制：

| 用途 | 大小上限 |
| --- | --- |
| 會員頭像 | 5 MiB |
| 主辦單位 Logo | 5 MiB |
| 活動封面 | 8 MiB |

允許格式：JPEG、PNG、WebP、GIF。基於主動內容與 XSS 風險，目前不接受 SVG。

R2 bucket 必須允許前端來源執行 `PUT` CORS。正式部署時請將正式前端網域加入 `AllowedOrigins`，不要使用 `*`。

## 技術架構

- Python 3.11
- FastAPI 0.110
- SQLAlchemy 2
- PostgreSQL（Neon）
- Pydantic 2
- Alembic
- Cookie + JWT
- Cloudflare R2（S3-compatible API）
- Pytest

## 本機開發

### 1. 建立並啟用虛擬環境

```bash
python3.11 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

專案根目錄的 `.python-version` 固定為 Python 3.11；使用 pyenv 等版本管理工具時
會自動套用。Docker image 亦使用相同的 Python minor version。

若既有 venv 是從其他路徑搬移而來，`pip` 的 shebang 可能失效；使用：

```bash
venv/bin/python -m pip install -r requirements.txt
```

### 2. 設定環境變數

建立 `.env`，至少包含：

```env
ENV=dev
DATABASE_URL=postgresql://...
TEST_DATABASE_URL=postgresql://...

JWT_SECRET=replace-with-a-long-random-secret
COOKIE_SECURE=false
BACKEND_CORS_ORIGINS=http://localhost:3001

FRONTEND_BASE_URL=http://localhost:3001
RESEND_API_KEY=
RESEND_FROM_EMAIL=

R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=actiflow
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
R2_PUBLIC_BASE_URL=https://<public-id>.r2.dev
```

注意：

- `.env` 不可提交 Git。
- `R2_ENDPOINT_URL` 不要附加 bucket 名稱。
- `ENV=dev` 時，若設定了 `TEST_DATABASE_URL`，目前程式會優先使用它。
- 生產環境應使用 `COOKIE_SECURE=true` 與明確的 CORS 網域。
- `SUPER_ADMIN_EMAIL`、`SUPER_ADMIN_PASSWORD` 僅供本機測試帳密管理，不是應用程式啟動必要設定。

### 測試角色帳號

測試密碼只存於本機 `.env`，不得寫入 README 或提交 Git。

| 測試身分 | 登入帳號 | 內部角色 | 密碼來源 |
| --- | --- | --- | --- |
| 網站系統管理員 | `admin@actiflow.dev` | `super_admin` | `SUPER_ADMIN_PASSWORD` |
| 活動單位擁有者 | `qa.owner@actiflow.dev` | `owner` | `ROLE_TEST_PASSWORD` |
| 活動單位管理員 | `qa.admin@actiflow.dev` | `admin` | `ROLE_TEST_PASSWORD` |
| 活動單位會員 | `qa.member@actiflow.dev` | `member` | `ROLE_TEST_PASSWORD` |
| 網站會員 | `qa.user@actiflow.dev` | 無特殊 membership | `ROLE_TEST_PASSWORD` |
| 訪客 | 不登入 | 無 | 不需要密碼 |

首次建立或需要重設 QA 帳密時執行：

```bash
./venv/bin/python -m scripts.seed_role_test_accounts
```

此腳本可重複執行，會使用 `.env` 中的 `ROLE_TEST_*` 設定更新測試帳號，
並將 owner、admin、member 放在同一個 `ROLE_TEST_ORGANIZER_UUID` 內，方便比較權限。

### 3. 啟動 API

```bash
./venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

確認：

```text
http://localhost:8000/
http://localhost:8000/docs
```

### 4. 執行測試

```bash
./venv/bin/python -m pytest -q
```

測試必須使用隔離的 `TEST_DATABASE_URL`。請勿將會新增或刪除資料的測試指向正式 Neon database。

pytest 會比較 `DATABASE_URL` 與 `TEST_DATABASE_URL` 的主機、port
及 database 名稱。兩者位置相同或未設定測試資料庫時，資料庫整合測試會安全跳過，
純單元及 SQLAlchemy mapper 測試仍會執行。Neon 測試 branch 應使用與正式 branch
不同的 hostname。

## 常用目錄

```text
app/api/          FastAPI routes 與權限 dependency
app/core/         設定、DB、JWT、例外與共用安全邏輯
app/crud/         資料存取層
app/models/       SQLAlchemy models
app/schemas/      Pydantic request/response schemas
app/services/     報名與 R2 等業務服務
alembic/          Database migrations
scripts/          可重複執行的維護與 seed scripts
tests/            Pytest tests
```

## 系統管理後台規劃

ActiFlow 將後台分為兩個責任範圍：

| 後台 | 路徑 | 管理範圍 |
| --- | --- | --- |
| 系統管理後台 | `/admin` | 整個 ActiFlow 平台，由平台角色使用 |
| 主辦單位後台 | `/organizers/{organizer_uuid}` | 單一主辦單位及其活動，由 organizer membership 控制 |

系統管理員不應透過主辦後台模擬 organizer；主辦單位管理員也不能因為能管理自己的活動，就取得平台級資料。

### 系統後台資訊架構

```text
/admin
├── dashboard          系統總覽
├── users              會員管理
├── organizers         主辦單位管理
│   └── applications   主辦單位申請審核
├── events             全平台活動管理
├── submissions        報名資料監控
├── media              R2 媒體管理
├── settings           系統設定
└── audit-logs         管理操作紀錄
```

目前已完成：

- `super_admin` membership 辨識
- `/admin` route guard 與系統管理入口
- 系統管理總覽與即時統計 API
- 會員列表、Email 搜尋與分頁
- 主辦單位列表與待審申請清單
- 主辦申請核准／拒絕流程（包含確認原因、transaction 與 audit log）
- 全平台活動搜尋、狀態／時間篩選與分頁
- 活動強制下架／恢復發布（要求原因並寫入 audit log）
- 跨平台報名搜尋、狀態統計與分頁監控（唯讀）
- 管理操作紀錄搜尋、資源／動作篩選與前後狀態摘要（唯讀）
- 非敏感系統設定管理、版本衝突保護與設定異動 audit log
- `/admin/dashboard` 舊路徑相容導向

規劃中的管理模組：

#### Dashboard

- 會員、主辦單位、活動及報名總數
- 草稿、已發布、關閉、近期與歷史活動數
- 待審核主辦申請
- 最近管理操作及異常狀態
- R2 媒體數量與儲存空間摘要

#### 會員管理

- 依 email 搜尋及分頁
- 查看帳號、平台角色、organizer memberships 與報名紀錄
- 停用、恢復及強制重設密碼
- 指派或移除平台角色

停用、密碼重設與角色修改都屬敏感操作，必須有確認步驟並寫入 audit log。

#### 主辦單位與申請審核

- 查看所有主辦單位及其狀態
- 核准、拒絕、停權及恢復
- 查看成員、活動與申請資料
- 調整 owner/admin membership
- 保存拒絕、停權與恢復原因

#### 全平台活動管理

- 依狀態、日期與主辦單位篩選
- 查看活動內容、容量、報名截止時間與報名概況
- 強制下架違規活動或關閉報名
- 區分近期及歷史活動

總管理員第一階段以監控、下架及關閉為主，不直接修改主辦方的活動內容。

#### 報名監控

- 依 submission code、活動、狀態及日期搜尋
- 查看 email verification、付款及審核狀態
- 協助處理申訴、異常或重複報名
- 對管理操作保存操作者與原因

日常報名管理仍由活動所屬 organizer 處理；平台管理員只介入跨組織及異常事件。

#### R2 媒體管理

- 依頭像、Logo、活動封面分類
- 顯示 object key、MIME、大小、上傳者與時間
- 找出未被資料庫引用的孤兒物件
- 刪除違規或失效媒體
- 偵測單一帳號異常大量上傳

後續建議新增 `media_assets` table，集中記錄 R2 object metadata 與 ownership；目前部分功能只有 URL 欄位，無法可靠執行孤兒檔案清理。

#### 系統設定

- 平台名稱與維護模式
- 是否開放會員註冊及主辦申請
- 活動預設值及圖片限制
- Email 寄件資訊的非敏感欄位

Neon、R2、JWT 與 Email Secret 不可由後台頁面讀取或修改。

#### Audit log

至少保存：

- 操作者 UUID 與角色
- 操作時間、request ID 與來源 IP
- 操作資源及資源 UUID
- 變更前後摘要
- 停權、刪除、下架及角色異動原因

### 規劃中的平台權限矩陣

| 功能 | `super_admin` | `system_admin` | `site_admin` | `support` | `auditor` |
| --- | --- | --- | --- | --- | --- |
| 系統設定 | 完整 | 可管理 | 部分 | 無 | 唯讀 |
| 會員停權 | 是 | 是 | 是 | 否 | 唯讀 |
| 平台角色管理 | 是 | 否 | 否 | 否 | 唯讀 |
| 主辦申請審核 | 是 | 是 | 是 | 否 | 唯讀 |
| 活動強制下架 | 是 | 是 | 是 | 否 | 唯讀 |
| 報名資料 | 是 | 是 | 是 | 有限 | 唯讀 |
| Audit log | 是 | 是 | 唯讀 | 無 | 唯讀 |

此表為目標設計；目前敏感管理 API 仍以 `super_admin` guard 為主。在對應 dependency、測試與 audit log 完成前，不應開放其他平台角色。

### 建議開發批次

1. 管理骨架：真實 Dashboard 統計、側邊選單、route guard、loading/403/error。
2. 會員與主辦單位：列表、詳情、搜尋、分頁、停用及申請審核。
3. 活動與報名監控：跨平台查詢、詳情、強制下架、關閉與敏感操作確認。
4. 媒體、設定與稽核：`media_assets`、孤兒清理、系統設定、audit log 及細分 RBAC。

## 安全與維運提醒

- 不要在 README、issue、commit 或前端環境變數中保存密碼與 Secret。
- 前端環境變數使用 `NEXT_PUBLIC_` 前綴後會進入瀏覽器 bundle，不可放 R2 Secret。
- R2 presigned URL 應視為短效 bearer token，不記錄完整 URL。
- 變更 model 後應建立 Alembic migration，不要只修改 ORM。
- 活動截止、容量、ownership 與角色權限必須由後端再次驗證。
- 上線前應將 in-memory rate limiting 改為 Redis 或其他共享儲存。

## Repository

- Backend：本 repository
- Frontend：`actiflow-frontend`
