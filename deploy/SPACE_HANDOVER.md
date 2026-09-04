# 把 Space 讓給公差工具：目前狀態與流程

目標：
1. 把 Hugging Face Space `finemtt1/Ignition-Coil-Simulation` 上線圈模擬器的最終版檔案存回這個 GitHub 倉庫。
2. 把同一個 Space 改成跑 `finemtt1/tolerance-studio`（公差工具）。

兩件事都用 GitHub Actions 自動完成，不需要在本機裝 git。

---

## 第 1 步：Space → GitHub 備份（已完成）

`.github/workflows/backup-space.yml` 會 clone Space、把檔案覆蓋到 `CoilProject/`，有差異就自動 commit。
2026-09-04 執行結果：Space 上的 app.py 比 GitHub 舊版新（改寫成 matplotlib Agg / Figure、
新增 Typical_15A_IGBT 等），已同步進 `CoilProject/`。

之後如果 Space 又有改動，到 Actions 分頁手動按一次 **Run workflow** 即可再同步。
本機也可以直接執行 `python deploy/sync_from_space.py`。

---

## 第 2 步：GitHub → Space 部署公差工具

流程檔在 tolerance-studio 倉庫：`.github/workflows/deploy-space.yml`。
它會 clone Space、執行 `deploy/make_space.py` 只挑 Space 需要的檔案
（app.py、requirements.txt、LICENSE、tolstudio/、README_SPACE.md → README.md、packages.txt），
清掉舊的線圈檔案後 push，最後等 Space 建置到 RUNNING 才結束。

唯一需要人工做的：在 tolerance-studio 倉庫的
Settings → Secrets and variables → Actions 新增 secret `HF_TOKEN`
（內容是 https://huggingface.co/settings/tokens 產生的 **Write** 權限 token）。
沒有這個 secret 時流程會直接略過，不會動到 Space。

### 為什麼可以直接換

| 項目 | 說明 |
|---|---|
| Gradio 版本 | Space 的 README 標頭會被換成 `sdk_version: 4.44.1`，requirements 也釘 `gradio<5`，HF 會照新標頭重建。 |
| 綁定位址 | 公差工具的 `app.launch()` 讀 `GRADIO_SERVER_NAME`，HF Space 會自動設成 `0.0.0.0`。 |
| 中文字型 | `make_space.py` 會產生 `packages.txt`（fonts-noto-cjk）。 |
| 舊版本 | Space 的 git 歷史還在（Files → History），加上第 1 步已存回 GitHub，隨時可還原。 |

### 建議順手做的

- Space 頁面 → Settings → **Rename or transfer this Space**，改名為 `tolerance-studio`，舊網址會自動轉址。
- 若要處理機密的圖面尺寸，把 Visibility 改成 Private。
