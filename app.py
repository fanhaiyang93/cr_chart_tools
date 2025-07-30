# 解决PyInstaller打包后的matplotlib字体问题
import os
import sys

# 添加字体文件路径
font_path = os.path.join(os.path.dirname(__file__), 'fonts/OTF/SimplifiedChinese/SourceHanSansSC-Regular.otf')

if getattr(sys, 'frozen', False):
    # 运行在PyInstaller打包环境中
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    
    # 设置matplotlib缓存目录
    import tempfile
    cache_dir = os.path.join(tempfile.gettempdir(), 'matplotlib')
    os.makedirs(cache_dir, exist_ok=True)
    os.environ['MPLCONFIGDIR'] = cache_dir
    
    # 预加载matplotlib以避免运行时字体扫描
    import matplotlib.pyplot as plt
    plt.ioff()  # 关闭交互模式

# 原有的imports
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
from matplotlib.patches import Polygon
from matplotlib.collections import LineCollection
import matplotlib.patches as mpatches
import socket
import webbrowser
import threading

# 设置页面配置
st.set_page_config(
    page_title="城市人效与CR值分析工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 设置中文字体
if os.path.exists(font_path):
    plt.rcParams['font.family'] = ['Source Han Sans SC']
    plt.rcParams['axes.unicode_minus'] = False
    import matplotlib.font_manager as fm
    fm.fontManager.addfont(font_path)
else:
    st.error("未找到字体文件，中文显示可能会出现问题。")

def validate_data(df):
    """验证数据格式和内容"""
    errors = []
    warnings = []
    
    # 检查必需列
    required_columns = ['城市', '人效', 'CR值', '离职率']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"缺少必需的列：{', '.join(missing_columns)}")
        return errors, warnings
    
    # 检查数据是否为空
    if df.empty:
        errors.append("数据为空")
        return errors, warnings
    
    # 检查数值列
    numeric_columns = ['人效', 'CR值', '离职率']
    for col in numeric_columns:
        try:
            pd.to_numeric(df[col], errors='raise')
        except (ValueError, TypeError):
            errors.append(f"列'{col}'包含非数值数据")
    
    # 检查离职率范围
    try:
        turnover_rates = pd.to_numeric(df['离职率'], errors='coerce')
        if turnover_rates.min() < 0 or turnover_rates.max() > 1:
            warnings.append("离职率建议在0-1之间")
    except:
        pass
    
    # 检查是否有重复城市
    if df['城市'].duplicated().any():
        warnings.append("存在重复的城市名称")
    
    return errors, warnings

def calculate_boundary_lines(x_range, slope, intercept, y_threshold, slope_change_ratio):
    """计算上边界线（当y值超过阈值时改变斜率）"""
    x_vals = []
    y_vals = []
    
    for x in x_range:
        y = slope * x + intercept
        if y > y_threshold:
            # 使用新斜率
            new_slope = slope * slope_change_ratio
            # 计算新截距，使得在阈值点连续
            x_threshold = (y_threshold - intercept) / slope
            new_intercept = y_threshold - new_slope * x_threshold
            y = new_slope * x + new_intercept
        x_vals.append(x)
        y_vals.append(y)
    
    return x_vals, y_vals

def calculate_lower_boundary_lines(x_range, slope, intercept, y_threshold, slope_change_ratio):
    """计算下边界线（当y值低于阈值时改变斜率）"""
    x_vals = []
    y_vals = []
    
    for x in x_range:
        y = slope * x + intercept
        if y < y_threshold:
            # 使用新斜率
            new_slope = slope * slope_change_ratio
            # 计算新截距，使得在阈值点连续
            x_threshold = (y_threshold - intercept) / slope
            new_intercept = y_threshold - new_slope * x_threshold
            y = new_slope * x + new_intercept
        x_vals.append(x)
        y_vals.append(y)
    
    return x_vals, y_vals

