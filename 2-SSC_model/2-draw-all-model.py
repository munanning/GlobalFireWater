import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_squared_log_error
import math
import os

# 定义模型及其对应的预测结果文件
models = {
    'RandomForest': 'RFmodel_prediction_results.csv',
    'XGBoost': 'XGBoost_model_prediction_results.csv',
    'SVR': 'SVR_model_prediction_results.csv',
    'DNN': 'DNN_model_prediction_results.csv'
}

input_colors = ['#2a9d8f', '#e9c46a', '#415a77', '#e76f51']


# Metrics functions
def ei(y, ypred):
    df = pd.DataFrame({'y': y, 'ypred': ypred})
    df = df[(df['y'] >= 0) & (df['ypred'] >= 0)]
    Y = np.median(abs(np.log10(df['ypred'] / df['y'])))
    return 100 * (math.e ** Y - 1)


def bias(y, ypred):
    df = pd.DataFrame({'y': y, 'ypred': ypred})
    df = df[(df['y'] >= 0) & (df['ypred'] >= 0)]
    z = np.median(np.log10(df['ypred'] / df['y']))
    return 100 * np.sign(z) * (math.e ** abs(z) - 1)


def r2_score_custom(y, ypred):
    return np.corrcoef(y, ypred)[0, 1] ** 2


def calculate_metrics(y, ypred):
    ei_index = ei(y, ypred)
    bias_index = bias(y, ypred)
    r2_index = r2_score_custom(y, ypred)
    rmse_index = np.sqrt(np.mean((ypred - y) ** 2))
    return ei_index, bias_index, r2_index, rmse_index


# 创建 1x4 的子图
fig, axes = plt.subplots(2, 2, figsize=(8, 8), dpi=300)
axes = axes.flatten()  # 将二维数组展平成一维便于迭代


# 遍历每个模型及其对应的颜色
for idx, (model_name, prediction_file) in enumerate(models.items()):
    ax = axes[idx]
    color = input_colors[idx]

    # 检查预测结果文件是否存在
    if not os.path.exists(prediction_file):
        print(f"预测结果文件 '{prediction_file}' 不存在，跳过 {model_name} 模型。")
        ax.set_visible(False)
        continue

    # 读取预测结果
    data = pd.read_csv(prediction_file)
    in_situ = data['Actual']
    pred = data['Predicted']

    # 计算性能指标
    error, bias_val, r2_val, rmse_val = calculate_metrics(in_situ, pred)

    # 创建散点图
    ax.scatter(in_situ, pred, s=20, c=color, alpha=0.5, edgecolor='none')
    ax.plot([1, 5000], [1, 5000], ls='--', c='k', alpha=0.8)

    # 设置对数坐标轴
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(1, 5000)
    ax.set_ylim(1, 5000)

    # 添加核密度估计
    lower_bound, upper_bound = 1, 5000  # 设置合理的上下限
    filtered_in_situ = in_situ[(in_situ >= lower_bound) & (in_situ <= upper_bound)]
    filtered_pred = pred[(pred >= lower_bound) & (pred <= upper_bound)]

    sns.kdeplot(x=filtered_in_situ, y=filtered_pred, levels=[0.5, 0.7, 0.9], color='k', linewidths=0.5, zorder=100, ls='--', ax=ax)

    # 添加水平和垂直线
    for val in [1, 10, 100, 1000]:
        ax.axhline(y=val, linestyle='-', color='gray', alpha=0.5, lw=0.3)
        ax.axvline(x=val, linestyle='-', color='gray', alpha=0.5, lw=0.3)

    # 注释性能指标
    ax.text(0.60, 0.06, '$\it{Error}$' + ' = ' + '{}%'.format(round(error, 2)), transform=ax.transAxes, zorder=200)
    ax.text(0.60, 0.20, '$\it{Bias}$' + ' = ' + '{}%'.format(round(bias_val, 2)), transform=ax.transAxes, zorder=200)
    ax.text(0.06, 0.88, '$\it{R²}$' + ' = ' + '{}'.format(round(r2_val, 2)), transform=ax.transAxes, zorder=200)
    ax.text(0.06, 0.74, '$\it{RMSE}$' + ' = ' + '{} mg/L'.format(round(rmse_val, 2)), transform=ax.transAxes,
            zorder=200)

    # 设置标签和标题
    ax.set_xlabel('Actual SSC (mg/L)')
    if idx == 0:
        ax.set_ylabel('Predicted SSC (mg/L)')
    ax.set_title(f'{model_name} Prediction')

    # 添加图例（可选）
    # ax.legend()

# 调整布局
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# 保存绘图
plt.savefig('SSC_Prediction_Comparison_All_Models.png', dpi=300, bbox_inches='tight')

# 显示绘图
plt.show()
