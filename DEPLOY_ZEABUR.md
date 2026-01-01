# Zeabur 部署指南 (支持数据持久化)

如果你希望应用在重启后**数据不丢失**（保留注册用户、历史记录），Zeabur 是一个非常好的选择。它支持从 GitHub 自动部署，并且可以挂载存储卷。

## 准备工作
同 Streamlit Cloud 部署，确保代码已上传到 GitHub。

## 部署步骤

### 1. 创建项目
1. 访问 [zeabur.com](https://zeabur.com/) 并登录（支持 GitHub 登录）。
2. 点击 **Create Project**，选择区域（推荐新加坡或日本，速度快）。
3. 点击 **Deploy New Service** -> **Git**。
4. 选择你的 GitHub 仓库。

### 2. 配置服务
Zeabur 会自动检测到这是 Python 项目并开始构建。
**重要**：默认情况下，Zeabur 也是无状态的。我们需要添加存储卷。

1. 等待服务部署成功（或者部署失败也没关系，我们需要先配置）。
2. 点击该服务卡片进入详情页。
3. 切换到 **Settings** 标签。
4. 找到 **Volumes** (挂载卷) 部分。
5. 点击 **Add Volume**。
6. **Mount Path** (挂载路径) 填写：`/app/data`
   * 注意：我们的代码 `db_manager.py` 会检测 `/app/data` 目录，如果有挂载，就会把数据库存在那里。
7. 点击保存，Zeabur 会自动重启服务。

### 3. 绑定域名
1. 切换到 **Domain** 标签。
2. 点击 **Generate Domain** 使用 Zeabur 提供的免费域名（例如 `your-app.zeabur.app`）。
3. 或者点击 **Custom Domain** 绑定你自己的域名（支持自动 HTTPS）。

### 4. 验证数据持久化
1. 访问你的应用，注册一个新用户。
2. 回到 Zeabur 控制台，点击 **Restart** 重启服务。
3. 再次访问应用，尝试登录。如果能登录成功，说明数据已成功保存！

---

## 费用说明
Zeabur 提供一定的免费额度（Serverless 模式），对于个人小项目通常够用。如果资源消耗过大，可能会转为付费模式（Developer Plan $5/月）。请关注 Zeabur 的最新计价策略。
