# -*- coding: utf-8 -*-
"""
把 Hugging Face Space「finemtt1/Ignition-Coil-Simulation」目前線上的檔案
抓回來，覆蓋到本倉庫的 CoilProject/，讓 GitHub 保有 Space 的最終版本。

用法（在 Coil 倉庫根目錄執行）：
    python deploy/sync_from_space.py            # 從 Hugging Face clone 後同步
    python deploy/sync_from_space.py <已 clone 的 Space 資料夾>   # 離線：從本機資料夾同步

同步完成後自己看一下 git diff，確認沒問題再：
    git add CoilProject && git commit -m "Sync final files from HF Space" && git push
"""

import os
import shutil
import subprocess
import sys
import tempfile

SPACE_URL = "https://huggingface.co/spaces/finemtt1/Ignition-Coil-Simulation"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "CoilProject")

# Space 上的 .gitattributes 在 GitHub 這邊一直是存成沒有點的 gitattributes，維持原樣
RENAME = {".gitattributes": "gitattributes"}
SKIP_DIRS = {".git", "__pycache__"}


def clone_space():
    tmp = tempfile.mkdtemp(prefix="coil-space-")
    print("正在 clone %s ..." % SPACE_URL)
    subprocess.check_call(["git", "clone", "--depth", "1", SPACE_URL, tmp])
    return tmp


def main(src=None):
    if src is None:
        src = clone_space()
    src = os.path.abspath(src)
    if not os.path.isdir(src):
        raise SystemExit("找不到資料夾：%s" % src)

    os.makedirs(DEST, exist_ok=True)
    copied = []
    for base, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel_base = os.path.relpath(base, src)
        for name in files:
            if name.endswith((".pyc",)):
                continue
            rel = name if rel_base == "." else os.path.join(rel_base, name)
            out_name = RENAME.get(rel, rel)
            out = os.path.join(DEST, out_name)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copy2(os.path.join(base, name), out)
            copied.append(out_name)

    print("已同步 %d 個檔案到 %s：" % (len(copied), DEST))
    for c in sorted(copied):
        print("  " + c)

    try:
        diff = subprocess.run(["git", "-C", ROOT, "status", "--short", "CoilProject"],
                              capture_output=True, text=True, check=True).stdout
        print("\ngit 狀態（空白代表 GitHub 已經是最新版，不用再 commit）：")
        print(diff if diff.strip() else "  （沒有差異）")
    except Exception as e:  # git 不在 PATH 等情況，不影響同步結果
        print("（無法執行 git status：%s）" % e)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
