# 把 Space 讓給公差工具：操作步驟

目標：
1. 先把 Hugging Face Space `finemtt1/Ignition-Coil-Simulation` 上目前的線圈模擬器檔案存回這個 GitHub 倉庫。
2. 再把同一個 Space 改成跑 `finemtt1/tolerance-studio`（公差工具）。

> 先說明一件事：Hugging Face 的免費 CPU basic Space **沒有數量上限**，
> 直接到 https://huggingface.co/new-space 再開一個給公差工具用，線圈模擬器的網址就能保留。
> 如果你還是想沿用這一個 Space，照下面做。

---

## 第 1 步：把 Space 上的檔案存回 GitHub

GitHub 這邊 `CoilProject/` 裡的 4 個檔案（app.py、README.md、requirements.txt、gitattributes）
是 2026-01-28 從 Space 抓下來的 V11 版。如果之後在 Space 網頁上直接改過 app.py，這裡就會落後。

在本機 Coil 倉庫根目錄執行：

```bash
python deploy/sync_from_space.py
```

它會 clone Space、把檔案覆蓋進 `CoilProject/`，最後印出 `git status`：

- 印出「沒有差異」→ GitHub 已是最新版，第 1 步結束。
- 有列出檔案 → 看一下 `git diff CoilProject`，然後：

```bash
git add CoilProject
git commit -m "Sync final files from HF Space"
git push
```

clone 若要求登入，帳號填 HF 帳號、密碼填 Access Token（https://huggingface.co/settings/tokens）。
Space 是 Public 的話通常不用登入。

---

## 第 2 步：把 Space 換成公差工具

公差工具倉庫已經有 `deploy/make_space.py`，它只會挑 Space 需要的檔案
（app.py、requirements.txt、LICENSE、tolstudio/、README_SPACE.md → README.md、packages.txt），
測試、MES 資料、xlsx 都不會被帶上去。

在本機 tolerance-studio 倉庫根目錄執行：

```bash
git clone https://huggingface.co/spaces/finemtt1/Ignition-Coil-Simulation ../Space
python deploy/make_space.py ../Space
cd ../Space
git add -A
git commit -m "Replace ignition coil simulator with Tolerance Studio"
git push
```

`make_space.py` 會清掉 `../Space` 裡除了 `.git` 之外的所有舊檔案再放入新檔案，
所以舊的線圈 app.py 會被正確移除，不會殘留。push 之後 Space 會自動重建，約 2～4 分鐘。

### 為什麼可以直接換

| 項目 | 說明 |
|---|---|
| Gradio 版本 | Space 的 README 標頭會被換成 `sdk_version: 4.44.1`，requirements 也釘 `gradio<5`，HF 會照新標頭重建，舊的 6.2.0 不會殘留。 |
| 綁定位址 | 公差工具的 `app.launch()` 讀 `GRADIO_SERVER_NAME` 環境變數，HF Space 會自動設成 `0.0.0.0`，不用改程式。 |
| 中文字型 | `make_space.py` 會產生 `packages.txt`（fonts-noto-cjk），圖表中文正常。 |
| 舊版本 | Space 本身的 git 歷史還在（Files → History），加上第 1 步已存回 GitHub，隨時可還原。 |

### 建議順手做的

- Space 頁面 → Settings → **Rename or transfer this Space**，把名稱改成 `tolerance-studio`，
  網址會變成 `https://huggingface.co/spaces/finemtt1/tolerance-studio`，舊網址會自動轉址。
- 若要處理機密的圖面尺寸，把 Visibility 改成 Private。
