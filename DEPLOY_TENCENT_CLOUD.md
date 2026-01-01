# 腾讯云部署指南 (Tencent Cloud Deployment Guide)

本指南将帮助您将《地下水/地表水环境预测系统》部署到腾讯云服务器 (CVM) 或轻量应用服务器 (Lighthouse)。

## 1. 准备工作

*   **购买服务器**：
    *   推荐购买 **轻量应用服务器 (Lighthouse)**，因为它配置简单，性价比高。
    *   操作系统推荐选择 **Ubuntu 20.04 LTS** 或 **Ubuntu 22.04 LTS** (CentOS 也可以，但以下命令以 Ubuntu 为例)。
    *   配置建议：至少 2核 CPU, 2GB 内存 (因为涉及到科学计算)。

*   **连接服务器**：
    *   使用腾讯云控制台的 "登录" 按钮，或使用 SSH 客户端 (如 Putty, Xshell) 连接。

## 2. 环境安装

在服务器终端中执行以下命令来安装 Python 和必要的工具：

```bash
# 更新软件源
sudo apt-get update

# 安装 Python3 和 pip
sudo apt-get install -y python3 python3-pip

# 验证安装
python3 --version
pip3 --version
```

## 3. 上传代码

您可以使用以下方法之一将代码上传到服务器：

*   **方法 A (推荐)**: 使用 SCP 或 SFTP 工具 (如 WinSCP, FileZilla) 将本地的项目文件夹上传到服务器的 `/home/ubuntu/water_app` 目录。
*   **方法 B**: 如果您使用 Git，可以将代码推送到仓库，然后在服务器上 `git clone`。

假设您已将代码上传到 `/home/ubuntu/water_app`。

## 4. 安装依赖

进入项目目录并安装 Python 依赖库：

```bash
cd /home/ubuntu/water_app

# 安装依赖 (建议使用清华源加速)
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 5. 运行应用

### 临时运行 (用于测试)
```bash
python3 -m streamlit run app.py
```
此时，您可以通过 `http://服务器公网IP:8501` 访问。如果无法访问，请检查防火墙 (见第 6 步)。按 `Ctrl+C` 停止。

### 长期后台运行 (使用 nohup)
为了让应用在关闭终端后继续运行：

```bash
nohup python3 -m streamlit run app.py > app.log 2>&1 &
```

### 长期后台运行 (使用 systemd - 推荐生产环境)
创建一个服务文件：

```bash
sudo nano /etc/systemd/system/water_app.service
```

粘贴以下内容 (请根据实际路径修改 `WorkingDirectory` 和 `ExecStart`)：

```ini
[Unit]
Description=Streamlit Water Prediction App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/water_app
ExecStart=/usr/bin/python3 -m streamlit run app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

保存并退出 (Ctrl+O, Enter, Ctrl+X)。然后启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start water_app
sudo systemctl enable water_app
```

## 6. 配置防火墙 (重要)

默认情况下，云服务器可能未开放 8501 端口。

1.  登录 **腾讯云控制台**。
2.  找到您的服务器实例，进入 **"防火墙"** 或 **"安全组"** 设置。
3.  点击 **"添加规则"**。
4.  添加一条规则：
    *   **协议端口**: TCP:8501
    *   **策略**: 允许
    *   **来源**: 0.0.0.0/0 (或 all)
5.  保存。

现在，您应该可以通过浏览器访问：`http://您的公网IP:8501`

## 7. 高级配置 (可选 - 使用 Docker)

如果您熟悉 Docker，可以直接构建镜像运行：

```bash
# 安装 Docker
sudo apt-get install -y docker.io

# 构建镜像
sudo docker build -t water-app .

# 运行容器
sudo docker run -d -p 8501:8501 --name my-water-app water-app
```

---
**常见问题：**
*   **Sqlite 错误**: 如果遇到数据库写入权限错误，请确保数据库文件 (`water_env.db`) 和所在目录对运行用户可写。 `chmod 777 water_env.db` (简单粗暴) 或 `chown ubuntu:ubuntu water_env.db`。
*   **中文字体乱码**: Linux 服务器可能缺少中文字体。您可以安装字体包：
    ```bash
    sudo apt-get install -y fonts-wqy-microhei
    ```
    然后在 `app.py` 中确认 matplotlib 配置已包含 'WenQuanYi Micro Hei' (我们代码中已配置常见中文字体，安装该包通常即可解决)。
