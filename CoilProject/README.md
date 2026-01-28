---
title: Ignition Coil Simulation
emoji: 🦀
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 6.2.0
app_file: app.py
pinned: false
license: mit
short_description: performance simulation
---

# ⚡ 點火線圈設計模擬器 V11.0

這是一個專業的點火線圈 (Ignition Coil) 模擬工具，支援磁飽和計算與 IGBT 動態偏移補償。

### 核心功能
* **磁飽和模擬**：考慮鐵芯飽和後的電壓表現。
* **K 值校準**：利用實測數據反推結構係數。
* **結構計算**：自動推算線圈外徑 (OD) 與二次側電阻。

### 如何啟動
1. 安裝環境：`pip install -r requirements.txt`
2. 執行程式：`python app.py`

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference
