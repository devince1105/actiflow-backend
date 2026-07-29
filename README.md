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

ActiFlow 將權限拆為「平台角色」與「主辦單位角色」。同一位使用者可以是一般會員，同時加入多個主辦單位，並另外擁有一個平台角色。

### 公開訪客與一般會員

| 身分 | 主要權限 |
| --- | --- |
| 訪客 | 查看公開活動、近期活動及歷史活動；不能存取會員與後台資料 |
| 一般會員 | 登入、更新個人資料與頭像、送出活動報名、查看自己的報名紀錄與詳情 |

單筆會員資料與報名資料均以目前登入者 UUID 驗證，不能透過修改 URL 查看其他會員的內容。

### 主辦單位角色

主辦單位角色定義於 `OrganizerMembership`：

| 角色 | 目前權限狀態 |
| --- | --- |
| `owner` | 已實作：完整管理所屬主辦單位的活動、欄位、範本與報名資料 |
| `admin` | 已實作：與 owner 一樣可通過 organizer admin guard |
| `editor` | 已定義；目前管理 API 尚未細分編輯權，預設不能通過 admin guard |
| `viewer` | 已定義；預留唯讀後台權限 |
| `member` | 已定義；可作為主辦單位成員，但不能通過 admin guard |

Canonical organizer API 使用 URL 中的 `organizer_uuid` 搭配資料庫 membership 驗證，不信任前端傳入的角色資訊。`owner` 與 `admin` 目前可：

- 建立、修改、發布、下架及關閉活動
- 管理活動欄位與活動範本
- 查看、審核與匯出報名資料
- 存取所屬主辦單位的後台功能

### 平台角色

平台角色定義於 `SystemMembership`：

| 角色 | 目前權限狀態 |
| --- | --- |
| `super_admin` | 已實作：系統級活動類型、範本、主辦單位申請及管理功能 |
| `system_admin` | 已定義，尚未全面配置獨立 guard |
| `site_admin` | 已定義，尚未全面配置獨立 guard |
| `support` | 已定義，預留客服查詢與有限操作權限 |
| `auditor` | 已定義，預留稽核唯讀權限 |

目前系統級敏感 API 主要使用 `super_admin` guard。其他平台角色在模型中已保留，但在新增功能前，不應假設它們已擁有管理權限。

### 權限判斷原則

- 身分驗證使用 HttpOnly Cookie 中的 access token。
- Token 主要識別 user；敏感權限會回資料庫查詢最新 membership。
- 停用、暫停或刪除的 membership 不應取得管理權限。
- Public API 不可回傳密碼雜湊、R2 Secret、JWT Secret 或其他內部憑證。
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
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

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
