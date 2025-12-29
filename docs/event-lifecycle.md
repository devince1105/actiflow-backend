 <!-- docs/event-lifecycle.md -->


# Event Lifecycle

本文件說明 ActiFlow 中 **Event（活動）** 的生命週期設計，
包含狀態定義、轉換規則、角色權限，以及與 Submission 的關聯。

---

## 1. Event 是什麼？

Event 代表一個「可對外開放報名的活動實例」，  
由 Organizer 建立並管理，並承載以下核心職責：

- 承接 Activity Template
- 定義報名欄位（Event Fields）
- 控制是否可被使用者報名
- 管理報名結果（Submissions）

---

## 2. Event 狀態定義

| Status        | 說明 |
|---------------|------|
| `draft`       | 草稿狀態，尚未對外開放 |
| `published`   | 已發布，可對外報名 |
| `closed`      | 已關閉，不再接受新報名 |
| `archived`    | 封存狀態，僅供查詢 |

---

## 3. Event 狀態轉換規則（Domain Rule）

Event 狀態只能依照以下規則轉換：

```text
draft     -> published
published -> closed
closed    -> archived
```
❌ 不允許：

- draft -> closed
- published -> archived
- 此規則應由 CRUD / domain layer 強制執行。

## 4. Event 狀態與 Submission 的關係

### 4.1 建立 Submission 條件

只有在 Event 為：
```text
published
```
時，才允許：

- Public 使用者建立 Submission
- Email 驗證流程啟動

### 4.2 Event 關閉後的行為

當 Event 進入：
```text
closed
```

- ❌ 不可建立新 Submission
- ✅ 既有 Submission 仍可：
  - 被 Organizer 審核（approve / reject）
  - 查詢與匯出

## 5. 角色與權限（簡述）

| 行為	| Organizer Admin / Owner |
|------|-------------------------|
| 建立 Event	| ✅ |
| 修改 draft Event	| ✅ |
| Publish Event	| ✅ |
| Close Event	| ✅ |
| Archive Event	| ✅ |


### Public User	 

- ❌ 無 Event 管理權限
- 僅能在 published 狀態下報名

## 6. Event Close 的語意（重要）

close 並不代表：

- Event 被刪除
- Submission 被鎖死

而是代表：

「活動不再接受新報名，但仍在結案流程中」

這個設計確保：

Organizer 可以安心完成審核

Submission lifecycle 不被中斷

7. Event 與 Submission Lifecycle 的整體關係

```text
Event:        draft -> published -> closed -> archived
                   |
                   v
Submission:  pending -> email_verified -> paid -> completed / rejected
```

Event 決定：

- 是否能產生 Submission

Submission lifecycle：

- 獨立於 Event 狀態
- 在 Event close 後仍可繼續推進

8. 設計原則（Design Principles）

- Event 與 Submission 狀態解耦
- 所有狀態轉換必須是：
  - 明確
  - 單向
  - 可審計

- API 僅負責 command
- 狀態合法性由 domain 層保證

## 9. 延伸規劃（Future）

可能的後續擴充：

- Event reopen（重新開放報名）
- Event schedule-based auto close
- Event-level notification（活動關閉通知）

## 10. 相關文件

- docs/submission-flow.md
- app/crud/event/
- app/api/events/


---