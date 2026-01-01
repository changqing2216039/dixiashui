# GitHub 自动部署指南

你提到的 "通过 GitHub 上传后部署"，通常是指 CI/CD 自动部署流程。
**注意：** Cloudflare Pages 仅支持静态网页，**无法直接运行** Python/Streamlit 应用。

以下是两种最符合 "GitHub 推送即部署" 体验的方案：

## 方案一：Streamlit Community Cloud (官方免费)

这是最简单、最官方的方案。

### 限制
⚠️ **数据丢失风险**：Streamlit Cloud 的文件系统是临时的。每次应用重启（或你推送新代码），本地的 `water_env.db` 都会被重置。
* **解决方法**：对于演示项目，这没问题。如果需要保存数据，建议后续升级代码连接到云数据库（如 Supabase）。

### 部署步骤
1. **上传代码到 GitHub**
   - 在 GitHub 创建一个新仓库（Public）。
   - 将本项目代码推送到该仓库。

2. **连接 Streamlit Cloud**
   - 访问 [share.streamlit.io](https://share.streamlit.io/) 并使用 GitHub 账号登录。
   - 点击 **New app**。
   - 选择刚才创建的 GitHub 仓库。
   - **Main file path** 填 `app.py`。
   - 点击 **Deploy!**。

---

## 方案二：Zeabur (推荐，支持数据库持久化)

Zeabur 是一个现代化的部署平台，支持从 GitHub 自动部署，并且**支持挂载存储卷**，可以完美解决 SQLite 数据库丢失的问题。它也支持绑定 Cloudflare 域名。

### 部署步骤

1. **上传代码到 GitHub** (同上)。

2. **在 Zeabur 创建项目**
   - 访问 [zeabur.com](https://zeabur.com/) 并登录。
   - 创建新项目。
   - 点击 **Deploy New Service** -> **Git**。
   - 选择你的 GitHub 仓库。

3. **配置持久化存储 (关键)**
   - 服务部署成功后，点击该服务。
   - 进入 **Settings** -> **Volumes**。
   - 点击 **Add Volume**。
   - **Mount Path** 填写 `/app/data` (这是我们代码里配置的持久化路径)。
   - 重启服务。

4. **绑定 Cloudflare 域名**
   - 在 Zeabur 服务页面点击 **Domain**。
   - 你可以使用 Zeabur 提供的免费域名，也可以绑定你自己在 Cloudflare 上的域名。

---

## 方案三：Render (备选)

Render 也是一个流行的部署平台，支持 Docker 和 Python。

1. 在 GitHub 上传代码。
2. 注册 [Render.com](https://render.com/)。
3. New -> **Web Service**。
4. 连接 GitHub 仓库。
5. Runtime 选择 **Docker** (因为我们有 Dockerfile)。
6. 免费版同样存在**重启后数据库丢失**的问题（除非升级到付费版添加 Disk）。

---

## 总结

| 平台 | 费用 | 数据库持久化 | 难度 | 推荐指数 |
| :--- | :--- | :--- | :--- | :--- |
| **Streamlit Cloud** | 免费 | ❌ (重启丢数据) | ⭐ (极简) | ⭐⭐⭐ (演示首选) |
| **Zeabur** | 有免费额度 | ✅ (支持挂载卷) | ⭐⭐ | ⭐⭐⭐⭐⭐ (生产首选) |
| **Cloudflare Pages** | 免费 | ❌ (不支持 Python) | ❌ | 不适用 |
| **Cloudflare Tunnel** | 免费 | ✅ (数据在本地) | ⭐⭐⭐ | ⭐⭐⭐⭐ (自托管首选) |