def classify_city_region(x, y, config):
    """判断城市在图表中的映射结果"""
    # 确保x和y是数值类型
    try:
        x = float(x)
        y = float(y)
    except (ValueError, TypeError):
        return "数据错误"
    # 基准点和标准线
    point1 = (config['point1_x'], config['point1_y'])
    point2 = (config['point2_x'], config['point2_y'])
    
    # 计算标准线斜率和截距
    slope = (point2[1] - point1[1]) / (point2[0] - point1[0])
    intercept = point1[1] - slope * point1[0]
    
    # 计算上边界线在该x坐标的y值
    upper_intercept = intercept + config['float_ratio']
    upper_y = slope * x + upper_intercept
    if upper_y > config['upper_y_threshold']:
        new_slope = slope * config['upper_slope_ratio']
        x_threshold = (config['upper_y_threshold'] - upper_intercept) / slope
        new_intercept = config['upper_y_threshold'] - new_slope * x_threshold
        upper_y = new_slope * x + new_intercept
    
    # 计算下边界线在该x坐标的y值
    lower_intercept = intercept - config['float_ratio']
    lower_y = slope * x + lower_intercept
    if lower_y < config['lower_y_threshold']:
        new_slope = slope * config['lower_slope_ratio']
        x_threshold = (config['lower_y_threshold'] - lower_intercept) / slope
        new_intercept = config['lower_y_threshold'] - new_slope * x_threshold
        lower_y = new_slope * x + new_intercept
    
    # 判断点的位置
    if y > upper_y:
        return "超额支付"
    elif y < lower_y:
        return "价值低估"
    else:
        return "合理区间"

