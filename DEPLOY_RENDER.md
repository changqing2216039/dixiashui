# 替代 Vercel 的最佳方案：Render 部署指南

**为什么不能用 Vercel？**
您可能记得 Trae 或其他前端工具默认支持 Vercel，这对于 React/Vue 等网页是正确的。
但是，**Streamlit 是一个需要持续运行的 Python 程序**，而 Vercel 是“无服务器”架构（运行 10 秒就断开），因此**Streamlit 无法在 Vercel 上运行**（会报错或白屏）。

**解决方案：使用 Render**
Render 是目前最像 Vercel 的替代品：
1.  **操作完全一样**：连接 GitHub -> 点击部署。
2.  **支持 Streamlit**：它提供真正的后台服务器。
3.  **有免费版**：个人使用完全免费。

---

## 部署步骤 (30秒搞定)

### 1. 上传代码到 GitHub
(如果您之前已经做过这一步，请跳过)
1.  去 GitHub 创建一个仓库。
2.  把本地文件上传上去。

### 2. 在 Render 创建服务
1.  访问 [Render.com](https://render.com/) 并注册（可以用 GitHub 登录）。
2.  点击右上角 **"New +"** -> 选择 **"Web Service"**。
3.  选择 **"Build and deploy from a Git repository"**。
4.  在列表中找到您的 GitHub 仓库，点击 **"Connect"**。

### 3. 确认配置
Render 会自动读取我为您准备的 `render.yaml` 文件，您几乎什么都不用填。
*   **Name**: 随便起个名字 (比如 `water-app`)。
*   **Instance Type**: 选 **"Free"** (免费版)。
*   点击底部的 **"Create Web Service"**。

### 4. 等待上线
*   等待几分钟，部署完成后，左上角会显示一个类似 `https://water-app.onrender.com` 的网址。
*   这就是您的永久访问地址！

---
**提示**：Render 的免费版在 15 分钟没人访问后会休眠，下次访问时启动需要等待 30-50 秒，这是正常的。
