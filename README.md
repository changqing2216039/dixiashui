---
title: 水环境污染解析解计算系统
emoji: 💧
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: 1.35.0
app_file: app.py
pinned: false
license: mit
---

# 水环境污染解析解计算系统 (Water Environment Prediction System)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io/cloud)

基于 Python 和 Streamlit 开发的地下水与地表水环境影响预测系统。

## 功能特点 (Features)

*   **地下水预测 (Groundwater)**: 
    *   基于 HJ610-2016 附录 D 解析解模型
    *   支持一维、二维、三维模型
    *   包含瞬时注入、连续注入、短时注入等多种情景
    *   支持浓度分布图、穿透曲线、交互式图表 (Plotly)
*   **地表水预测 (Surface Water)**:
    *   基于 HJ2.3-2018 附录 E 解析解模型
    *   一维稳态衰减模型 (河流)
*   **用户系统**:
    *   注册/登录
    *   会员计费 (模拟支付与点数消耗)
    *   历史记录保存与回看
    *   后台管理系统 (管理员)

## 如何运行 (How to Run)

### 本地运行 (Local)

1.  克隆仓库:
    ```bash
    git clone https://github.com/your-username/water-prediction-app.git
    cd water-prediction-app
    ```
2.  安装依赖:
    ```bash
    pip install -r requirements.txt
    ```
3.  运行应用:
    ```bash
    streamlit run app.py
    ```

### 部署到 Streamlit Cloud (免费)

1.  Fork 本仓库到您的 GitHub。
2.  访问 [Streamlit Cloud](https://streamlit.io/cloud)。
3.  点击 "New app"，选择本仓库。
4.  点击 "Deploy"。

**注意**: Streamlit Cloud 免费版不支持持久化存储。每次重启应用，注册的用户和历史记录将会重置。

## 文件说明

*   `app.py`: 主程序入口
*   `db_manager.py`: 数据库管理
*   `models/`: 核心计算模型代码
*   `requirements.txt`: Python 依赖库
*   `packages.txt`: Linux 系统依赖 (用于字体支持)

## License

MIT
