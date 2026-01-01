# Streamlit Community Cloud 免费部署指南

这是最简单、最官方的部署方式，完全免费，非常适合演示。

## ⚠️ 重要提示：数据持久化
Streamlit Cloud 的文件系统是临时的。这意味着：
*   **应用重启、休眠唤醒或更新代码后，本地的 SQLite 数据库 (`water_env.db`) 会被重置。**
*   **后果**：所有注册用户、充值记录、计算历史都会丢失，恢复到初始状态。
*   **建议**：此方式仅用于展示功能。如果需要长期运营并保存数据，请使用 Zeabur 或自建服务器。

---

## 准备工作 (我已经帮你做好了)

1.  **依赖文件**: 
    *   `requirements.txt`: 包含 streamlit, pandas 等 Python 库。
    *   `packages.txt`: 我已创建此文件并添加了 `fonts-wqy-zenhei`，确保**中文图表**在云端能正常显示。
2.  **代码适配**:
    *   `app.py`: 我已修改字体配置，优先使用 Linux 字体，防止乱码。

---

## 部署步骤

### 第一步：上传代码到 GitHub
1.  登录你的 GitHub 账号。
2.  创建一个新的 Public 仓库（例如命名为 `water-monitor`）。
3.  将你本地的所有代码上传到这个仓库。
    *   如果你不会使用 git 命令，可以直接在 GitHub 页面点击 "Upload files"，把所有文件拖进去提交。

### 第二步：在 Streamlit Cloud 部署
1.  访问 [share.streamlit.io](https://share.streamlit.io/)。
2.  使用 GitHub 账号登录。
3.  点击右上角的 **"New app"** 按钮。
4.  填写配置：
    *   **Repository**: 选择你刚才创建的 `water-monitor` 仓库。
    *   **Branch**: 通常是 `main` 或 `master`。
    *   **Main file path**: 填写 `app.py`。
5.  点击 **"Deploy!"**。

### 第三步：等待构建
*   Streamlit 会自动安装 `requirements.txt` 和 `packages.txt` 中的依赖。
*   等待 1-2 分钟，右侧就会出现你的应用界面。
*   如果不小心关掉了，可以在 Dashboard 重新打开。

---

## 常见问题

**Q: 图表中文显示方框/乱码？**
A: 请确认 `packages.txt` 文件已上传到 GitHub，且内容包含 `fonts-wqy-zenhei`。

**Q: 怎么看后台日志？**
A: 在应用界面的右下角点击 "Manage app"，展开底部的终端窗口即可查看报错信息。