def create_scatter_plot(df, config):
    """创建散点图"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 数据类型转换，确保数值列为float类型
    df = df.copy()
    try:
        # 先检查数据是否为空
        if df.empty:
            raise ValueError("输入数据为空")
        
        # 转换数值列，使用errors='coerce'将无效值转为NaN
        df['人效'] = pd.to_numeric(df['人效'], errors='coerce')
        df['CR值'] = pd.to_numeric(df['CR值'], errors='coerce')
        df['离职率'] = pd.to_numeric(df['离职率'], errors='coerce')
        
        # 检查转换后是否有有效数据
        valid_rows_before = len(df)
        
        # 删除包含NaN的行
        df = df.dropna(subset=['人效', 'CR值', '离职率'])
        
        valid_rows_after = len(df)
        
        if df.empty:
            raise ValueError("数据转换后为空，请检查数据格式。可能原因：\n1. 人效、CR值、离职率列包含非数值数据\n2. 存在空值或无效数据")
        
        if valid_rows_after < valid_rows_before:
            print(f"警告：已自动删除 {valid_rows_before - valid_rows_after} 行包含无效数据的记录")
        
        # 确保数据类型为float
        df['人效'] = df['人效'].astype(float)
        df['CR值'] = df['CR值'].astype(float)
        df['离职率'] = df['离职率'].astype(float)
            
    except Exception as e:
        raise ValueError(f"数据格式错误：{str(e)}。请确保人效、CR值、离职率列包含有效数值")
    
    # 获取配置参数
    x_min = config['x_min']
    x_max = config['x_max']
    y_min = config['y_min']
    y_max = config['y_max']
    
    # 基准点和标准线
    point1 = (config['point1_x'], config['point1_y'])
    point2 = (config['point2_x'], config['point2_y'])
    
    # 计算标准线斜率和截距
    slope = (point2[1] - point1[1]) / (point2[0] - point1[0])
    intercept = point1[1] - slope * point1[0]
    
    # 生成x轴范围
    x_range = np.linspace(x_min, x_max, 1000)
    
    # 计算上边界线
    upper_intercept = intercept + config['float_ratio']
    raw_upper_x, raw_upper_y = calculate_boundary_lines(
        x_range, slope, upper_intercept, 
        config['upper_y_threshold'], config['upper_slope_ratio']
    )
    
    # 计算下边界线
    lower_intercept = intercept - config['float_ratio']
    raw_lower_x, raw_lower_y = calculate_lower_boundary_lines(
        x_range, slope, lower_intercept,
        config['lower_y_threshold'], config['lower_slope_ratio']
    )
    
    # 直接使用原始边界线数据，不做交叉处理
    upper_x = raw_upper_x
    upper_y = raw_upper_y
    lower_x = raw_lower_x
    lower_y = raw_lower_y
    
    # 填充区域
    # 超额支付区域（上边界线以上）
    if len(upper_x) > 0 and len(upper_y) > 0:
        ax.fill_between(x_range, upper_y, y_max, 
                       color=config['overpay_color'], alpha=0.3, label='超额支付')
    
    # 价值低估区域（下边界线以下）
    if len(lower_x) > 0 and len(lower_y) > 0:
        # 为下边界线创建对应的y值数组
        lower_y_full = np.interp(x_range, lower_x, lower_y, left=y_min, right=y_min)
        ax.fill_between(x_range, y_min, lower_y_full, 
                       color=config['undervalue_color'], alpha=0.3, label='价值低估')
    
    # 合理区间（两条边界线之间）
    if len(upper_x) > 0 and len(upper_y) > 0 and len(lower_x) > 0 and len(lower_y) > 0:
        # 为下边界线创建对应的y值数组
        lower_y_full = np.interp(x_range, lower_x, lower_y, left=y_min, right=y_min)
        ax.fill_between(x_range, lower_y_full, upper_y, 
                       color=config['reasonable_color'], alpha=0.3, label='合理区间')
    elif len(upper_x) > 0 and len(upper_y) > 0:
        # 如果只有上边界线，填充从y_min到上边界线
        ax.fill_between(x_range, y_min, upper_y, 
                       color=config['reasonable_color'], alpha=0.3, label='合理区间')
    elif len(lower_x) > 0 and len(lower_y) > 0:
        # 如果只有下边界线，填充从下边界线到y_max
        lower_y_full = np.interp(x_range, lower_x, lower_y, left=y_min, right=y_min)
        ax.fill_between(x_range, lower_y_full, y_max, 
                       color=config['reasonable_color'], alpha=0.3, label='合理区间')
    
    # 绘制标准线（添加边界约束）
    standard_y = slope * x_range + intercept
    
    # 确保标准线不超出上下边界线的范围
    # 对每个x点，标准线的y值应该在对应的上下边界线之间
    for i in range(len(standard_y)):
        # 找到对应x值在边界线中的位置
        x_val = x_range[i]
        
        # 计算该x值对应的上下边界线y值
        if len(upper_x) > 0 and len(upper_y) > 0:
            upper_y_val = np.interp(x_val, upper_x, upper_y)
        else:
            upper_y_val = y_max
            
        if len(lower_x) > 0 and len(lower_y) > 0:
            lower_y_val = np.interp(x_val, lower_x, lower_y)
        else:
            lower_y_val = y_min
        
        # 约束标准线在边界线范围内
        if standard_y[i] > upper_y_val:
            standard_y[i] = upper_y_val
        elif standard_y[i] < lower_y_val:
            standard_y[i] = lower_y_val
    
    ax.plot(x_range, standard_y, 'g-', linewidth=1, label='标准线')
    
    # 绘制边界线（实线，变细）
    if len(upper_x) > 0 and len(upper_y) > 0:
        ax.plot(upper_x, upper_y, 'r-', linewidth=1, label='上边界线')
    if len(lower_x) > 0 and len(lower_y) > 0:
        ax.plot(lower_x, lower_y, 'b-', linewidth=1, label='下边界线')
    
    # 绘制基于基准点1的参考线（虚线）
    ax.axhline(y=point1[1], color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
    ax.axvline(x=point1[0], color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
    
    # 绘制散点
    if not df.empty:
        # 根据离职率设置颜色深度，确保颜色映射始终从0开始
        turnover_min = 0  # 强制设置最小值为0
        turnover_max = max(df['离职率'].max(), 0.1)  # 确保最大值至少为0.1，避免除零错误
        
        # 标准化离职率到0-1范围，确保从0开始
        normalized_turnover = (df['离职率'] - turnover_min) / (turnover_max - turnover_min)
        # 确保标准化后的值在0-1范围内
        normalized_turnover = np.clip(normalized_turnover, 0, 1)
        
        scatter = ax.scatter(df['人效'], df['CR值'], 
                           c=df['离职率'], cmap='Reds', 
                           vmin=turnover_min, vmax=turnover_max,  # 设置颜色条范围从0开始
                           s=100, alpha=0.7, edgecolors='black', linewidth=0.5)
        
        # 添加城市标签
        for i, row in df.iterrows():
            ax.annotate(row['城市'], 
                       (row['人效'], row['CR值']), 
                       xytext=(5, 5), textcoords='offset points',
                       fontsize=8, ha='left')
        
        # 添加颜色条，确保从0开始显示
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('离职率', rotation=270, labelpad=15)
        # 设置颜色条的刻度，确保从0开始
        cbar.set_ticks(np.linspace(turnover_min, turnover_max, 6))
    
    # 设置坐标轴
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    
    # 设置X轴刻度，使用计算出的步长，确保不超出范围
    x_step = config.get('x_step', 1.0)
    # 生成刻度，确保不超出x_max
    x_ticks = np.arange(x_min, x_max + x_step/2, x_step)
    # 过滤掉超出范围的刻度
    x_ticks = x_ticks[x_ticks <= x_max]
    ax.set_xticks(x_ticks)
    
    # 设置Y轴刻度，使用计算出的步长，确保不超出范围
    y_step = config.get('y_step', 0.1)
    # 生成刻度，确保不超出y_max
    y_ticks = np.arange(y_min, y_max + y_step/2, y_step)
    # 过滤掉超出范围的刻度
    y_ticks = y_ticks[y_ticks <= y_max]
    ax.set_yticks(y_ticks)
    ax.set_xlabel('人效', fontsize=12)
    ax.set_ylabel('CR值', fontsize=12)
    ax.set_title('城市人效与CR值分析图', fontsize=14, fontweight='bold')
    
    # 添加网格
    ax.grid(True, alpha=0.3)
    
    # 添加图例
    ax.legend(loc='upper left', bbox_to_anchor=(0, 1))
    
    plt.tight_layout()
    return fig

def main():
    st.title("📊 城市人效与CR值分析工具")
    
    # 侧边栏 - 参数配置
    st.sidebar.header("参数配置")
    
    # 坐标轴配置
    st.sidebar.subheader("坐标轴配置")
    x_min = st.sidebar.number_input("X轴最小值", value=190.0, step=0.1)
    x_max = st.sidebar.number_input("X轴最大值", value=2470.0, step=0.1)
    y_min = st.sidebar.number_input("Y轴最小值", value=0.4, step=0.1)
    y_max = st.sidebar.number_input("Y轴最大值", value=1.6, step=0.1)
    x_step_constant = st.sidebar.number_input("X轴分段数", value=20.0, step=1.0)
    y_step_constant = st.sidebar.number_input("Y轴分段数", value=6.0, step=1.0)
    
    # 计算X轴步长：(x轴最大值-x轴最小值)/2/计算常量
    x_step = (x_max - x_min) / x_step_constant
    st.sidebar.text(f"计算得出的X轴步长: {x_step:.2f}")
    
    # 计算Y轴步长：(y轴最大值+y轴最小值)/2/计算常量
    y_step = (y_max - y_min) / y_step_constant
    st.sidebar.text(f"计算得出的Y轴步长: {y_step:.3f}")
    
    # 基准点配置
    st.sidebar.subheader("基准点配置")
    point1_x = st.sidebar.number_input("基准点1 X坐标", value=1330.0, step=0.1)
    point1_y = st.sidebar.number_input("基准点1 Y坐标", value=1.0, step=0.1)
    point2_x = st.sidebar.number_input("基准点2 X坐标", value=1520.0, step=0.1)
    point2_y = st.sidebar.number_input("基准点2 Y坐标", value=1.1, step=0.1)
    
    # 边界线配置
    st.sidebar.subheader("边界线配置")
    float_ratio = st.sidebar.number_input("浮动比例", value=0.15, step=0.01)
    upper_y_threshold = st.sidebar.number_input("上边界Y轴阈值", value=1.25, step=0.1)
    upper_slope_ratio = st.sidebar.number_input("上边界斜率变化比例", value=0.5, step=0.1)
    lower_y_threshold = st.sidebar.number_input("下边界Y轴阈值", value=0.75, step=0.1)
    lower_slope_ratio = st.sidebar.number_input("下边界斜率变化比例", value=0.5, step=0.1)
    
    # 颜色配置
    st.sidebar.subheader("颜色配置")
    reasonable_color = st.sidebar.color_picker("合理区间颜色", value="#90EE90")
    overpay_color = st.sidebar.color_picker("超额支付颜色", value="#FFB6C1")
    undervalue_color = st.sidebar.color_picker("价值低估颜色", value="#87CEEB")
    
    # 主界面布局
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("数据导入")
        
        # 文件上传
        uploaded_file = st.file_uploader(
            "选择Excel或CSV文件", 
            type=['xlsx', 'xls', 'csv'],
            help="文件应包含：城市、人效、CR值、离职率四列"
        )
        
        # 示例数据和模板
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("使用示例数据", use_container_width=True):
                sample_data = {
                   '城市': ['合肥','苏州','成都','武汉','济南','杭州','西安','郑州','青岛','长沙','南京','东莞','天津','宁波','佛山','无锡','沈阳','重庆','大连'],
                   '人效': [1405.62, 1874.77, 1591.06, 815.20, 963.98, 1751.92, 1413.03, 580.65, 1141.69, 896.13, 1109.96, 1278.20, 1112.95, 1324.32, 1129.46, 1259.64, 982.72, 768.20, 623.56],
                   'CR值': [1.53, 1.28, 1.21, 1.20, 1.18, 1.16, 1.08, 1.07, 1.06, 1.05, 1.05, 1.03, 1.01, 0.98, 0.93, 0.80, 0.79, 0.77, 0.57],
                   '离职率': [0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.065, 0.07, 0.075, 0.08, 0.085, 0.09, 0.095, 0.10, 0.105, 0.11]
                 }
                df = pd.DataFrame(sample_data)
                # 确保映射结果列存在
                if '映射结果' not in df.columns:
                    df['映射结果'] = ""
                st.session_state['df'] = df
                st.success("示例数据已加载！")
        
        with col_b:
            # 下载模板
            template_data = {
                '城市': ['城市A', '城市B', '城市C'],
                '人效': [5.0, 6.0, 4.5],
                'CR值': [1.2, 1.1, 1.3],
                '离职率': [0.10, 0.15, 0.08]
            }
            template_df = pd.DataFrame(template_data)
            csv_template = template_df.to_csv(index=False, encoding='utf-8-sig')
            
            st.download_button(
                label="📥 下载模板",
                data=csv_template,
                file_name="数据模板.csv",
                mime="text/csv",
                use_container_width=True,
                help="下载标准数据格式模板"
            )
        
        # 处理上传的文件
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                # 确保映射结果列存在
                if '映射结果' not in df.columns:
                    df['映射结果'] = ""
                
                st.session_state['df'] = df
                st.success("文件上传成功！")
            except Exception as e:
                st.error(f"文件读取错误：{str(e)}")
        
        # 显示和编辑数据
        if 'df' in st.session_state:
            st.subheader("数据预览")
            
            # 检查数据列名
            required_columns = ['城市', '人效', 'CR值', '离职率']
            missing_columns = [col for col in required_columns if col not in st.session_state['df'].columns]
            
            if missing_columns:
                st.error(f"缺少必需的列：{', '.join(missing_columns)}")
                st.info("请确保数据包含以下列：城市、人效、CR值、离职率")
            else:
                st.success("数据格式正确！")
            
            # 移除映射结果列（如果存在）
            df_for_editor = st.session_state['df'].copy()
            if '映射结果' in df_for_editor.columns:
                df_for_editor = df_for_editor.drop(columns=['映射结果'])
            
            edited_df = st.data_editor(
                df_for_editor,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "人效": st.column_config.NumberColumn(
                        "人效",
                        help="人效指标（数值）",
                        min_value=0,
                        format="%.2f"
                    ),
                    "CR值": st.column_config.NumberColumn(
                        "CR值",
                        help="CR值指标（数值）",
                        min_value=0,
                        format="%.2f"
                    ),
                    "离职率": st.column_config.NumberColumn(
                        "离职率",
                        help="离职率（0-1之间的数值）",
                        min_value=0,
                        max_value=1,
                        format="%.3f"
                    )
                }
            )
            
            # 检查数据是否有变化
            if not df_for_editor.equals(edited_df):
                # 更新session state中的数据（不包含映射结果列）
                st.session_state['df'] = edited_df.copy()
            
            # 显示映射结果表格（如果存在）
            if 'mapping_results' in st.session_state and st.session_state['mapping_results'] is not None:
                st.subheader("📊 映射结果")
                st.dataframe(
                    st.session_state['mapping_results'],
                    use_container_width=True,
                    column_config={
                        "人效": st.column_config.NumberColumn(
                            "人效",
                            help="人效指标（数值）",
                            format="%.2f"
                        ),
                        "CR值": st.column_config.NumberColumn(
                            "CR值",
                            help="CR值指标（数值）",
                            format="%.2f"
                        ),
                        "离职率": st.column_config.NumberColumn(
                            "离职率",
                            help="离职率（0-1之间的数值）",
                            format="%.3f"
                        ),
                        "映射结果": st.column_config.TextColumn(
                            "映射结果",
                            help="城市在图表中的映射结果"
                        )
                    }
                )
    
    with col2:
        st.header("数据分析")
        
        # 计算映射结果按钮
        if st.button("🔍 计算映射结果", type="secondary", use_container_width=True):
            if 'df' not in st.session_state:
                st.error("请先导入数据！")
            else:
                # 使用数据编辑器中当前显示的数据进行验证和计算
                current_data = edited_df if 'edited_df' in locals() else st.session_state['df']
                
                # 验证数据
                errors, warnings = validate_data(current_data)
                
                if errors:
                    st.error("数据验证失败：")
                    for error in errors:
                        st.error(f"• {error}")
                else:
                    # 显示警告（如果有）
                    if warnings:
                        for warning in warnings:
                            st.warning(f"⚠️ {warning}")
                    
                    try:
                        # 使用数据编辑器中的当前数据进行处理
                        df_with_region = current_data.copy()
                        
                        # 强制转换数值列类型
                        df_with_region['人效'] = pd.to_numeric(df_with_region['人效'], errors='coerce')
                        df_with_region['CR值'] = pd.to_numeric(df_with_region['CR值'], errors='coerce')
                        
                        # 配置参数
                        config = {
                            'x_min': x_min, 'x_max': x_max, 'y_min': y_min, 'y_max': y_max,
                            'x_step': x_step, 'y_step': y_step,
                            'point1_x': point1_x, 'point1_y': point1_y,
                            'point2_x': point2_x, 'point2_y': point2_y,
                            'float_ratio': float_ratio,
                            'upper_y_threshold': upper_y_threshold, 'upper_slope_ratio': upper_slope_ratio,
                            'lower_y_threshold': lower_y_threshold, 'lower_slope_ratio': lower_slope_ratio,
                            'reasonable_color': reasonable_color, 'overpay_color': overpay_color, 'undervalue_color': undervalue_color
                        }
                        
                        with st.spinner("正在计算映射结果..."):
                            # 计算映射结果
                            df_with_region['映射结果'] = df_with_region.apply(
                                lambda row: classify_city_region(row['人效'], row['CR值'], config), axis=1
                            )
                            
                            # 保存映射结果到session state，用于在预览数据下方显示
                            st.session_state['mapping_results'] = df_with_region
                            
                            st.success("✅ 映射结果计算完成！请查看下方的映射结果表格。")
                            
                            # 强制重新渲染页面以显示映射结果
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"计算映射结果时出错：{str(e)}")
        
        st.header("图表生成")
        
        if 'df' in st.session_state and not st.session_state['df'].empty:
            # 配置参数字典
            config = {
                'x_min': x_min, 'x_max': x_max, 'y_min': y_min, 'y_max': y_max,
                'x_step': x_step, 'y_step': y_step,
                'point1_x': point1_x, 'point1_y': point1_y,
                'point2_x': point2_x, 'point2_y': point2_y,
                'float_ratio': float_ratio,
                'upper_y_threshold': upper_y_threshold, 'upper_slope_ratio': upper_slope_ratio,
                'lower_y_threshold': lower_y_threshold, 'lower_slope_ratio': lower_slope_ratio,
                'reasonable_color': reasonable_color,
                'overpay_color': overpay_color,
                'undervalue_color': undervalue_color
            }
            
            # 按钮区域
            button_col1, button_col2 = st.columns(2)
            
            with button_col1:
                # 生成图表按钮
                if st.button("🎯 生成图表", type="primary", use_container_width=True):
                    # 优先使用映射结果数据，如果不存在则使用原始数据
                    if 'mapping_results' in st.session_state and st.session_state['mapping_results'] is not None:
                        df_for_chart = st.session_state['mapping_results'].copy()
                        chart_data_source = "映射结果数据"
                    else:
                        df_for_chart = st.session_state['df'].copy()
                        chart_data_source = "原始数据"
                    
                    # 验证数据
                    errors, warnings = validate_data(df_for_chart)
                    
                    if errors:
                        for error in errors:
                            st.error(error)
                        st.info("请修正数据错误后重试")
                    else:
                        # 显示警告（如果有）
                        for warning in warnings:
                            st.warning(warning)
                        
                        try:
                            with st.spinner("正在生成图表..."):
                                fig = create_scatter_plot(df_for_chart, config)
                                
                                # 保存图表到session state
                                st.session_state['current_fig'] = fig
                                st.success(f"图表生成成功！（基于{chart_data_source}）")
                            
                        except Exception as e:
                            st.error(f"图表生成错误：{str(e)}")
                            st.info(df_for_chart)
                            st.info("请检查数据格式是否正确，确保数值列包含有效数字")
            
            with button_col2:
                # 下载图片按钮
                if 'current_fig' in st.session_state:
                    # 直接显示下载按钮
                    img_buffer = io.BytesIO()
                    st.session_state['current_fig'].savefig(
                        img_buffer, format='png', dpi=300, bbox_inches='tight'
                    )
                    img_buffer.seek(0)
                    
                    st.download_button(
                        label="💾 下载图片",
                        data=img_buffer.getvalue(),
                        file_name="城市人效CR值分析图.png",
                        mime="image/png",
                        use_container_width=True,
                        type="secondary"
                    )
                else:
                    st.button("💾 下载图片", disabled=True, use_container_width=True, help="请先生成图表", type="secondary")
            
            # 显示已生成的图表
            if 'current_fig' in st.session_state:
                st.pyplot(st.session_state['current_fig'])
        else:
            st.info("请先导入数据")


def find_free_port(start_port=8501):
    """查找一个空闲端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        for port in range(start_port, 65535):
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                continue
    return None

