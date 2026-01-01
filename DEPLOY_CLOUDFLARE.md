# 使用 Cloudflare Tunnel 部署指南

由于本应用使用了 SQLite 数据库，需要持久化存储，因此不适合直接部署在无状态的 Cloudflare Pages 或 Workers 上。

最推荐的方案是：**在任意服务器（或本地电脑）运行 Docker，并通过 Cloudflare Tunnel 将服务安全地暴露到公网。**

这种方式的优点：
- **不需要公网 IP**：家里电脑也能做服务器。
- **不需要开端口**：无需在路由器设置端口映射，更安全。
- **免费**：Cloudflare Tunnel 是免费的。
- **自带 HTTPS**：自动配置 SSL 证书。

---

## 步骤 1：获取 Cloudflare Tunnel Token

1. 登录 [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)。
2. 点击左侧菜单 **Networks** -> **Tunnels**。
3. 点击 **Create a tunnel**。
4. 选择 **Cloudflared** 连接器类型，点击 **Next**。
5. 给隧道起个名字（例如 `water-monitor`），点击 **Save Tunnel**。
6. 在 "Install and run a connector" 页面，你会看到不同系统的安装命令。
7. **关键步骤**：找到 Docker 命令部分，复制 `--token` 后面的那串长字符。
   - 命令格式通常是：`tunnel run --token eyJhIjoi...`
   - 你只需要复制 `eyJhIjoi...` 这部分。

## 步骤 2：配置项目

1. 打开项目根目录下的 `docker-compose.yml` 文件。
2. 找到 `cloudflared` 服务下的 `TUNNEL_TOKEN` 环境变量。
3. 将刚才复制的 Token 粘贴进去。

```yaml
  cloudflared:
    ...
    environment:
      - TUNNEL_TOKEN=这里粘贴你的Token
```

## 步骤 3：启动服务

在项目根目录下运行终端命令：

```bash
docker-compose up -d
```

这会自动构建镜像并启动两个容器：应用容器和隧道容器。

## 步骤 4：配置公网域名

1. 回到 Cloudflare Tunnel 的配置页面，点击 **Next**。
2. 进入 **Public Hostnames** 标签页。
3. 点击 **Add a public hostname**。
4. 填写信息：
   - **Subdomain**：你想用的子域名（如 `water`）。
   - **Domain**：选择你的域名。
   - **Service**：
     - **Type**：`HTTP`
     - **URL**：`streamlit-app:8501`  (注意：这里必须填 `streamlit-app`，这是 docker-compose 里的服务名)
5. 点击 **Save hostname**。

## 完成！

现在，你可以通过 `https://water.你的域名.com` 访问你的应用了。

### 关于数据备份
所有数据（数据库文件）都保存在项目目录下的 `data` 文件夹中。请定期备份该文件夹。
