import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import os
import sys

# Add current directory to path to fix module import on Streamlit Cloud
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import db_manager
from models import groundwater_models, surfacewater_models
import json

# Configure Matplotlib for Chinese support
# Use WenQuanYi for Linux/Cloud, fallback to Windows fonts
plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'WenQuanYi Micro Hei', 'SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False # Solve the minus sign display problem

# Initialize Database
db_manager.init_db()

SESSION_FILE = ".user_session"

def check_auto_login():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
                user_id = data.get("user_id")
                username = data.get("username")
                role = data.get("role", "user") # Default to user
                if user_id and username:
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.session_state.role = role
                    return True
        except:
            pass
    return False

# Page Configuration
st.set_page_config(page_title="水环境污染解析解计算", layout="wide")

# Custom CSS to make buttons smaller/compact
st.markdown("""
<style>
    /* Make buttons more compact */
    div.stButton > button {
        padding: 0.25rem 0.5rem;
        line-height: 1.2;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if 'user_id' not in st.session_state:
    if not check_auto_login():
        st.session_state.user_id = None
    
if 'username' not in st.session_state:
    st.session_state.username = None

if 'role' not in st.session_state:
    st.session_state.role = 'user'

def login_page():
    st.title("用户登录")
    
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        username = st.text_input("用户名", key="login_user")
        password = st.text_input("密码", type="password", key="login_pass")
        remember_me = st.checkbox("记住我 (下次自动登录)")
        
        if st.button("登录"):
            user_data = db_manager.authenticate_user(username, password)
            if user_data:
                st.session_state.user_id = user_data['id']
                st.session_state.username = username
                st.session_state.role = user_data['role']
                
                if remember_me:
                    try:
                        with open(SESSION_FILE, "w") as f:
                            json.dump({"user_id": user_data['id'], "username": username, "role": user_data['role']}, f)
                    except Exception as e:
                        print(f"Failed to save session: {e}")
                        
                st.success("登录成功！")
                st.rerun()
            else:
                st.error("用户名或密码错误，或账户被禁用")
                
    with tab2:
        new_user = st.text_input("用户名", key="reg_user")
        new_pass = st.text_input("密码", type="password", key="reg_pass")
        if st.button("注册"):
            if new_user and new_pass:
                if db_manager.register_user(new_user, new_pass):
                    st.success("注册成功，请登录")
                else:
                    st.error("用户名已存在")
            else:
                st.warning("请输入用户名和密码")

def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.role = None
    if os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
        except:
            pass
    st.rerun()

def get_ui_state(prefix_list):
    """Capture session state variables starting with given prefixes"""
    state = {}
    # Also include specific global keys
    global_keys = ["project_name"]
    
    # Capture prefixed keys
    for key in st.session_state:
        for prefix in prefix_list:
            if key.startswith(prefix):
                state[key] = st.session_state[key]
                break
    
    # Capture global keys if they exist
    for key in global_keys:
        if key in st.session_state:
            state[key] = st.session_state[key]
            
    return state

def load_params_callback(hist_id):
    """Callback to load parameters from history"""
    detail = db_manager.get_calculation_detail(hist_id)
    if detail and "parameters" in detail:
        saved_params = detail["parameters"]
        if "_ui_state" in saved_params:
            for k, v in saved_params["_ui_state"].items():
                st.session_state[k] = v
            # Note: Success message cannot be shown in callback easily as it might be cleared on rerun
        else:
            # For older records without UI state, we can't do much automatically
            pass

def load_history_sidebar(category_filter):
    """Render history loader in sidebar"""
    if not st.session_state.user_id:
        return

    st.divider()
    st.subheader("历史参数读取")
    
    # Get history
    history = db_manager.get_user_calculations(st.session_state.user_id)
    # Filter by category (e.g., "Groundwater" or "Surface Water")
    filtered_history = [h for h in history if category_filter in h[2]]
    
    if filtered_history:
        options = {h[0]: f"{h[3]} - {h[1]}" for h in filtered_history}
        selected_hist_id = st.selectbox("选择历史记录", options.keys(), format_func=lambda x: options[x], key=f"hist_sel_{category_filter}")
        
        # Use callback to load parameters BEFORE widget instantiation on next run
        # But wait, callback runs BEFORE the script reruns. 
        # So when we click, callback runs, updates session_state, then script reruns.
        # This avoids "modifying instantiated widget" error because on rerun, 
        # widgets will pick up the new values from session_state.
        st.button("读取参数", on_click=load_params_callback, args=(selected_hist_id,), key=f"btn_load_{category_filter}")
        
    else:
        st.caption("暂无相关历史记录")

def plot_3d_isosurface(res, x_range, y_range, z_range, title):
    X, Y, Z = np.meshgrid(x_range, y_range, z_range, indexing='xy')
    
    fig = go.Figure(data=go.Volume(
        x=X.flatten(),
        y=Y.flatten(),
        z=Z.flatten(),
        value=res.flatten(),
        isomin=np.min(res) + 1e-10,
        isomax=np.max(res),
        opacity=0.1, # needs to be small to see through all surfaces
        surface_count=20, # needs to be a large number for good volume rendering
    ))
    fig.update_layout(title=title, scene=dict(
        xaxis_title='X (m)',
        yaxis_title='Y (m)',
        zaxis_title='Z (m)'
    ))
    return fig

# --- Admin Page ---
def admin_page():
    st.title("后台管理系统")
    if st.session_state.role != 'admin':
        st.error("无权访问")
        return

    tab1, tab2, tab3, tab4 = st.tabs(["📊 仪表盘", "👥 用户管理", "💰 财务管理", "⚙️ 系统设置"])

    with tab1:
        st.subheader("概览")
        users = db_manager.get_all_users()
        payments = db_manager.get_all_payments()
        
        total_users = len(users)
        total_revenue = sum([p[2] for p in payments if p[5] == 'approved']) # p[2] is amount, p[5] is status
        pending_payments = len([p for p in payments if p[5] == 'pending'])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("总用户数", total_users)
        c2.metric("总收入 (元)", f"{total_revenue:,.2f}")
        c3.metric("待处理支付", pending_payments)

    with tab2:
        st.subheader("用户列表")
        # id, username, role, status, created_at
        df_users = pd.DataFrame(users, columns=["ID", "用户名", "角色", "状态", "注册时间"])
        st.dataframe(df_users, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            with st.expander("管理用户状态"):
                target_user_id = st.number_input("输入用户ID进行操作", min_value=1, step=1, key="status_uid")
                new_status = st.selectbox("设置状态", ["active", "banned"])
                if st.button("更新用户状态"):
                    db_manager.update_user_status(target_user_id, new_status)
                    st.success(f"用户 ID {target_user_id} 状态已更新为 {new_status}")
                    st.rerun()
        
        with c2:
            with st.expander("充值/调整次数"):
                target_uid_usage = st.number_input("输入用户ID", min_value=1, step=1, key="usage_uid")
                delta_usage = st.number_input("增加/减少次数 (负数减少)", value=10, step=1)
                if st.button("更新剩余次数"):
                    db_manager.admin_update_usage(target_uid_usage, int(delta_usage))
                    st.success(f"用户 ID {target_uid_usage} 次数已更新")
                    # No rerun needed strictly, but good for feedback if we showed the list with usage
                    # But get_all_users doesn't return usage yet. It's fine.

    with tab3:
        st.subheader("支付记录")
        # id, username, amount, method, trans_id, status, created_at
        if payments:
            df_payments = pd.DataFrame(payments, columns=["ID", "用户名", "金额", "支付方式", "交易号", "状态", "时间"])
            st.dataframe(df_payments, use_container_width=True)
            
            with st.expander("审核支付"):
                p_id = st.number_input("输入支付记录ID", min_value=1, step=1)
                action = st.selectbox("操作", ["approved", "rejected"])
                if st.button("提交审核"):
                    db_manager.update_payment_status(p_id, action)
                    st.success(f"支付记录 {p_id} 已更新为 {action}")
                    st.rerun()
        else:
            st.info("暂无支付记录")

    with tab4:
        st.subheader("收款设置")
        # Load existing
        wechat_qr = db_manager.get_system_setting("wechat_qr")
        alipay_qr = db_manager.get_system_setting("alipay_qr")
        current_desc = db_manager.get_system_setting("payment_description")
        
        # Contact Info
        contact_qq = db_manager.get_system_setting("contact_qq", "")
        contact_wx_qr = db_manager.get_system_setting("contact_wx_qr", "")
        
        new_desc = st.text_area("通用收款说明 (银行卡号等)", value=current_desc)
        
        st.markdown("---")
        st.write("### 联系方式设置")
        c_qq, c_wx = st.columns(2)
        with c_qq:
            new_contact_qq = st.text_input("联系QQ", value=contact_qq)
        with c_wx:
            st.write("联系微信二维码")
            if contact_wx_qr:
                try:
                    st.image(contact_wx_qr, width=100)
                except: pass
            up_contact_wx = st.file_uploader("上传联系微信二维码", type=["png", "jpg", "jpeg"], key="up_contact_wx")
        
        st.markdown("---")
        st.write("### 收款二维码设置")
        
        # Ensure upload directory exists
        UPLOAD_DIR = "uploaded_qr"
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR)
            
        c1, c2 = st.columns(2)
        with c1:
            st.write("#### 微信支付")
            if wechat_qr:
                try:
                    st.image(wechat_qr, width=150, caption="当前使用中")
                except:
                    st.warning("图片无法加载")
            
            up_wx = st.file_uploader("上传微信二维码", type=["png", "jpg", "jpeg"], key="up_wx")
            new_wechat_path = st.text_input("或手动输入链接/路径", value=wechat_qr, key="txt_wx")

        with c2:
            st.write("#### 支付宝")
            if alipay_qr:
                try:
                    st.image(alipay_qr, width=150, caption="当前使用中")
                except:
                    st.warning("图片无法加载")
                    
            up_ali = st.file_uploader("上传支付宝二维码", type=["png", "jpg", "jpeg"], key="up_ali")
            new_alipay_path = st.text_input("或手动输入链接/路径", value=alipay_qr, key="txt_ali")
            
        if st.button("保存设置"):
            import time
            
            # Handle WeChat Upload
            final_wechat = new_wechat_path
            if up_wx is not None:
                # Generate unique filename
                ext = up_wx.name.split('.')[-1]
                fname = f"wechat_{int(time.time())}.{ext}"
                fpath = os.path.join(UPLOAD_DIR, fname)
                with open(fpath, "wb") as f:
                    f.write(up_wx.getbuffer())
                final_wechat = fpath
                
            # Handle Alipay Upload
            final_alipay = new_alipay_path
            if up_ali is not None:
                ext = up_ali.name.split('.')[-1]
                fname = f"alipay_{int(time.time())}.{ext}"
                fpath = os.path.join(UPLOAD_DIR, fname)
                with open(fpath, "wb") as f:
                    f.write(up_ali.getbuffer())
                final_alipay = fpath
                
            # Handle Contact WeChat Upload
            final_contact_wx = contact_wx_qr
            if up_contact_wx is not None:
                ext = up_contact_wx.name.split('.')[-1]
                fname = f"contact_wx_{int(time.time())}.{ext}"
                fpath = os.path.join(UPLOAD_DIR, fname)
                with open(fpath, "wb") as f:
                    f.write(up_contact_wx.getbuffer())
                final_contact_wx = fpath

            db_manager.set_system_setting("payment_description", new_desc)
            db_manager.set_system_setting("wechat_qr", final_wechat)
            db_manager.set_system_setting("alipay_qr", final_alipay)
            db_manager.set_system_setting("contact_qq", new_contact_qq)
            db_manager.set_system_setting("contact_wx_qr", final_contact_wx)
            
            st.success("设置已保存")
            st.rerun()

# --- Membership Page ---
def membership_page():
    st.title("会员充值中心")
    
    desc = db_manager.get_system_setting("payment_description", "请联系管理员获取支付方式")
    wechat_qr = db_manager.get_system_setting("wechat_qr", "")
    alipay_qr = db_manager.get_system_setting("alipay_qr", "")
    
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.info("### 支付方式")
        st.markdown(desc)
        
        pay_tabs = st.tabs(["微信支付", "支付宝"])
        with pay_tabs[0]:
            if wechat_qr:
                try:
                    if wechat_qr.startswith("http"): st.image(wechat_qr, width=300)
                    elif os.path.exists(wechat_qr): st.image(wechat_qr, width=300)
                    else: st.warning("微信二维码无法加载")
                except: st.warning("加载失败")
            else:
                st.caption("未配置微信二维码")
                
        with pay_tabs[1]:
            if alipay_qr:
                try:
                    if alipay_qr.startswith("http"): st.image(alipay_qr, width=300)
                    elif os.path.exists(alipay_qr): st.image(alipay_qr, width=300)
                    else: st.warning("支付宝二维码无法加载")
                except: st.warning("加载失败")
            else:
                st.caption("未配置支付宝二维码")
                
    with c2:
        st.markdown("### 提交支付凭证")
        amount = st.number_input("支付金额 (元)", min_value=0.01, value=100.0, step=10.0)
        method = st.selectbox("支付方式", ["支付宝", "微信支付", "银行转账"])
        trans_id = st.text_input("交易单号/转账备注")
        
        if st.button("提交支付记录"):
            if trans_id:
                db_manager.create_payment(st.session_state.user_id, amount, method, trans_id)
                st.success("支付记录已提交，请等待管理员审核！")
            else:
                st.error("请输入交易单号")
                
    st.divider()
    st.subheader("我的充值记录")
    # Filter payments for current user (quick hack: fetch all and filter in python, optimal for small app)
    all_payments = db_manager.get_all_payments()
    my_payments = [p for p in all_payments if p[1] == st.session_state.username] # username is index 1 in get_all_payments query result
    
    if my_payments:
        df_my = pd.DataFrame(my_payments, columns=["ID", "用户名", "金额", "支付方式", "交易号", "状态", "时间"])
        # Hide ID and Username
        st.dataframe(df_my[["金额", "支付方式", "交易号", "状态", "时间"]], use_container_width=True)
    else:
        st.info("暂无记录")

def user_info_page():
    st.title("用户信息")
    
    if not st.session_state.user_id:
        st.warning("请先登录")
        return
        
    info = db_manager.get_user_full_info(st.session_state.user_id)
    if info:
        st.write(f"### 用户名: {info['username']}")
        st.write(f"### 剩余使用次数: {info['usage_left']}")
        st.write(f"### 登录次数: {info['login_count']}")
        st.write(f"### 注册时间: {info['created_at']}")
        st.write(f"### 最后一次登录时间: {info['last_login_at']}")
        st.write(f"### 购买次数: {info['purchase_count']}")
    else:
        st.error("无法获取用户信息")

def contact_page():
    st.title("联系管理员")
    
    contact_qq = db_manager.get_system_setting("contact_qq", "未设置")
    contact_wx_qr = db_manager.get_system_setting("contact_wx_qr", "")
    
    st.info(f"### 管理员QQ: {contact_qq}")
    
    st.write("### 管理员微信")
    if contact_wx_qr:
        try:
            if contact_wx_qr.startswith("http") or os.path.exists(contact_wx_qr):
                st.image(contact_wx_qr, width=300, caption="扫码添加管理员微信")
            else:
                st.warning("二维码无法加载")
        except:
            st.warning("二维码加载失败")
    else:
        st.caption("未设置微信二维码")

# --- Existing Pages (Collapsed for brevity in thought, but included in full write) ---
# ... (Keeping groundwater_page, surfacewater_page, history_page exactly as is) ...

def groundwater_page():
    st.header("地下水污染预测 (HJ610-2016 附录D)")
    
    # Model Selection Tabs
    tab1, tab2, tab3 = st.tabs(["一维模型 (1D)", "二维模型 (2D)", "三维模型 (3D)"])
    
    params = {}
    model_type = ""
    res = None
    x_range = None
    y_range = None
    z_range = None
    
    # Common Inputs
    with st.sidebar:
        st.subheader("基本信息")
        project_name = st.text_input("项目名称", value="默认项目", key="project_name")
        
        if st.button("保存参数", key="btn_save_gw", help="保存当前参数设置", use_container_width=True):
            if st.session_state.user_id:
                # Save only UI state
                ui_params = {"_ui_state": get_ui_state(["1d_", "2d_", "3d_"])}
                db_manager.save_calculation(
                    st.session_state.user_id,
                    project_name,
                    "Groundwater - Parameters",
                    ui_params,
                    {}
                )
                st.toast("参数已保存到数据库！")
            else:
                st.toast("请先登录", icon="⚠️")
        
        load_history_sidebar("Groundwater")
        st.divider()
    
    with tab1:
        st.subheader("一维模型")
        sub_model = st.radio("选择情景", ["瞬时注入 (Instantaneous)", "连续注入 (Continuous)", "短时注入 (Short-term Release)"], key="1d_sub")
        model_type = f"1D - {sub_model}"
        
        col1, col2 = st.columns(2)
        with col1:
            # Unified 1D Inputs
            with st.expander("基本参数输入", expanded=True):
                c1, c2 = st.columns(2)
                
                if "Short-term" in sub_model:
                    with c1:
                        C0 = st.number_input("初始浓度 C0 (mg/L)", value=100.0, key="1d_C0_short")
                        u = st.number_input("孔隙流速 u (m/d)", value=0.1, key="1d_u_short")
                        limit_val = st.number_input("评价标准 (mg/L)", value=0.5, key="1d_limit_short")
                    with c2:
                        DL = st.number_input("纵向弥散系数 DL (m²/d)", value=0.5, key="1d_DL_short")
                        duration = st.number_input("泄漏持续时间 (d)", value=10.0, key="1d_dur")
                        lambda_coef = st.number_input("反应系数λ (1/d)", value=0.0, key="1d_lambda_short")
                        detection_limit = st.number_input("检出限 (mg/L)", value=0.05, key="1d_det_limit_short")
                    params = {
                        "C0": C0, "DL": DL, "u": u, "duration": duration, "lambda_coef": lambda_coef,
                        "limit_val": limit_val, "detection_limit": detection_limit
                    }
                    
                    st.markdown("### 一维短时泄漏模型")
                    with st.expander("模型说明：污染物短时注入", expanded=True):
                        st.write("在一维短时注入污染物条件下，注入条件可表示为：")
                        st.latex(r"C(x,t)|_{x=0} = \begin{cases} C_0 & 0 < t \le t_0 \\ 0 & t > t_0 \end{cases}")
                        st.write("式中，$t_0$ 为注入污染物时间。此问题的解为：")
                        st.latex(r"C(x,t) = \frac{C_0}{2} \left[ \text{erfc}\left(\frac{x-ut}{2\sqrt{D_L t}}\right) - \text{erfc}\left(\frac{x-u(t-t_0)}{2\sqrt{D_L(t-t_0)}}\right) \right]")
                        st.write(r"注：上式为不考虑化学反应($\lambda=0$)时的简化形式。当考虑反应系数时，模型采用持续注入模型的叠加原理计算。")
                        
                elif "Continuous" in sub_model:
                    with c1:
                        C0 = st.number_input("初始浓度 C0 (mg/L)", value=100.0, key="1d_C0_cont")
                        u = st.number_input("孔隙流速 u (m/d)", value=0.1, key="1d_u_cont")
                        limit_val = st.number_input("评价标准 (mg/L)", value=0.5, key="1d_limit_cont")
                    with c2:
                        DL = st.number_input("纵向弥散系数 DL (m²/d)", value=0.5, key="1d_DL_cont")
                        lambda_coef = st.number_input("反应系数λ (1/d)", value=0.0, key="1d_lambda_cont")
                        detection_limit = st.number_input("检出限 (mg/L)", value=0.05, key="1d_det_limit_cont")
                    params = {
                        "C0": C0, "DL": DL, "u": u, "lambda_coef": lambda_coef,
                        "limit_val": limit_val, "detection_limit": detection_limit
                    }
                    
                    st.markdown("### 一维持续泄漏模型")
                    with st.expander("模型说明：污染物连续注入", expanded=True):
                        st.latex(r"C(x,t) = \frac{C_0}{2} \left\{ \exp\left(\frac{(u-w)x}{2D_L}\right) \text{erfc}\left(\frac{x-wt}{2\sqrt{D_L t}}\right) + \exp\left(\frac{(u+w)x}{2D_L}\right) \text{erfc}\left(\frac{x+wt}{2\sqrt{D_L t}}\right) \right\}")
                        st.latex(r"w = \sqrt{u^2 + 4\lambda D_L}")
                        st.write(r"式中：$C_0$为初始浓度，$u$为流速，$D_L$为弥散系数，$\lambda$为反应系数，$x$为距离，$t$为时间。")
                        st.write(r"当不考虑反应系数，即 $\lambda=0$ 时，模型变为：")
                        st.latex(r"C(x,t) = \frac{C_0}{2} \left[ \text{erfc}\left(\frac{x-ut}{2\sqrt{D_L t}}\right) + \exp\left(\frac{ux}{D_L}\right) \text{erfc}\left(\frac{x+ut}{2\sqrt{D_L t}}\right) \right]")
                    
                elif "Instantaneous" in sub_model:
                    with c1:
                        M = st.number_input("污染物泄漏质量m (g)", value=100.0, key="1d_M")
                        u = st.number_input("地下水实际流速u (m/d)", value=0.1, key="1d_u_inst")
                        ne = st.number_input("含水层有效孔隙度n", value=0.3, key="1d_ne")
                        limit_val = st.number_input("评价标准 (mg/L)", value=0.5, key="1d_limit")
                    with c2:
                        lambda_coef = st.number_input("反应系数λ (1/d)", value=0.0, key="1d_lambda")
                        DL = st.number_input("纵向弥散系数DL (m²/d)", value=0.5, key="1d_DL_inst")
                        W = st.number_input("横截面积W (m²)", value=2.0, key="1d_W")
                        detection_limit = st.number_input("检出限 (mg/L)", value=0.05, key="1d_det_limit")
                    params = {
                        "M": M, "ne": ne, "W": W, "DL": DL, "u": u, "lambda_coef": lambda_coef,
                        "limit_val": limit_val, "detection_limit": detection_limit
                    }
                    
                    st.markdown("### 一维瞬时泄漏模型")
                    with st.expander("模型说明：污染物瞬时注入", expanded=True):
                        st.latex(r"C(x,t) = \frac{m}{2n W \sqrt{\pi D_L t}} \exp\left[ -\lambda t - \frac{(x - ut)^2}{4 D_L t} \right]")
                        st.markdown(r"""
                        式中：$m$ 为污染物泄漏质量，g；$W$ 为横截面面积，m^2；$n$ 为有效孔隙度；$u$ 为地下水实际流速，m/d；$D_L$ 为弥散系数，m^2/d；$\lambda$ 为反应系数，1/d；$x$ 为预测点位置，m，$t$ 为预测时间，d。
                        当不考虑反应系数，即 $\lambda=0$ 时，模型变为：
                        """)
                        st.latex(r"C(x,t) = \frac{m}{2n W \sqrt{\pi D_L t}} \exp\left[ - \frac{(x - ut)^2}{4 D_L t} \right]")
            
            with st.expander("预测方案设置", expanded=True):
                # Scheme Selection
                scheme_1d = st.radio("方案选择", ["方案一：指定时间不同位置计算", "方案二：指定位置不同时间计算"], horizontal=True, key="1d_scheme")
                
                if "方案一" in scheme_1d:
                    st.markdown("**方案一：计算指定时刻不同距离处的浓度，绘制曲线图，计算超标距离**")
                    t_str = st.text_input("预测时间t (天) [逗号分隔]", value="100, 200, 300, 500, 1000", key="1d_t_str")
                    
                    c1, c2, c3 = st.columns(3)
                    with c1: x_min = st.number_input("预测起始范围Xmin (m)", value=-50.0, key="1d_xmin")
                    with c2: x_max = st.number_input("预测最大范围Xmax (m)", value=100.0, key="1d_xmax")
                    with c3: dx = st.number_input("x剖分间距", value=1.0, key="1d_dx")
                    
                    params.update({
                        "t_str": t_str, "x_min": x_min, "x_max": x_max, "dx": dx,
                        "scheme": "scheme1"
                    })
                else:
                    st.markdown("**方案二：计算指定位置不同时刻的浓度，绘制曲线图，计算超标时间**")
                    x_str = st.text_input("预测位置 (m) [逗号分隔]", value="5, 10, 15, 20, 30, 40, 50", key="1d_x_str")
                    t_max = st.number_input("预测最大时间Tmax (天)", value=1000.0, key="1d_tmax")
                    
                    params.update({
                        "x_str": x_str, "t_max": t_max,
                        "scheme": "scheme2"
                    })
                
        if st.button("计算一维模型"):
            # Prepare for consumption check
            try:
                times_to_check = []
                if params.get("scheme") == "scheme1":
                     times_to_check = [float(x.strip()) for x in params["t_str"].split(',') if x.strip()]
                elif params.get("scheme") == "scheme2":
                     times_to_check = [params["t_max"]]
                
                max_time_req = max(times_to_check) if times_to_check else 0
            except:
                max_time_req = 99999 # Fail safe if parse error, let calculation logic handle error but assume high for safety

            # Check logic: Free if <= 300 days. Else consume usage.
            if st.session_state.user_id:
                if max_time_req <= 300:
                    st.success("预测时间 ≤ 300天，本次免费！")
                else:
                    if not db_manager.consume_usage(st.session_state.user_id):
                        st.error("剩余使用次数不足，请充值！(超过300天的预测需要消耗次数)")
                        st.stop()
                    else:
                        st.info("已消耗 1 次预测次数")
            else:
                 # Not logged in limitations
                 if max_time_req > 365:
                      st.error("未登录用户最大预测时间不能超过365天")
                      st.stop()

            def calculate_1d_dispatch(t, x):
                if "Short-term" in sub_model:
                    return groundwater_models.calculate_1d_short_release(
                        params["C0"], params["DL"], params["u"], t, params["duration"], x, params["lambda_coef"]
                    )
                elif "Continuous" in sub_model:
                    return groundwater_models.calculate_1d_continuous(
                        params["C0"], params["DL"], params["u"], t, x, params["lambda_coef"]
                    )
                elif "Instantaneous" in sub_model:
                    return groundwater_models.calculate_1d_instantaneous(
                        params["M"], params["ne"], params["W"], params["DL"], params["u"], t, x, params["lambda_coef"]
                    )

            res_dict = {}
            summary_data = []
            
            if params.get("scheme") == "scheme1":
                try:
                    times = [float(x.strip()) for x in params["t_str"].split(',') if x.strip()]
                except:
                    st.error("时间格式错误")
                    st.stop()
                
                x_range = np.arange(params["x_min"], params["x_max"] + params["dx"], params["dx"])
                
                if not st.session_state.user_id and max(times) > 365:
                    st.error("未登录或权限不足，预测时间不能大于365天!")
                
                for t_val in times:
                    res = calculate_1d_dispatch(t_val, x_range)
                    res_dict[t_val] = res
                    
                    max_c = np.max(res)
                    
                    exceed_mask = res > params["limit_val"]
                    if np.any(exceed_mask):
                        x_ex = x_range[exceed_mask]
                        exceed_str = f"{x_ex[0]:.1f}m - {x_ex[-1]:.1f}m"
                    else:
                        exceed_str = "未超标"
                        
                    affect_mask = res > params["detection_limit"]
                    if np.any(affect_mask):
                        x_aff = x_range[affect_mask]
                        affect_str = f"{x_aff[0]:.1f}m - {x_aff[-1]:.1f}m"
                    else:
                        affect_str = "无影响"
                        
                    summary_data.append({
                        "时间(天)": t_val,
                        "最大浓度(mg/L)": float(f"{max_c:.3f}"),
                        "超标距离": exceed_str,
                        "影响距离": affect_str
                    })
                
                with col2:
                    st.subheader("方案一计算结果如下：")
                    
                    tabs_1d = st.tabs(["曲线图", "数据表格", "结果统计"])
                    
                    with tabs_1d[0]:
                        fig = go.Figure()
                        for t_val in times:
                            fig.add_trace(go.Scatter(x=x_range, y=res_dict[t_val], mode='lines', name=f't={t_val}天', line=dict(dash='dash')))
                        
                        fig.add_hline(y=params["limit_val"], line_color="salmon", annotation_text="标准值")
                        fig.add_hline(y=params["detection_limit"], line_color="mediumseagreen", annotation_text="检出限")
                        
                        fig.update_layout(xaxis_title="距离(m)", yaxis_title="浓度(mg/L)")
                        st.plotly_chart(fig)
                        
                    with tabs_1d[1]:
                        df_res = pd.DataFrame({"距离(m)": x_range})
                        for t_val in times:
                            df_res[f"t={t_val}天"] = res_dict[t_val]
                        
                        def highlight_1d(val):
                            if isinstance(val, (int, float)):
                                if val > params["limit_val"]: return 'color: red'
                                elif val > params["detection_limit"]: return 'color: blue'
                                else: return 'color: green'
                            return ''
                            
                        st.dataframe(df_res.style.map(highlight_1d, subset=[f"t={t}天" for t in times]), use_container_width=True)
                        st.caption("注：红色表示大于标准值，蓝色表示大于检出限，绿色表示小于检出限")
                        
                    with tabs_1d[2]:
                        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
                        st.warning("注：超标距离和影响距离是根据计算范围内的数据进行统计，若最大计算范围仍然超标或超过检出限，则需扩大计算范围以便获得更准确的超标距离和影响距离。")

            elif params.get("scheme") == "scheme2":
                try:
                    x_locs = [float(x.strip()) for x in params["x_str"].split(',') if x.strip()]
                except:
                    st.error("位置格式错误")
                    st.stop()
                    
                if not st.session_state.user_id and params["t_max"] > 365:
                    st.error("未登录或权限不足，预测时间不能大于365天!")
                    
                t_range = np.linspace(1, params["t_max"], 100)
                
                res_dict_s2 = {}
                
                for x_val in x_locs:
                    c_series = []
                    for t_val in t_range:
                        c = calculate_1d_dispatch(t_val, np.array([x_val]))
                        c_series.append(c[0])
                    
                    c_series = np.array(c_series)
                    res_dict_s2[x_val] = c_series
                    
                    max_c = np.max(c_series)
                    
                    exceed_mask = c_series > params["limit_val"]
                    if np.any(exceed_mask):
                        t_ex = t_range[exceed_mask]
                        exceed_str = f"{t_ex[0]:.0f}天 - {t_ex[-1]:.0f}天"
                    else:
                        exceed_str = "未超标"
                        
                    affect_mask = c_series > params["detection_limit"]
                    if np.any(affect_mask):
                        t_aff = t_range[affect_mask]
                        affect_str = f"{t_aff[0]:.0f}天 - {t_aff[-1]:.0f}天"
                    else:
                        affect_str = "无影响"
                        
                    summary_data.append({
                        "位置(m)": x_val,
                        "最大浓度(mg/L)": float(f"{max_c:.3f}"),
                        "超标时间": exceed_str,
                        "影响时间": affect_str
                    })
                    
                with col2:
                    st.subheader("方案二计算结果如下：")
                    
                    tabs_1d_s2 = st.tabs(["曲线图", "数据表格", "结果统计"])
                    
                    with tabs_1d_s2[0]:
                        fig = go.Figure()
                        for x_val in x_locs:
                            fig.add_trace(go.Scatter(x=t_range, y=res_dict_s2[x_val], mode='lines', name=f'x={x_val}m', line=dict(dash='dash')))
                        
                        fig.add_hline(y=params["limit_val"], line_color="salmon", annotation_text="标准值")
                        fig.add_hline(y=params["detection_limit"], line_color="mediumseagreen", annotation_text="检出限")
                        
                        fig.update_layout(xaxis_title="时间(天)", yaxis_title="浓度(mg/L)")
                        st.plotly_chart(fig)
                        
                    with tabs_1d_s2[1]:
                        t_display = np.linspace(1, params["t_max"], 10, dtype=int)
                        df_res_s2 = pd.DataFrame({"时间(天)": t_display})
                        
                        for x_val in x_locs:
                            c_disp = []
                            for t_d in t_display:
                                c = calculate_1d_dispatch(t_d, np.array([x_val]))
                                c_disp.append(c[0])
                            df_res_s2[f"x={x_val}m"] = c_disp
                            
                        def highlight_1d_s2(val):
                            if isinstance(val, (int, float)):
                                if val > params["limit_val"]: return 'color: red'
                                elif val > params["detection_limit"]: return 'color: blue'
                                else: return 'color: green'
                            return ''
                            
                        st.dataframe(df_res_s2.style.map(highlight_1d_s2, subset=[f"x={x}m" for x in x_locs]), use_container_width=True)
                        st.caption("注：红色表示大于标准值，蓝色表示大于检出限，绿色表示小于检出限")
                        
                    with tabs_1d_s2[2]:
                        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
                        st.warning("注：超标时间和影响时间是根据预测时间范围内的数据进行统计，若最大时间仍然超标或超过检出限，则需扩大预测时间范围以便获得更准确的超标时间和影响时间。")

    with tab2:
        st.subheader("二维模型")
        sub_model = st.radio("选择情景", [
            "点源瞬时注入 (Point Instantaneous)", 
            "点源连续注入 (Point Continuous)", 
            "点源短时注入 (Point Short-term)",
            "面源瞬时注入 (Area Instantaneous)",
            "面源连续注入 (Area Continuous)"
        ], key="2d_sub")
        model_type = f"2D - {sub_model}"
        
        col1, col2 = st.columns(2)
        with col1:
            # Unified Parameter Input Area
            with st.expander("基本参数输入", expanded=True):
                if "Point Short-term" in sub_model:
                    # Custom layout for Point Short-term
                    c1, c2, c3 = st.columns(3)
                    with c1: m_val = st.number_input("污染物泄漏质量m (g/d)", value=10.0, key="2d_m_short")
                    with c2: ne = st.number_input("含水层有效孔隙度n", value=0.3, key="2d_ne_short")
                    with c3: duration = st.number_input("泄漏时间t0 (d)", value=60.0, key="2d_t0_short")
                    
                    c1, c2, c3 = st.columns(3)
                    with c1: H = st.number_input("含水层厚度b (m)", value=2.0, key="2d_b_short")
                    with c2: DL = st.number_input("纵向弥散系数DL (m^2/d)", value=0.1, key="2d_DL_short")
                    with c3: limit_val = st.number_input("评价标准 (mg/L)", value=0.5, key="2d_limit_short")
                    
                    c1, c2, c3 = st.columns(3)
                    with c1: u = st.number_input("地下水实际流速u (m/d)", value=0.01, format="%.4f", key="2d_u_short")
                    with c2: DT = st.number_input("横向弥散系数DT (m^2/d)", value=0.01, key="2d_DT_short")
                    with c3: detection_limit = st.number_input("检出限 (mg/L)", value=0.05, key="2d_det_limit_short")
                    
                    st.markdown("### 二维点源短时泄漏模型")
                    with st.expander("模型说明：点源短时注入", expanded=True):
                        st.latex(r"c(x,y,t) = \begin{cases} \frac{m}{4\pi n b \sqrt{D_L D_T}} \int_0^t \exp \left( -\frac{(x-u\tau)^2}{4D_L\tau} - \frac{y^2}{4D_T\tau} \right) \frac{d\tau}{\tau} & t \le t_0 \\ \frac{m}{4\pi n b \sqrt{D_L D_T}} \int_{t-t_0}^t \exp \left( -\frac{(x-u\tau)^2}{4D_L\tau} - \frac{y^2}{4D_T\tau} \right) \frac{d\tau}{\tau} & t > t_0 \end{cases}")
                        st.write(r"式中：$m$为污染物泄漏质量，g/d；$b$为含水层厚度，m；$n$为有效孔隙度；$u$为地下水实际流速，m/d；$D_L$为纵向弥散系数，m^2/d；$D_T$为横向弥散系数，m^2/d；$x$为地下水流向距离，m；$y$为垂直于地下水流向方向的距离；$t_0$为泄漏时间，d；$t$为预测时间，d。")

                    # Hidden/Default params
                    C0 = m_val
                    Q = 1.0
                    M = 0.0
                    lambda_coef = 0.0
                    width, length = 0.0, 0.0
                else:
                    # Row 1: Source Term
                    c1, c2, c3 = st.columns(3)
                    
                    if "Point Continuous" in sub_model:
                        st.write("选择泄漏量输入类型")
                        input_type = st.radio(
                            "选择泄漏量输入类型", 
                            ["泄漏质量", "泄漏量和浓度"], 
                            horizontal=True,
                            label_visibility="collapsed",
                            key="2d_input_type"
                        )
                        
                        if input_type == "泄漏质量":
                            with c1: 
                                m_val = st.number_input("污染物泄漏质量m (g/d)", value=100.0, key="2d_m_val")
                                C0 = m_val
                                Q = 1.0
                            M = 0.0
                        else:
                            with c1: Q = st.number_input("废水泄漏量Q (m³/d)", value=10.0, key="2d_Q_pc")
                            with c2: C0 = st.number_input("污染物浓度C0 (g/m³)", value=10.0, key="2d_C0_pc")
                            st.write(f"m = Q × C0 = {Q * C0:.2f} g/d")
                            M = 0.0
                        
                        width, length = 0.0, 0.0
                        duration = 0.0

                        st.markdown("### 二维点源持续泄漏模型")
                        with st.expander("模型说明：点源持续注入", expanded=True):
                            st.write("采用Hantush近似解：")
                            st.latex(r"C(x,y,t) = \frac{m}{4\pi n M \sqrt{D_L D_T}} \exp\left(\frac{xu}{2D_L}\right) \left[ 2K_0(\beta) - W\left(\frac{u^2 t}{4D_L}, \beta\right) \right]")
                            st.latex(r"\beta = \sqrt{\frac{u^2 x^2}{4 D_L^2} + \frac{u^2 y^2}{4 D_L D_T}}")
                            st.write(r"式中：$m$ 为污染物泄漏质量(或源强 $C_0 Q$)，$M$ 为含水层厚度，$K_0$ 为第二类修正贝塞尔函数，$W$ 为井函数。")
                
                    elif "Point Instantaneous" in sub_model:
                        with c1: M = st.number_input("污染物泄漏质量m (g)", value=100.0, key="2d_M_g")
                        C0, Q = 0.0, 0.0
                        width, length = 0.0, 0.0
                        duration = 0.0
                        
                        st.markdown("### 二维点源瞬时泄漏模型")
                        with st.expander("模型说明：点源瞬时注入", expanded=True):
                            st.latex(r"C(x,y,t) = \frac{m/M}{4\pi n t \sqrt{D_L D_T}} \exp\left[ -\lambda t - \frac{(x-ut)^2}{4D_L t} - \frac{y^2}{4D_T t} \right]")
                            st.write(r"式中：$m$为污染物泄漏质量，$M$为含水层厚度，$n$为有效孔隙度，$u$为地下水实际流速，$D_L$为纵向弥散系数，$D_T$为横向弥散系数，$x$为地下水流向距离，$y$为垂直于地下水流向方向的距离，$t$为预测时间，$\lambda$为反应系数。")
                            st.write(r"当不考虑化学反应，即$\lambda=0$时，模型为HJ610推荐的模型：")
                            st.latex(r"C(x,y,t) = \frac{m/M}{4\pi n t \sqrt{D_L D_T}} \exp\left[ - \frac{(x-ut)^2}{4D_L t} - \frac{y^2}{4D_T t} \right]")

                    elif "Area Instantaneous" in sub_model:
                        with c1: M = st.number_input("污染物泄漏质量m (g)", value=100.0, key="2d_M_area_inst")
                        C0, Q = 0.0, 0.0
                        duration = 0.0
                        
                        st.markdown("---")
                        st.write("面源尺寸设置:")
                        ac1, ac2 = st.columns(2)
                        with ac1: width = st.number_input("污染源宽度 (m)", value=20.0, key="2d_width_ai")
                        with ac2: length = st.number_input("污染源长度 (m)", value=30.0, key="2d_length_ai")

                        st.markdown("### 二维面源瞬时泄漏模型")
                        with st.expander("模型说明：面源瞬时注入", expanded=True):
                            st.latex(r"C(x,y,t) = \frac{m}{4nMLb} \left[ \text{erf}\left(\frac{x-ut-L}{2\sqrt{D_L t}}\right) - \text{erf}\left(\frac{x-ut}{2\sqrt{D_L t}}\right) \right] \left[ \text{erf}\left(\frac{y-b/2}{2\sqrt{D_T t}}\right) - \text{erf}\left(\frac{y+b/2}{2\sqrt{D_T t}}\right) \right]")
                            st.write(r"式中：$m$为污染物泄漏质量，g；$L$为污染源长度，m；$b$为污染源宽度，m；$M$为含水层厚度，m；$n$为有效孔隙度；$u$为地下水实际流速，m/d；$D_L$为纵向弥散系数，m^2/d；$D_T$为横向弥散系数，m^2/d；$x$为地下水流向距离，m；$y$为垂直于地下水流向方向的距离；$t$为预测时间，d。")

                    elif "Area Continuous" in sub_model:
                        with c1: C0 = st.number_input("源浓度 C0 (mg/L)", value=100.0, key="2d_C0_area_cont")
                        with c2: Q = st.number_input("渗漏率 Q (m³/d)", value=1.0, key="2d_Q_area_cont")
                        st.write(f"m = Q × C0 = {Q * C0:.2f} g/d")
                        M = 0.0
                        duration = 0.0
                        
                        st.markdown("---")
                        st.write("面源尺寸设置:")
                        ac1, ac2 = st.columns(2)
                        with ac1: width = st.number_input("污染源宽度 (m)", value=20.0, key="2d_width_ac")
                        with ac2: length = st.number_input("污染源长度 (m)", value=30.0, key="2d_length_ac")

                        st.markdown("### 二维面源持续泄漏模型")
                        with st.expander("模型说明：面源持续注入", expanded=True):
                            st.latex(r"C(x,y,t) = \frac{m}{4nMLb} \int_0^t \left[ \text{erf}\left(\frac{x-u\tau-L}{2\sqrt{D_L \tau}}\right) - \text{erf}\left(\frac{x-u\tau}{2\sqrt{D_L \tau}}\right) \right] \left[ \text{erf}\left(\frac{y-b/2}{2\sqrt{D_T \tau}}\right) - \text{erf}\left(\frac{y+b/2}{2\sqrt{D_T \tau}}\right) \right] d\tau")
                            st.write(r"式中：$m$为污染物泄漏质量，g/d；$L$为污染源长度，m；$b$为污染源宽度，m；$M$为含水层厚度，m；$n$为有效孔隙度；$u$为地下水实际流速，m/d；$D_L$为纵向弥散系数，m^2/d；$D_T$为横向弥散系数，m^2/d；$x$为地下水流向距离，m；$y$为垂直于地下水流向方向的距离；$t$为预测时间，d。")
                    
                    else:
                        C0, Q, M = 0.0, 0.0, 0.0
                        width, length = 0.0, 0.0
                        duration = 0.0
    
                    st.markdown("---")
                    # Row 2: Aquifer
                    c1, c2, c3 = st.columns(3)
                    with c1: ne = st.number_input("含水层有效孔隙度n", value=0.3, key="2d_ne")
                    with c2: H = st.number_input("含水层厚度M (m)", value=10.0, key="2d_H")
                    with c3: lambda_coef = st.number_input("反应系数λ (1/d)", value=0.0, key="2d_lambda")
                    
                    # Row 3: Transport
                    c1, c2, c3 = st.columns(3)
                    with c1: u = st.number_input("地下水实际流速u (m/d)", value=0.01, format="%.4f", key="2d_u")
                    with c2: DL = st.number_input("纵向弥散系数DL (m²/d)", value=0.1, key="2d_DL")
                    with c3: DT = st.number_input("横向弥散系数DT (m²/d)", value=0.01, key="2d_DT")
                    
                    # Row 4: Standards
                    c1, c2 = st.columns(2)
                    with c1: limit_val = st.number_input("评价标准 (mg/L)", value=0.5, key="2d_limit")
                    with c2: detection_limit = st.number_input("检出限 (mg/L)", value=0.05, key="2d_det_limit")
    
            # Unified Scheme Selection
            with st.expander("预测方案设置", expanded=True):
                t_str = st.text_input("输入预测时间t (天) [逗号分隔]", value="100, 200, 300, 1000, 3650, 5000", key="2d_t_str")
                
                use_flow = st.checkbox("考虑地下水流向 (可选)", value=True, key="2d_use_flow")
                if use_flow:
                    st.caption("考虑地下水流向后，x将代表东西方向，y代表南北方向")
                    c1, c2, c3 = st.columns(3)
                    with c1: angle = st.number_input("地下水流向 (°)", value=0.0, key="2d_angle")
                    with c2: x_s = st.number_input("泄漏点x坐标 (m) (面源为中心点)", value=15.0, key="2d_xs")
                    with c3: y_s = st.number_input("泄漏点y坐标 (m) (面源为中心点)", value=0.0, key="2d_ys")
                else:
                    angle = 0.0
                    x_s = 0.0
                    y_s = 0.0
    
                st.write("选择预测方案:")
                scheme = st.radio("方案选择", [
                    "方案一：网格点预测，计算超标面积、影响面积，绘制污染晕图",
                    "方案二：厂界浓度预测",
                    "方案三：计算指定位置（如敏感点）处浓度随时间的变化趋势",
                    "方案四：计算地下水流向上浓度、浓度沿程分布、超标距离和影响距离等"
                ], index=0, label_visibility="collapsed")
                
                # Conditional Scheme Inputs
                if "方案三" in scheme:
                    st.write("计算指定坐标处浓度变化，输入预测点编号及坐标:")
                    default_points = "1#,60,15\n2#,50,20\n3#,55,26\nA,30,30\nB,70,20\nC,75,22"
                    points_str = st.text_area("预测点 (编号,x,y 一行一个)", value=default_points, height=150, key="points_str")
                    
                    try:
                        pts_lines = points_str.strip().split('\n')
                        p_ids = []
                        p_x = []
                        p_y = []
                        for line in pts_lines:
                            parts = line.split(',')
                            if len(parts) == 3:
                                p_ids.append(parts[0].strip())
                                p_x.append(float(parts[1].strip()))
                                p_y.append(float(parts[2].strip()))
                        
                        if p_ids:
                            fig_loc_3 = go.Figure()
                            
                            # Draw Source
                            if "Area" in sub_model:
                                theta_rad = np.radians(angle)
                                dx_l = length / 2
                                dy_w = width / 2
                                corners_local = [(dx_l, dy_w), (-dx_l, dy_w), (-dx_l, -dy_w), (dx_l, -dy_w), (dx_l, dy_w)]
                                corners_x = []
                                corners_y = []
                                for cx, cy in corners_local:
                                    rx = cx * np.cos(theta_rad) - cy * np.sin(theta_rad)
                                    ry = cx * np.sin(theta_rad) + cy * np.cos(theta_rad)
                                    corners_x.append(x_s + rx)
                                    corners_y.append(y_s + ry)
                                fig_loc_3.add_trace(go.Scatter(x=corners_x, y=corners_y, mode='lines', fill='toself', name='面源范围', line=dict(color='red'), fillcolor='rgba(255,0,0,0.2)'))
                                fig_loc_3.add_trace(go.Scatter(x=[x_s], y=[y_s], mode='markers', name='面源中心', marker=dict(color='red', size=8)))
                            else:
                                fig_loc_3.add_trace(go.Scatter(x=[x_s], y=[y_s], mode='markers', name='泄漏点', marker=dict(color='red', size=10)))
    
                            fig_loc_3.add_trace(go.Scatter(x=p_x, y=p_y, mode='markers', name='指定点', text=p_ids, marker=dict(color='green', size=10)))
                            fig_loc_3.update_layout(title="位置关系图 (根据上面的参数自动生成)", xaxis_title="X", yaxis_title="Y", showlegend=True, width=500, height=400)
                            st.plotly_chart(fig_loc_3)
                            params["obs_points"] = list(zip(p_ids, p_x, p_y))
                            
                    except Exception as e:
                        st.error(f"格式错误: {e}")
                
                elif "方案二" in scheme:
                    st.write("计算厂界浓度分布，输入厂界拐点坐标:")
                    default_boundary = "0,-50\n150,-50\n150,20\n100,20\n100,60\n0,60\n0,-50"
                    boundary_coords_str = st.text_area("厂界坐标 (x,y 一行一个)", value=default_boundary, height=150, key="boundary_str")
                    
                    try:
                        b_lines = boundary_coords_str.strip().split('\n')
                        b_x = []
                        b_y = []
                        for line in b_lines:
                            parts = line.split(',')
                            if len(parts) == 2:
                                b_x.append(float(parts[0].strip()))
                                b_y.append(float(parts[1].strip()))
                        
                        if b_x:
                            fig_loc = go.Figure()
                            fig_loc.add_trace(go.Scatter(x=b_x, y=b_y, mode='lines+markers', name='厂界', line=dict(color='skyblue', width=3)))
                            
                            # Draw Source
                            if "Area" in sub_model:
                                theta_rad = np.radians(angle)
                                dx_l = length / 2
                                dy_w = width / 2
                                corners_local = [(dx_l, dy_w), (-dx_l, dy_w), (-dx_l, -dy_w), (dx_l, -dy_w), (dx_l, dy_w)]
                                corners_x = []
                                corners_y = []
                                for cx, cy in corners_local:
                                    rx = cx * np.cos(theta_rad) - cy * np.sin(theta_rad)
                                    ry = cx * np.sin(theta_rad) + cy * np.cos(theta_rad)
                                    corners_x.append(x_s + rx)
                                    corners_y.append(y_s + ry)
                                fig_loc.add_trace(go.Scatter(x=corners_x, y=corners_y, mode='lines', fill='toself', name='面源范围', line=dict(color='red'), fillcolor='rgba(255,0,0,0.2)'))
                                fig_loc.add_trace(go.Scatter(x=[x_s], y=[y_s], mode='markers', name='面源中心', marker=dict(color='red', size=8)))
                            else:
                                fig_loc.add_trace(go.Scatter(x=[x_s], y=[y_s], mode='markers', name='泄漏点', marker=dict(color='red', size=10)))
    
                            fig_loc.update_layout(title="位置关系图 (根据上面的参数自动生成)", xaxis_title="X", yaxis_title="Y", showlegend=True, width=500, height=400)
                            st.plotly_chart(fig_loc)
                            params["boundary_x"] = b_x
                            params["boundary_y"] = b_y
                    except Exception as e:
                        st.error(f"坐标格式错误: {e}")
    
                elif "方案四" in scheme:
                    c1, c2, c3 = st.columns(3)
                    with c1: dist_downstream = st.number_input("泄漏点下游方向范围 (m)", value=200.0, key="s4_down")
                    with c2: dist_upstream = st.number_input("泄漏点上游方向范围 (m)", value=-20.0, key="s4_up")
                    with c3: dist_step = st.number_input("间距 (m)", value=1.0, key="s4_step")
                    params["s4_range"] = (dist_upstream, dist_downstream, dist_step)
                
                elif "方案一" in scheme:
                    st.markdown("为保证计算精确，确保预测范围的设置要大于超标范围和影响范围。")
                    c1, c2, c3 = st.columns(3)
                    with c1: x_max = st.number_input("x方向最大值Xmax (m)", value=180.0, key="x_max")
                    with c2: x_min = st.number_input("x方向最小值Xmin (m)", value=-20.0, key="x_min")
                    with c3: nx = st.number_input("x剖分数量", value=101, key="nx")
                    
                    c1, c2, c3 = st.columns(3)
                    with c1: y_max = st.number_input("y方向最大值Ymax (m)", value=100.0, key="y_max")
                    with c2: y_min = st.number_input("y方向最小值Ymin (m)", value=-100.0, key="y_min")
                    with c3: ny = st.number_input("y剖分数量 (与x划分数量相等)", value=101, key="ny")
                    
                    params["x_max"] = x_max
                    params["x_min"] = x_min
                    params["nx"] = int(nx)
                    params["y_max"] = y_max
                    params["y_min"] = y_min
                    params["ny"] = int(ny)
    
                    try:
                        fig_loc_1 = go.Figure()
                        fig_loc_1.add_shape(
                            type="rect",
                            x0=x_min, y0=y_min, x1=x_max, y1=y_max,
                            line=dict(color="blue", width=2),
                            fillcolor="rgba(0,0,255,0.1)",
                        )
                        fig_loc_1.add_trace(go.Scatter(x=[x_min, x_max, x_max, x_min, x_min], y=[y_min, y_min, y_max, y_max, y_min], mode='lines', name='预测范围', line=dict(color='blue')))
                        
                        # Draw Source
                        if "Area" in sub_model:
                            theta_rad = np.radians(angle)
                            dx_l = length / 2
                            dy_w = width / 2
                            corners_local = [(dx_l, dy_w), (-dx_l, dy_w), (-dx_l, -dy_w), (dx_l, -dy_w), (dx_l, dy_w)]
                            corners_x = []
                            corners_y = []
                            for cx, cy in corners_local:
                                rx = cx * np.cos(theta_rad) - cy * np.sin(theta_rad)
                                ry = cx * np.sin(theta_rad) + cy * np.cos(theta_rad)
                                corners_x.append(x_s + rx)
                                corners_y.append(y_s + ry)
                            fig_loc_1.add_trace(go.Scatter(x=corners_x, y=corners_y, mode='lines', fill='toself', name='面源范围', line=dict(color='red'), fillcolor='rgba(255,0,0,0.2)'))
                            fig_loc_1.add_trace(go.Scatter(x=[x_s], y=[y_s], mode='markers', name='面源中心', marker=dict(color='red', size=8)))
                        else:
                            fig_loc_1.add_trace(go.Scatter(x=[x_s], y=[y_s], mode='markers', name='泄漏点', marker=dict(color='red', size=10)))
                        
                        fig_loc_1.update_layout(
                            title="位置关系图 (根据上面的参数自动生成)", 
                            xaxis_title="X", 
                            yaxis_title="Y", 
                            showlegend=True, 
                            width=500, 
                            height=400,
                            xaxis=dict(range=[min(x_min, x_s) - 10, max(x_max, x_s) + 10]),
                            yaxis=dict(range=[min(y_min, y_s) - 10, max(y_max, y_s) + 10])
                        )
                        st.plotly_chart(fig_loc_1)
                    except Exception as e:
                        st.error(f"绘图错误: {e}")
    
            # Pack Params
            params.update({
                "M": M, "C0": C0, "Q": Q, "duration": duration, "width": width, "length": length,
                "ne": ne, "H": H, "DL": DL, "DT": DT, "u": u, "lambda_coef": lambda_coef,
                "t_str": t_str, "angle": angle, "x_s": x_s, "y_s": y_s, 
                "limit_val": limit_val, "detection_limit": detection_limit,
                "scheme": scheme,
                "sub_model": sub_model
            })

        if st.button("计算二维模型"):
            # Prepare for consumption check
            try:
                times_to_check = []
                if "t_str" in params:
                     times_to_check = [float(x.strip()) for x in params["t_str"].split(',') if x.strip()]
                
                # Scheme 2/3/4 usually rely on t_str or t_max
                # Check specific scheme params if t_str is not the only driver
                if "t_max" in params:
                    times_to_check.append(params["t_max"])
                
                max_time_req = max(times_to_check) if times_to_check else 0
            except:
                max_time_req = 99999

            if st.session_state.user_id:
                if max_time_req <= 300:
                    st.success("预测时间 ≤ 300天，本次免费！")
                else:
                    if not db_manager.consume_usage(st.session_state.user_id):
                        st.error("剩余使用次数不足，请充值！(超过300天的预测需要消耗次数)")
                        st.stop()
                    else:
                        st.info("已消耗 1 次预测次数")
            else:
                 if max_time_req > 365:
                      st.error("未登录用户最大预测时间不能超过365天")
                      st.stop()
            
            with st.spinner("正在计算..."):
                try:
                    times = [float(x.strip()) for x in params["t_str"].split(',') if x.strip()]
                except:
                    st.error("时间格式错误")
                    st.stop()
                
                with col2:
                    st.markdown("### 计算结果")
    
                    # Helper function for dispatch
                    def calculate_2d_dispatch(t_val, X_in, Y_in):
                        # X_in, Y_in can be meshgrid or 1D arrays or scalars
                        if "Instantaneous" in sub_model:
                            if "Area" in sub_model:
                                return groundwater_models.calculate_2d_area_instantaneous_rotated(
                                    params["M"], params["ne"], params["H"], params["DL"], params["DT"], 
                                    params["u"], t_val, X_in, Y_in, params["width"], params["length"], 
                                    params["angle"], params["x_s"], params["y_s"], params["lambda_coef"]
                                )
                            else: # Point Instantaneous
                                return groundwater_models.calculate_2d_instantaneous_rotated(
                                    params["M"], params["ne"], params["H"], params["DL"], params["DT"], 
                                    params["u"], t_val, X_in, Y_in, params["angle"], params["x_s"], params["y_s"],
                                    params["lambda_coef"]
                                )
                        elif "Short-term" in sub_model:
                             return groundwater_models.calculate_2d_short_release_rotated(
                                params["C0"], params["Q"], params["ne"], params["H"], params["DL"], params["DT"], 
                                params["u"], t_val, params["duration"], X_in, Y_in, params["angle"], params["x_s"], params["y_s"],
                                params["lambda_coef"]
                            )
                        else: # Continuous (Point or Area)
                            if "Area" in sub_model:
                                return groundwater_models.calculate_2d_area_continuous_rotated(
                                    params["C0"], params["Q"], params["ne"], params["H"], params["DL"], params["DT"], 
                                    params["u"], t_val, X_in, Y_in, params["width"], params["length"], 
                                    params["angle"], params["x_s"], params["y_s"], params["lambda_coef"]
                                )
                            else: # Point Continuous
                                return groundwater_models.calculate_2d_continuous_rotated(
                                    params["C0"], params["Q"], params["ne"], params["H"], params["DL"], params["DT"], 
                                    params["u"], t_val, X_in, Y_in, params["angle"], params["x_s"], params["y_s"],
                                    params["lambda_coef"]
                                )
    
                    if "方案一" in params["scheme"]:
                        x_range = np.linspace(params["x_min"], params["x_max"], params["nx"])
                        y_range = np.linspace(params["y_min"], params["y_max"], params["ny"])
                        X, Y = np.meshgrid(x_range, y_range)
                        
                        results_dict = {}
                        summary_data = []
                        flat_x = X.flatten()
                        flat_y = Y.flatten()
                        grid_df = pd.DataFrame({"x": flat_x, "y": flat_y})
                        
                        dx = x_range[1] - x_range[0]
                        dy = y_range[1] - y_range[0]
                        cell_area = dx * dy
                        
                        for t_val in times:
                            res_t_mg = calculate_2d_dispatch(t_val, X, Y)
                            
                            max_c = np.max(res_t_mg)
                            area_exceeded = np.sum(res_t_mg > params["limit_val"]) * cell_area
                            area_affected = np.sum(res_t_mg > params["detection_limit"]) * cell_area
                            
                            summary_data.append({
                                "时间 (d)": t_val,
                                "最大浓度 (mg/L)": float(f"{max_c:.4f}"),
                                "超标面积 (m²)": float(f"{area_exceeded:.2f}"),
                                "影响面积 (m²)": float(f"{area_affected:.2f}")
                            })
                            results_dict[t_val] = res_t_mg
                            grid_df[f"t={t_val}天"] = res_t_mg.flatten()
                        
                        st.write("#### 统计结果")
                        st.warning("注：超标面积和影响面积是根据预测范围内的网格进行统计，若最大范围处仍然超标或超过检出限，则需扩大预测范围以获得更准确的超标面积和影响面积。")
                        st.dataframe(pd.DataFrame(summary_data), hide_index=True)
                        st.write("#### 网格点计算数据")
                        st.dataframe(grid_df, height=300)
                        st.write("#### 浓度分布图")
                        
                        for selected_t in times:
                            st.markdown(f"##### T = {selected_t} d")
                            res_plot = results_dict[selected_t]
                            plot_tabs = st.tabs([f"等值线图 (T={selected_t}d)", f"等值线图 (交互式, T={selected_t}d)"])
                            
                            with plot_tabs[0]:
                                fig_static, ax = plt.subplots(figsize=(5, 4)) # Reduced size from (10, 8) to (5, 4)
                                cf = ax.contourf(X, Y, res_plot, cmap='YlGnBu', levels=20)
                                cbar = fig_static.colorbar(cf, ax=ax)
                                cbar.set_label('浓度 (mg/L)')
                                levels_lines = []
                                line_colors = []
                                line_labels = []
                                if params["detection_limit"] < np.max(res_plot):
                                    levels_lines.append(params["detection_limit"])
                                    line_colors.append('blue')
                                    line_labels.append('检出限')
                                if params["limit_val"] < np.max(res_plot):
                                    levels_lines.append(params["limit_val"])
                                    line_colors.append('red')
                                    line_labels.append('标准值')
                                if levels_lines:
                                    # Increase number of contour levels for smoother lines, or just draw specific levels
                                    cs = ax.contour(X, Y, res_plot, levels=levels_lines, colors=line_colors, linestyles='dashed', linewidths=0.8)
                                    # Adjust inline_spacing to reduce gap in the line for labels
                                    ax.clabel(cs, inline=True, fontsize=6, fmt='%.3f', inline_spacing=2) 
                                
                                # Draw Source on Matplotlib
                                if "Area" in sub_model:
                                    # For matplotlib, we can compute the corners too
                                    theta_rad = np.radians(angle)
                                    dx_l = length / 2
                                    dy_w = width / 2
                                    corners_local = [(dx_l, dy_w), (-dx_l, dy_w), (-dx_l, -dy_w), (dx_l, -dy_w), (dx_l, dy_w)]
                                    corners_x = []
                                    corners_y = []
                                    for cx, cy in corners_local:
                                        rx = cx * np.cos(theta_rad) - cy * np.sin(theta_rad)
                                        ry = cx * np.sin(theta_rad) + cy * np.cos(theta_rad)
                                        corners_x.append(x_s + rx)
                                        corners_y.append(y_s + ry)
                                    ax.plot(corners_x, corners_y, 'r-', linewidth=1, label='面源范围') # Thinner line
                                    ax.plot(params["x_s"], params["y_s"], 'ro', markersize=2) # Even smaller marker (was 3)
                                else:
                                    ax.plot(params["x_s"], params["y_s"], 'ro', markersize=2, label='泄漏点') # Even smaller marker (was 3)
                                
                                ax.set_xlabel('X (m)')
                                ax.set_ylabel('Y (m)')
                                ax.set_title(f'T={selected_t}d 浓度分布')
                                
                                # Set fixed size for Matplotlib figure when displaying
                                st.pyplot(fig_static, use_container_width=False)
    
                            with plot_tabs[1]:
                                fig = go.Figure()
                                fig.add_trace(go.Contour(
                                    z=res_plot, x=x_range, y=y_range,
                                    colorscale='Viridis',
                                    contours=dict(start=0, end=np.max(res_plot), size=np.max(res_plot)/20 if np.max(res_plot) > 0 else 0.1, coloring='heatmap', showlabels=True),
                                    colorbar=dict(title='浓度 (mg/L)')
                                ))
                                
                                # Draw Source on Plotly
                                if "Area" in sub_model:
                                    theta_rad = np.radians(angle)
                                    dx_l = length / 2
                                    dy_w = width / 2
                                    corners_local = [(dx_l, dy_w), (-dx_l, dy_w), (-dx_l, -dy_w), (dx_l, -dy_w), (dx_l, dy_w)]
                                    corners_x = []
                                    corners_y = []
                                    for cx, cy in corners_local:
                                        rx = cx * np.cos(theta_rad) - cy * np.sin(theta_rad)
                                        ry = cx * np.sin(theta_rad) + cy * np.cos(theta_rad)
                                        corners_x.append(x_s + rx)
                                        corners_y.append(y_s + ry)
                                    fig.add_trace(go.Scatter(x=corners_x, y=corners_y, mode='lines', fill='toself', name='面源范围', line=dict(color='red', width=1), fillcolor='rgba(255,0,0,0.1)')) # Thinner line
                                else:
                                    fig.add_trace(go.Scatter(x=[params["x_s"]], y=[params["y_s"]], mode='markers', marker=dict(color='red', size=2, symbol='x'), name='泄漏点')) # Even smaller marker (was 4)
                                
                                fig.update_layout(
                                    autosize=False,
                                    width=None,  # Use container width with fixed aspect ratio via scaleanchor if possible, or just fixed size
                                    height=None, 
                                    margin=dict(l=30, r=30, b=30, t=30),
                                    font=dict(size=10),
                                    xaxis=dict(scaleanchor="y", scaleratio=1, constrain="domain"), # Fix aspect ratio
                                    yaxis=dict(constrain="domain"),
                                    plot_bgcolor='rgba(0,0,0,0)' # Transparent background to let contour fill show, or set to a specific color
                                )
                                
                                fig.update_xaxes(range=[params["x_min"], params["x_max"]])
                                fig.update_yaxes(range=[params["y_min"], params["y_max"]])
                                
                                # Use container width but aspect ratio is fixed by plotly layout
                                st.plotly_chart(fig, key=f"plotly_chart_{selected_t}", use_container_width=True)
    
                    elif "方案二" in params["scheme"]:
                        if not st.session_state.user_id and max(times) > 365:
                             st.error("预测时间超过限制，请登录后重试")
                        
                        st.subheader("方案二：厂界浓度计算结果如下")
                        tabs_s2 = st.tabs(["曲线图", "数据表格", "结论汇总"])
                        
                        b_x = params.get("boundary_x", [])
                        b_y = params.get("boundary_y", [])
                        
                        if not b_x:
                            st.error("未设置厂界坐标")
                        else:
                            points_x = []
                            points_y = []
                            for i in range(len(b_x)-1):
                                x1, y1 = b_x[i], b_y[i]
                                x2, y2 = b_x[i+1], b_y[i+1]
                                dist = np.sqrt((x2-x1)**2 + (y2-y1)**2)
                                if dist == 0: continue
                                num_steps = int(np.ceil(dist))
                                seg_x = np.linspace(x1, x2, num_steps)
                                seg_y = np.linspace(y1, y2, num_steps)
                                if i < len(b_x) - 2:
                                    points_x.extend(seg_x[:-1])
                                    points_y.extend(seg_y[:-1])
                                else:
                                    points_x.extend(seg_x)
                                    points_y.extend(seg_y)
                                    
                            pts_x = np.array(points_x)
                            pts_y = np.array(points_y)
                            
                            df_boundary = pd.DataFrame({"坐标 (x, y)": [f"{x:.1f}, {y:.1f}" for x, y in zip(pts_x, pts_y)]})
                            fig_s2 = go.Figure()
                            fig_s2.add_trace(go.Scatter3d(x=pts_x, y=pts_y, z=np.zeros_like(pts_x), mode='lines', name='厂界', line=dict(color='black', width=4)))
                            summary_s2 = []
    
                            for t_val in times:
                                c_boundary_mg = calculate_2d_dispatch(t_val, pts_x, pts_y)
                                df_boundary[f"t={t_val}天"] = c_boundary_mg
                                max_c_boundary = np.max(c_boundary_mg)
                                summary_s2.append({"时间 (d)": t_val, "厂界最大浓度 (mg/L)": max_c_boundary})
                                fig_s2.add_trace(go.Scatter3d(x=pts_x, y=pts_y, z=c_boundary_mg, mode='lines', name=f't={t_val}天'))
    
                            with tabs_s2[0]:
                                st.write("厂界浓度分布图")
                                fig_s2.update_layout(scene=dict(xaxis_title='X (m)', yaxis_title='Y (m)', zaxis_title='浓度 (mg/L)'), height=600)
                                st.plotly_chart(fig_s2)
                            with tabs_s2[1]:
                                st.dataframe(df_boundary, use_container_width=True)
                            with tabs_s2[2]:
                                for item in summary_s2:
                                    st.write(f"**t = {item['时间 (d)']}天**")
                                    st.write(f"厂界最大浓度为： `{item['厂界最大浓度 (mg/L)']}` mg/L")
    
                    elif "方案三" in params["scheme"]:
                        if not st.session_state.user_id and max(times) > 365:
                            st.error("预测时间超过限制")
                        
                        st.subheader("方案三：指定点计算结果如下")
                        tabs_s3 = st.tabs(["曲线图", "数据表格", "结论汇总"])
                        obs_points = params.get("obs_points", [])
                        
                        if obs_points:
                            max_t = max(times)
                            t_daily = np.arange(1, int(max_t) + 1, 1)
                            df_s3 = pd.DataFrame({"时间(天)": t_daily})
                            summary_s3 = []
                            fig_s3 = go.Figure()
                            
                            for pid, px, py in obs_points:
                                # Calculate Series loop
                                c_series_list = []
                                # For instantaneous we can use vectorization if available, but for generic dispatch we loop
                                # Actually calculate_2d_dispatch works for scalar t.
                                # For performance, if model is Instantaneous, we could use the specialized series function.
                                # But to keep it unified and support all models, we loop or use vectorized time if model supports it.
                                # Our dispatch takes scalar t. So we loop.
                                
                                # Optimization: if Point Instantaneous, use specialized function
                                if "Point Instantaneous" in sub_model:
                                    _, c_series_mg = groundwater_models.calculate_2d_instantaneous_point_series(
                                        params["M"], params["ne"], params["H"], params["DL"], params["DT"],
                                        params["u"], t_daily, px, py, 
                                        params["angle"], params["x_s"], params["y_s"], params["lambda_coef"]
                                    )
                                else:
                                    # For other models, loop (might be slow for large t_daily)
                                    # If t_daily is huge (e.g. 5000 days), this is 5000 calls.
                                    # For Continuous, each call is 100 steps. 500,000 steps. Acceptable.
                                    c_temp = []
                                    for t_d in t_daily:
                                        # Passing scalar px, py
                                        val = calculate_2d_dispatch(t_d, np.array([px]), np.array([py]))
                                        c_temp.append(val[0])
                                    c_series_mg = np.array(c_temp)
    
                                df_s3[pid] = c_series_mg
                                fig_s3.add_trace(go.Scatter(x=t_daily, y=c_series_mg, mode='lines', name=pid))
                                
                                max_val = np.max(c_series_mg)
                                exceed_mask = c_series_mg > params["limit_val"]
                                exceed_str = f"第{t_daily[exceed_mask][0]}天到第{t_daily[exceed_mask][-1]}天" if np.any(exceed_mask) else "未超标"
                                affect_mask = c_series_mg > params["detection_limit"]
                                affect_str = f"第{t_daily[affect_mask][0]}天到第{t_daily[affect_mask][-1]}天" if np.any(affect_mask) else "无影响"
                                
                                summary_s3.append({"id": pid, "max": max_val, "exceed": exceed_str, "affect": affect_str})
                                
                            fig_s3.add_hline(y=params["limit_val"], line_color="orange", annotation_text="标准值")
                            fig_s3.add_hline(y=params["detection_limit"], line_color="gold", annotation_text="检出限")
                            
                            with tabs_s3[0]:
                                st.plotly_chart(fig_s3)
                            with tabs_s3[1]:
                                def highlight_vals(val):
                                    if val > params["limit_val"]: return 'color: red'
                                    elif val > params["detection_limit"]: return 'color: blue'
                                    else: return 'color: green'
                                st.dataframe(df_s3.style.map(highlight_vals, subset=[pid for pid, _, _ in obs_points]), use_container_width=True)
                            with tabs_s3[2]:
                                for item in summary_s3:
                                    st.markdown(f"**{item['id']}** Max: `{item['max']:.6f}` mg/L. 超标: {item['exceed']}. 影响: {item['affect']}")
                                    st.markdown("---")
    
                    elif "方案四" in params["scheme"]:
                        st.subheader("方案四：地下水流向计算结果如下")
                        d_up, d_down, d_step = params.get("s4_range", (-20.0, 200.0, 1.0))
                        l_vals = np.arange(d_up, d_down + d_step, d_step)
                        
                        theta = np.radians(params["angle"])
                        dx_line = l_vals * np.cos(theta)
                        dy_line = l_vals * np.sin(theta)
                        X_line = params["x_s"] + dx_line
                        Y_line = params["y_s"] + dy_line
                        
                        res_dict_s4 = {}
                        summary_s4 = []
                        fig4 = go.Figure()
                        
                        for t_val in times:
                            c_line = calculate_2d_dispatch(t_val, X_line, Y_line)
                            res_dict_s4[t_val] = c_line
                            fig4.add_trace(go.Scatter(x=l_vals, y=c_line, mode='lines', name=f't={t_val}天', line=dict(dash='dash')))
                            
                            exceed_mask = c_line > params["limit_val"]
                            exceed_str = f"{l_vals[exceed_mask][0]:.2f}m - {l_vals[exceed_mask][-1]:.2f}m" if np.any(exceed_mask) else "未超标"
                            affect_mask = c_line > params["detection_limit"]
                            affect_str = f"{l_vals[affect_mask][0]:.2f}m - {l_vals[affect_mask][-1]:.2f}m" if np.any(affect_mask) else "无影响"
                            summary_s4.append({"time": t_val, "exceed": exceed_str, "affect": affect_str})
                            
                        fig4.add_hline(y=params["limit_val"], line_color="salmon", annotation_text="标准限值")
                        fig4.add_hline(y=params["detection_limit"], line_color="mediumseagreen", annotation_text="检出限")
                        
                        tabs_s4 = st.tabs(["曲线图", "数据表格"])
                        with tabs_s4[0]:
                            for item in summary_s4:
                                st.write(f"**t={item['time']}天**: 超标 {item['exceed']}, 影响 {item['affect']}")
                            st.plotly_chart(fig4)
                        with tabs_s4[1]:
                            df_s4 = pd.DataFrame({"距离(m)": l_vals})
                            for t_val in times: df_s4[f"t={t_val}天"] = res_dict_s4[t_val]
                            def highlight_vals_s4(val):
                                if isinstance(val, float):
                                    if val > params["limit_val"]: return 'color: red'
                                    elif val > params["detection_limit"]: return 'color: blue'
                                    else: return 'color: green'
                                return ''
                            st.dataframe(df_s4.style.map(highlight_vals_s4, subset=[f"t={t}天" for t in times]), use_container_width=True)
    
    with tab3:
        st.subheader("三维模型")
        sub_model = st.radio("选择情景", [
            "点源瞬时注入 (Instantaneous)", 
            "点源连续注入 (Continuous)", 
            "点源短时注入 (Short-term)"
        ], key="3d_sub")
        model_type = f"3D - {sub_model}"
        
        col1, col2 = st.columns(2)
        with col1:
            # Unified Parameters
            with st.expander("基本参数输入", expanded=True):
                c1, c2, c3 = st.columns(3)
                
                # Source Terms
                if "Instantaneous" in sub_model:
                    with c1: M = st.number_input("注入质量 M (kg)", value=100.0, key="3d_M")
                    C0, Q, duration = 0.0, 0.0, 0.0
                else:
                    with c1: C0 = st.number_input("源浓度 C0 (mg/L)", value=1000.0, key="3d_C0")
                    with c2: Q = st.number_input("渗漏率 Q (m³/d)", value=1.0, key="3d_Q")
                    M = 0.0
                    if "Short-term" in sub_model:
                        with c3: duration = st.number_input("泄漏持续时间 (d)", value=10.0, key="3d_dur")
                    else:
                        duration = 0.0
    
                st.markdown("---")
                # Aquifer & Transport
                c1, c2, c3 = st.columns(3)
                with c1: ne = st.number_input("有效孔隙度 ne", value=0.3, key="3d_ne")
                with c2: u = st.number_input("孔隙流速 u (m/d)", value=0.1, key="3d_u")
                with c3: lambda_coef = st.number_input("反应系数 λ (1/d)", value=0.0, key="3d_lambda")
                
                c1, c2, c3 = st.columns(3)
                with c1: DL = st.number_input("纵向弥散系数 DL (m²/d)", value=0.5, key="3d_DL")
                with c2: DT = st.number_input("横向弥散系数 DT (m²/d)", value=0.1, key="3d_DT")
                with c3: DV = st.number_input("垂向弥散系数 DV (m²/d)", value=0.01, key="3d_DV")
                
                # Standards
                c1, c2 = st.columns(2)
                with c1: limit_val = st.number_input("评价标准 (mg/L)", value=0.5, key="3d_limit")
                with c2: detection_limit = st.number_input("检出限 (mg/L)", value=0.05, key="3d_det_limit")
    
            # Scheme Selection
            with st.expander("预测方案设置", expanded=True):
                scheme_3d = st.radio("方案选择", [
                    "方案一：三维空间分布预测 (Isosurface/Slices)",
                    "方案二：指定位置浓度随时间变化",
                    "方案三：纵向 (轴线) 浓度分布预测"
                ], key="3d_scheme")
                
                if "方案一" in scheme_3d:
                    t_str = st.text_input("预测时间 t (d) [逗号分隔]", value="100, 200, 300, 1000, 3650, 5000", key="3d_t_str_s1")
                    c1, c2, c3 = st.columns(3)
                    with c1: x_max = st.number_input("最大纵向距离 X (m)", value=50.0, key="3d_x_max")
                    with c2: y_max = st.number_input("最大横向距离 Y (m)", value=20.0, key="3d_y_max")
                    with c3: z_max = st.number_input("最大垂向距离 Z (m)", value=10.0, key="3d_z_max")
                    params = {"t_str": t_str, "x_max": x_max, "y_max": y_max, "z_max": z_max}
                    
                elif "方案二" in scheme_3d:
                    t_max = st.number_input("最大预测时间 Tmax (d)", value=365.0, key="3d_t_max")
                    c1, c2, c3 = st.columns(3)
                    with c1: px = st.number_input("观测点 X (m)", value=10.0, key="3d_px")
                    with c2: py = st.number_input("观测点 Y (m)", value=0.0, key="3d_py")
                    with c3: pz = st.number_input("观测点 Z (m)", value=0.0, key="3d_pz")
                    params = {"t_max": t_max, "px": px, "py": py, "pz": pz}
                    
                elif "方案三" in scheme_3d:
                    t_str = st.text_input("预测时间 t (d) [逗号分隔]", value="100, 200, 300", key="3d_t_str")
                    c1, c2, c3 = st.columns(3)
                    with c1: x_range_max = st.number_input("最大纵向距离 X (m)", value=100.0, key="3d_x_range")
                    with c2: axis_y = st.number_input("轴线 Y 坐标 (m)", value=0.0, key="3d_ay")
                    with c3: axis_z = st.number_input("轴线 Z 坐标 (m)", value=0.0, key="3d_az")
                    params = {"t_str": t_str, "x_max": x_range_max, "ay": axis_y, "az": axis_z}

        # Calculation
        if st.button("计算三维模型"):
            # Prepare consumption check
            try:
                times_to_check = []
                if "t_str" in params:
                     times_to_check = [float(x.strip()) for x in params["t_str"].split(',') if x.strip()]
                if "t_max" in params:
                    times_to_check.append(params["t_max"])
                max_time_req = max(times_to_check) if times_to_check else 0
            except:
                max_time_req = 99999

            if st.session_state.user_id:
                if max_time_req <= 300:
                    st.success("预测时间 ≤ 300天，本次免费！")
                else:
                    if not db_manager.consume_usage(st.session_state.user_id):
                        st.error("剩余使用次数不足，请充值！(超过300天的预测需要消耗次数)")
                        st.stop()
                    else:
                        st.info("已消耗 1 次预测次数")
            else:
                 if max_time_req > 365:
                      st.error("未登录用户最大预测时间不能超过365天")
                      st.stop()

            # Dispatcher
            def calculate_3d_dispatch(t_in, X_in, Y_in, Z_in):
                if "Instantaneous" in sub_model:
                    return groundwater_models.calculate_3d_instantaneous(
                        M, ne, DL, DT, DV, u, t_in, X_in, Y_in, Z_in, lambda_coef
                    )
                elif "Short-term" in sub_model:
                    return groundwater_models.calculate_3d_short_release(
                        C0, Q, ne, DL, DT, DV, u, t_in, duration, X_in, Y_in, Z_in, lambda_coef
                    )
                else: # Continuous
                    return groundwater_models.calculate_3d_continuous(
                        C0, Q, ne, DL, DT, DV, u, t_in, X_in, Y_in, Z_in, lambda_coef
                    )

            with col2:
                if "方案一" in scheme_3d:
                    try:
                        times = [float(x.strip()) for x in params["t_str"].split(',') if x.strip()]
                    except:
                        st.error("时间格式错误")
                        st.stop()
    
                    with st.spinner("正在计算三维场..."):
                        x_range = np.linspace(0, params["x_max"], 40)
                        y_range = np.linspace(-params["y_max"], params["y_max"], 30)
                        z_range = np.linspace(-params["z_max"], params["z_max"], 20)
                        X, Y, Z = np.meshgrid(x_range, y_range, z_range, indexing='xy')
                        
                        st.subheader("三维分布结果")
                        
                        for t_val in times:
                            st.markdown(f"#### T={t_val}d")
                            res = calculate_3d_dispatch(t_val, X, Y, Z)
                            
                            tab_v1, tab_v2 = st.tabs([f"三维等值面 (T={t_val})", f"切片浓度图 (T={t_val})"])
                            
                            with tab_v1:
                                fig = plot_3d_isosurface(res, x_range, y_range, z_range, f"T={t_val}d 浓度场")
                                st.plotly_chart(fig, key=f"3d_iso_{t_val}")
                                
                            with tab_v2:
                                # Extract Z=0 slice (approximate)
                                z_idx = np.argmin(np.abs(z_range - 0))
                                res_slice = res[z_idx, :, :] # shape (ny, nx)
                                
                                fig_slice = go.Figure(data=go.Contour(
                                    z=res_slice, x=x_range, y=y_range,
                                    colorscale='Viridis',
                                    contours=dict(coloring='heatmap', showlabels=True)
                                ))
                                fig_slice.update_layout(title=f"Z={z_range[z_idx]:.1f}m 切片浓度分布", xaxis_title="X (m)", yaxis_title="Y (m)")
                                st.plotly_chart(fig_slice, key=f"3d_slice_{t_val}")
                                
                                max_c = np.max(res)
                                st.info(f"T={t_val}d 全场最大浓度: {max_c:.4f} mg/L")
                            
                            st.divider()
    
                elif "方案二" in scheme_3d:
                    t_vals = np.linspace(1, params["t_max"], 100)
                    
                    res_series = []
                    with st.spinner("计算时间序列..."):
                        for t_v in t_vals:
                            # Pass arrays of shape (1,) or scalars
                            val = calculate_3d_dispatch(t_v, np.array([params["px"]]), np.array([params["py"]]), np.array([params["pz"]]))
                            res_series.append(val[0])
                    
                    res_series = np.array(res_series)
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=t_vals, y=res_series, mode='lines', name='浓度变化'))
                    fig.add_hline(y=limit_val, line_color="red", annotation_text="标准值")
                    fig.update_layout(title=f"点 ({params['px']}, {params['py']}, {params['pz']}) 浓度随时间变化", xaxis_title="时间 (d)", yaxis_title="浓度 (mg/L)")
                    st.plotly_chart(fig)
                    
                elif "方案三" in scheme_3d:
                    try:
                        times = [float(x.strip()) for x in params["t_str"].split(',') if x.strip()]
                    except:
                        st.error("时间格式错误")
                        st.stop()
                        
                    x_vals = np.linspace(0, params["x_max"], 100)
                    # Y, Z are scalars
                    Y_in = np.full_like(x_vals, params["ay"])
                    Z_in = np.full_like(x_vals, params["az"])
                    
                    fig = go.Figure()
                    
                    with st.spinner("计算纵向分布..."):
                        for t_v in times:
                            # For Continuous, t_v is scalar, coords are arrays. This works fine with our model.
                            res_line = calculate_3d_dispatch(t_v, x_vals, Y_in, Z_in)
                            fig.add_trace(go.Scatter(x=x_vals, y=res_line, mode='lines', name=f't={t_v}d'))
                    
                    fig.add_hline(y=limit_val, line_color="red", annotation_text="标准值")
                    fig.update_layout(title=f"纵向浓度分布 (Y={params['ay']}, Z={params['az']})", xaxis_title="距离 X (m)", yaxis_title="浓度 (mg/L)")
                    st.plotly_chart(fig)
                    
                    # Table
                    st.write("数据预览")
                    df = pd.DataFrame({"距离(m)": x_vals})
                    for i, t_v in enumerate(times):
                         res_line = calculate_3d_dispatch(t_v, x_vals, Y_in, Z_in) # Recalculate or store? Recalculating is fast enough for line
                         df[f"t={t_v}d"] = res_line
                    st.dataframe(df)
    
    # Save Results
    if res is not None:
        st.divider()
        if st.session_state.user_id:
            if st.button("保存计算结果到数据库"):
                if isinstance(res, np.ndarray):
                    res_list = res.tolist()
                else:
                    res_list = res
                
                results_data = {"result": res_list}
                if x_range is not None: results_data["x"] = x_range.tolist()
                if y_range is not None: results_data["y"] = y_range.tolist()
                if z_range is not None: results_data["z"] = z_range.tolist()
                
                # Add UI State
                params["_ui_state"] = get_ui_state(["1d_", "2d_", "3d_"])
                
                db_manager.save_calculation(
                    st.session_state.user_id,
                    project_name,
                    f"Groundwater - {model_type}",
                    params,
                    results_data
                )
                st.success("结果已保存！")
        else:
            st.warning("登录后可保存结果")
            
        if x_range is not None and len(res.shape) == 1:
            df_res = pd.DataFrame({"Distance": x_range, "Concentration": res})
            st.download_button("下载结果 (CSV)", df_res.to_csv(index=False), "results.csv", "text/csv")


def surfacewater_page():
    st.header("地表水环境影响预测 (HJ2.3-2018 附录E)")
    
    model_type = st.selectbox("选择模型", ["一维稳态衰减 (1D Steady)", "二维岸边排放混合 (2D Mixing)"], key="sw_model_type")
    
    # Save Parameter Button
    col_proj, col_save = st.columns([5, 1], gap="small", vertical_alignment="bottom")
    with col_proj:
        project_name = st.text_input("项目名称", value="默认项目", key="project_name")
    with col_save:
        if st.button("保存参数", key="btn_save_sw", help="保存当前参数设置", use_container_width=True):
            if st.session_state.user_id:
                ui_params = {"_ui_state": get_ui_state(["sw_"])}
                db_manager.save_calculation(
                    st.session_state.user_id,
                    project_name,
                    "Surface Water - Parameters",
                    ui_params,
                    {}
                )
                st.toast("参数已保存到数据库！")
            else:
                st.toast("请先登录", icon="⚠️")
    
    load_history_sidebar("Surface Water")

    if "1D Steady" in model_type:
        with st.expander("基本参数输入", expanded=True):
            # Layout based on user screenshot: 2 columns
            # Left Column: Qp, Cp, Qh, Ch, Limit
            # Right Column: u, k, Ex, B, A
            
            c1, c2 = st.columns(2)
            with c1:
                Qp = st.number_input("污水排放量Qp (m^3/s)", value=1.0, key="sw_Qp")
                Cp = st.number_input("污染物排放浓度Cp (mg/l)", value=100.0, key="sw_Cp")
                Qh = st.number_input("河流流量Qh (m^3/s)", value=3.0, key="sw_Qh")
                Ch = st.number_input("河流上游污染物浓度Ch (mg/l)", value=15.0, key="sw_Ch")
                limit_val = st.number_input("评价标准 (mg/L)", value=20.0, key="sw_limit")
            
            with c2:
                u = st.number_input("河流断面流速u (m/s)", value=0.5, key="sw_u")
                K = st.number_input("污染物综合衰减系数k (1/s)", value=0.00005, format="%.6f", key="sw_K")
                Ex = st.number_input("污染物纵向扩散系数Ex (m^2/s)", value=0.5, key="sw_Ex")
                B = st.number_input("水面宽度B (m)", value=10.0, key="sw_B")
                A_area = st.number_input("断面面积 A(m^2)", value=20.0, key="sw_A")
                
            # Derived Params Calculation for Display
            # alpha = k*Ex / u^2
            # Pe = u*B / Ex
            
            u_safe = max(u, 1e-10)
            Ex_safe = max(Ex, 1e-10)
            
            alpha = (K * Ex_safe) / (u_safe**2)
            Pe = (u_safe * B) / Ex_safe
            
            st.markdown(f"`α = {alpha:.5f}` ; `Pe = {Pe:.1f}`")
            
            # Dynamic Model Description based on conditions
            if alpha <= 0.027 and Pe >= 1:
                st.markdown(r"当 $\alpha \le 0.027, Pe \ge 1$ 时，采用以下模型：")
                st.latex(r"C_0 = \frac{C_pQ_p + C_hQ_h}{Q_p + Q_h}")
                st.latex(r"C = C_0 \exp\left(-\frac{kx}{u}\right) \quad x \ge 0")
            elif alpha <= 0.027 and Pe < 1:
                st.markdown(r"当 $\alpha \le 0.027, Pe < 1$ 时，采用以下模型：")
                st.latex(r"C_0 = \frac{C_pQ_p + C_hQ_h}{Q_p + Q_h}")
                st.latex(r"C = C_0 \exp\left(\frac{ux}{E_x}\right) \quad x < 0")
                st.latex(r"C = C_0 \exp\left(-\frac{kx}{u}\right) \quad x \ge 0")
            elif 0.027 < alpha <= 380:
                st.markdown(r"当 $0.027 < \alpha \le 380$ 时，采用以下模型：")
                st.latex(r"C_0 = \frac{C_pQ_p + C_hQ_h}{(Q_p + Q_h)\sqrt{1 + 4\alpha}}")
                st.latex(r"C(x) = C_0 \exp\left[\frac{ux}{2E_x}(1 + \sqrt{1+4\alpha})\right] \quad x < 0")
                st.latex(r"C(x) = C_0 \exp\left[\frac{ux}{2E_x}(1 - \sqrt{1+4\alpha})\right] \quad x \ge 0")
            else: # alpha > 380
                st.markdown(r"当 $\alpha > 380$ 时，采用以下模型：")
                st.latex(r"C_0 = \frac{C_pQ_p + C_hQ_h}{2A\sqrt{kE_x}}")
                st.latex(r"C = C_0 \exp\left(x\sqrt{\frac{k}{E_x}}\right) \quad x < 0")
                st.latex(r"C = C_0 \exp\left(-x\sqrt{\frac{k}{E_x}}\right) \quad x \ge 0")
            
            # Need H for consistent param dict? H is not used in this 1D model anymore but might be good to keep or derive
            H = A_area / B if B != 0 else 0

        with st.expander("预测方案设置", expanded=True):
            scheme_sw = st.radio("方案选择", ["方案一：预测沿程浓度变化", "方案二：预测指定位置浓度"], horizontal=True, key="sw_scheme")
            
            if "方案一" in scheme_sw:
                st.markdown("**方案一：计算沿程不同距离处的浓度，绘制曲线图，计算超标距离**")
                c1, c2, c3 = st.columns(3)
                with c1: x_min = st.number_input("预测起始范围Xmin (m)", value=0.0, key="sw_xmin")
                with c2: x_max = st.number_input("预测最大范围Xmax (m)", value=10000.0, key="sw_xmax")
                with c3: dx = st.number_input("x剖分间距", value=10.0, key="sw_dx")
                params = {
                    "Qp": Qp, "Cp": Cp, "Qh": Qh, "Ch": Ch, "limit_val": limit_val,
                    "u": u, "K": K, "Ex": Ex, "B": B, "A": A_area, "H": H,
                    "x_min": x_min, "x_max": x_max, "dx": dx,
                    "scheme": "scheme1"
                }
            else:
                st.markdown("**方案二：计算指定位置浓度，评价超标情况**")
                st.write("预测位置 (m)")
                x_str = st.text_input("预测位置 (m) [逗号分隔]", value="500, 800, 1000, 5000, 10000", label_visibility="collapsed", key="sw_x_str")
                params = {
                    "Qp": Qp, "Cp": Cp, "Qh": Qh, "Ch": Ch, "limit_val": limit_val,
                    "u": u, "K": K, "Ex": Ex, "B": B, "A": A_area, "H": H,
                    "x_str": x_str,
                    "scheme": "scheme2"
                }

        if st.button("开始计算", type="primary"):
            # Consumption Check Logic
            try:
                dists_to_check = []
                if params.get("scheme") == "scheme1":
                     dists_to_check = [params.get("x_max", 0)]
                elif params.get("scheme") == "scheme2":
                     x_s = params.get("x_str", "")
                     dists_to_check = [float(x.strip()) for x in x_s.split(',') if x.strip()]
                
                max_dist_req = max(dists_to_check) if dists_to_check else 0
            except:
                max_dist_req = 99999

            if st.session_state.user_id:
                if max_dist_req <= 1000:
                    st.success("预测距离 ≤ 1000m，本次免费！")
                else:
                    if not db_manager.consume_usage(st.session_state.user_id):
                        st.error("剩余使用次数不足，请充值！(超过1000m的预测需要消耗次数)")
                        st.stop()
                    else:
                        st.info("已消耗 1 次预测次数")
            else:
                 if max_dist_req > 1000:
                      st.error("未登录用户最大预测距离不能超过1000m")
                      st.stop()

            st.markdown("### 方案一计算结果如下：") 

            if params["scheme"] == "scheme1":
                x_vals = np.arange(params["x_min"], params["x_max"] + params["dx"], params["dx"])
                res = surfacewater_models.calculate_river_1d_steady(
                    params["Cp"], params["Qp"], params["Ch"], params["Qh"], 
                    params["K"], params["u"], params["Ex"], params["B"], params["H"], x_vals
                )
                
                max_c = np.max(res)
                
                # Check exceedance
                exceed_mask = res > params["limit_val"]
                if np.any(exceed_mask):
                    x_ex = x_vals[exceed_mask]
                    exceed_str = f"第{x_ex[0]:.0f}m到第{x_ex[-1]:.0f}m"
                else:
                    exceed_str = "未超标"

                tab1, tab2 = st.tabs(["📈 曲线图", "💾 数据表格"])
                
                with tab1:
                    st.write(f"最大浓度为： `{max_c:.2f}` mg/L")
                    st.write(f"超标距离为{exceed_str}")
                    st.error("*注：超标距离是根据计算范围内的数进行统计，若最大计算范围仍然超标，则需扩大计算范围以便获得更准确的超标距离。")
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=x_vals, y=res, mode='lines', name='浓度 (mg/l)', line=dict(dash='dash', color='blue')))
                    fig.add_hline(y=params["limit_val"], line_color="skyblue", annotation_text="标准值")
                    fig.update_layout(xaxis_title="距离(m)", yaxis_title="浓度(mg/L)", showlegend=True)
                    st.plotly_chart(fig)
                    
                with tab2:
                    df_res = pd.DataFrame({"距离(m)": x_vals, "浓度 (mg/l)": res})
                    
                    def highlight_sw(val):
                        if val > params["limit_val"]: return 'color: red'
                        return ''
                    
                    st.dataframe(df_res.style.map(highlight_sw, subset=["浓度 (mg/l)"]), use_container_width=True)
                    st.caption("注：红色表示大于标准值")

            elif params["scheme"] == "scheme2":
                try:
                    x_locs = [float(x.strip()) for x in params["x_str"].split(',') if x.strip()]
                    # Check limit if not logged in
                    if not st.session_state.user_id:
                         valid_locs = [x for x in x_locs if x <= 1000]
                         if len(valid_locs) < len(x_locs):
                             st.error("未登录或权限不足，预测距离不能大于1000m!")
                             x_locs = valid_locs
                except:
                    st.error("位置格式错误")
                    st.stop()
                    
                x_vals = np.array(x_locs)
                res = surfacewater_models.calculate_river_1d_steady(
                    params["Cp"], params["Qp"], params["Ch"], params["Qh"], 
                    params["K"], params["u"], params["Ex"], params["B"], params["H"], x_vals
                )
                
                df_res = pd.DataFrame({"距离 (m)": x_vals, "浓度 (mg/l)": res})
                
                def highlight_sw(val):
                    if val > params["limit_val"]: return 'color: red'
                    return ''
                
                st.dataframe(df_res.style.map(highlight_sw, subset=["浓度 (mg/l)"]), use_container_width=True)
                st.caption("注：红色表示大于标准值，蓝色表示大于检出限，绿色表示小于检出限；鼠标移动至表格，右上角有下载表格、数据查找、表格全屏等功能。")

            # Save Results Logic
            if st.session_state.user_id:
                if st.button("保存计算结果到数据库", key="btn_save_res_sw"):
                     # Convert numpy array to list for JSON serialization
                    if isinstance(res, np.ndarray):
                        res_list = res.tolist()
                    else:
                        res_list = res
                        
                    results_data = {"result": res_list}
                    if isinstance(x_vals, np.ndarray):
                        results_data["x"] = x_vals.tolist()
                    else:
                        results_data["x"] = list(x_vals)
                    
                    # Add UI State
                    params["_ui_state"] = get_ui_state(["sw_"])
                    
                    db_manager.save_calculation(
                        st.session_state.user_id,
                        project_name,
                        "Surface Water - 1D Steady",
                        params,
                        results_data
                    )
                    st.success("结果已保存到历史记录！")

    else:
        # 2D Mixing Model (Existing code or placeholder)
        st.info("二维岸边排放混合模型功能待完善，目前保留原逻辑...")
        # ... (Keep original 2D logic or update later)
        col1, col2 = st.columns(2)
        with col1:
             st.subheader("参数输入")
             # ...
             H = st.number_input("平均水深 H (m)", value=2.0, key="sw_H")
             My = st.number_input("横向混合系数 My (m²/s)", value=0.1, key="sw_My")
             dist_max_x = st.number_input("最大纵向距离 X (m)", value=1000.0, key="sw_dist_max_x")
             dist_max_y = st.number_input("最大横向距离 Y (m)", value=50.0, key="sw_dist_max_y")
             
             # Re-add inputs that were in the unified block but needed here
             Cp = st.number_input("排放口浓度 Cp (mg/L)", value=50.0, key="sw_Cp_2d")
             Qp = st.number_input("排放流量 Qp (m³/s)", value=0.5, key="sw_Qp_2d")
             Ch = st.number_input("河流背景浓度 Ch (mg/L)", value=0.1, key="sw_Ch_2d")
             Qh = st.number_input("河流流量 Qh (m³/s)", value=10.0, key="sw_Qh_2d")
             u = st.number_input("河流流速 u (m/s)", value=0.5, key="sw_u_2d")
             
             params = {"Cp": Cp, "Qp": Qp, "Ch": Ch, "Qh": Qh, "u": u, "H": H, "My": My, "dist_max_x": dist_max_x, "dist_max_y": dist_max_y}

        if st.button("开始计算"):
             # ... existing 2D calculation ...
             pass

def history_page():
    st.header("计算历史记录")
    if not st.session_state.user_id:
        st.warning("请先登录查看历史记录")
        return
        
    history = db_manager.get_user_calculations(st.session_state.user_id)
    
    if not history:
        st.info("暂无计算记录")
        return
        
    df = pd.DataFrame(history, columns=["ID", "项目名称", "模型类型", "创建时间"])
    st.dataframe(df, use_container_width=True)
    
    selected_id = st.selectbox("选择记录查看详情", df["ID"].tolist())
    if st.button("加载详情"):
        detail = db_manager.get_calculation_detail(selected_id)
        if detail:
            st.subheader(f"项目: {detail['project_name']}")
            st.write(f"模型: {detail['model_type']}")
            st.write(f"时间: {detail['created_at']}")
            st.json(detail['parameters'])
            
            st.markdown("---")
            st.subheader("📊 结果可视化")
            
            results = detail.get("results", {})
            if results and "result" in results:
                try:
                    res_data = np.array(results["result"])
                    
                    # 1D Data
                    if "x" in results and len(res_data.shape) == 1:
                        x_data = np.array(results["x"])
                        
                        tab_v1, tab_v2 = st.tabs(["📈 曲线图", "📄 数据表格"])
                        with tab_v1:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=x_data, y=res_data, mode='lines+markers', name='浓度'))
                            # Try to detect if it's time or distance based on params
                            x_label = "距离 (m)"
                            if "t_max" in detail['parameters']: # Suggests time-based scheme
                                x_label = "时间 (d)"
                            
                            fig.update_layout(
                                title="计算结果曲线",
                                xaxis_title=x_label,
                                yaxis_title="浓度 (mg/L)",
                                hovermode="x unified"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            
                        with tab_v2:
                            df_res = pd.DataFrame({x_label: x_data, "浓度 (mg/L)": res_data})
                            st.dataframe(df_res, use_container_width=True)
                            st.download_button(
                                "下载数据 (CSV)", 
                                df_res.to_csv(index=False).encode('utf-8-sig'), 
                                "result_1d.csv", 
                                "text/csv"
                            )
                            
                    # 2D Data
                    elif "x" in results and "y" in results and len(res_data.shape) == 2:
                        x_data = np.array(results["x"])
                        y_data = np.array(results["y"])
                        
                        tab_v1, tab_v2 = st.tabs(["🗺️ 浓度分布图", "📊 交互式等值线"])
                        
                        with tab_v1:
                            fig = go.Figure(data=go.Heatmap(
                                z=res_data,
                                x=x_data,
                                y=y_data,
                                colorscale='Viridis',
                                colorbar=dict(title='浓度 (mg/L)')
                            ))
                            fig.update_layout(title="二维浓度热力图", xaxis_title="X (m)", yaxis_title="Y (m)")
                            st.plotly_chart(fig, use_container_width=True)
                            
                        with tab_v2:
                            fig_c = go.Figure(data=go.Contour(
                                z=res_data,
                                x=x_data,
                                y=y_data,
                                colorscale='Viridis',
                                contours=dict(showlabels=True)
                            ))
                            fig_c.update_layout(title="二维浓度等值线图", xaxis_title="X (m)", yaxis_title="Y (m)")
                            st.plotly_chart(fig_c, use_container_width=True)
                            
                    # 3D Data
                    elif "x" in results and "y" in results and "z" in results and len(res_data.shape) == 3:
                        x_data = np.array(results["x"])
                        y_data = np.array(results["y"])
                        z_data = np.array(results["z"])
                        
                        st.info(f"三维数据 (尺寸: {res_data.shape}) - 展示Z轴切片")
                        
                        z_idx = st.slider("选择Z轴切片层级", 0, len(z_data)-1, len(z_data)//2)
                        current_z = z_data[z_idx]
                        
                        slice_data = res_data[z_idx, :, :]
                        
                        fig = go.Figure(data=go.Contour(
                            z=slice_data,
                            x=x_data,
                            y=y_data,
                            colorscale='Viridis',
                            contours=dict(showlabels=True)
                        ))
                        fig.update_layout(
                            title=f"Z = {current_z:.1f} m 处浓度分布", 
                            xaxis_title="X (m)", 
                            yaxis_title="Y (m)"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                    else:
                        st.warning("数据格式暂不支持高级可视化，请直接查看下方原始数据")
                        st.write(results["result"])
                        
                except Exception as e:
                    st.error(f"可视化加载出错: {e}")
                    st.write("原始数据:", results)
            else:
                st.info("该记录仅包含参数，无计算结果数据 (可能是旧版本记录或仅保存了参数)")

def main():
    with st.sidebar:
        st.title("水环境模型系统")
        
        if st.session_state.user_id:
            st.write(f"欢迎, {st.session_state.username}")
            if st.session_state.role == 'admin':
                st.info("管理员已登录")
            if st.button("退出登录"):
                logout()
        else:
            st.info("未登录状态")
            
        nav_options = ["主页", "地下水预测", "地表水预测", "用户信息", "联系"]
        if st.session_state.user_id:
            nav_options.append("会员充值")
        if st.session_state.role == 'admin':
            nav_options.append("后台管理")
            
        page = st.radio("导航", nav_options)
        
    if page == "主页":
        if not st.session_state.user_id:
            login_page()
        else:
            st.header("欢迎使用水环境污染解析解计算系统")
            st.markdown("""
            本系统包含以下功能：
            1. **地下水预测**：基于 HJ610-2016 附录D 的解析解模型。
            2. **地表水预测**：基于 HJ2.3-2018 附录E 的解析解模型。
            3. **用户信息**：查看您的账户信息和剩余次数。
            4. **联系**：查看管理员联系方式。
            
            请在左侧侧边栏选择功能模块。
            """)
            
    elif page == "地下水预测":
        groundwater_page()
    elif page == "地表水预测":
        surfacewater_page()
    elif page == "用户信息":
        user_info_page()
    elif page == "联系":
        contact_page()
    elif page == "会员充值":
        membership_page()
    elif page == "后台管理":
        admin_page()

if __name__ == "__main__":
    main()