def run_app():
    """启动Streamlit应用"""
    if getattr(sys, 'frozen', False):
        # PyInstaller打包环境
        port = find_free_port()
        if port is None:
            print("❌ 错误：找不到可用的端口")
            return

        print(f"正在启动城市人效CR分析工具...")
        print(f"请在浏览器中访问: http://localhost:{port}")
        
        try:
            import streamlit.web.bootstrap as bootstrap
            
            flag_options = {
                "server.port": port,
                "server.address": "localhost",
                "global.developmentMode": False,
                "server.enableCORS": True,
                "server.enableXsrfProtection": False,
                "browser.serverAddress": "localhost",
                "browser.serverPort": port,
                "server.headless": True,
                "server.runOnSave": False,
                "server.fileWatcherType": "none",
            }

            # 在新线程中打开浏览器
            threading.Timer(3, lambda: webbrowser.open(f"http://localhost:{port}")).start()
            
            bootstrap.run(
                __file__,
                "streamlit run",
                [],
                flag_options
            )
        except Exception as e:
            print(f"启动失败: {e}")
            print(f"请手动运行: streamlit run app.py --server.port {port}")
    else:
        # 开发环境
        import streamlit.web.cli as stcli
        port = find_free_port()
        if port is None:
            print("❌ 错误：找不到可用的端口")
            return
        sys.argv = ["streamlit", "run", __file__, "--server.port", str(port)]
        stcli.main()

def start_app():
    """主应用入口，根据环境决定是渲染UI还是启动服务"""
    # 在PyInstaller打包的应用中，脚本会被执行两次。
    # 第一次是启动服务，第二次是Streamlit内核加载脚本以渲染UI。
    # `streamlit.runtime.exists()`可以判断当前是否在Streamlit的渲染进程中。
    import streamlit.runtime
    if streamlit.runtime.exists():
        # 如果已经在Streamlit环境中，则直接渲染页面
        main()
    else:
        # 如果不是，则说明是首次启动（例如，通过点击可执行文件），需要启动Streamlit服务
        run_app()

if __name__ == "__main__":
    start_app()