import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_squared_log_error
import math
import os

# Define models and their corresponding prediction result files
models = {
    'RandomForest': 'RFmodel_prediction_results.csv',
    'XGBoost': 'XGBoost_model_prediction_results.csv',
    'SVR': 'SVR_model_prediction_results.csv',
    'DNN': 'DNN_model_prediction_results.csv'
}

input_colors = ['#2a9d8f', '#e9c46a', '#415a77', '#e76f51']


# Metrics functions
def ei(y, ypred):
    # Calculate Error Index (EI)
    df = pd.DataFrame({'y': y, 'ypred': ypred})
    df = df[(df['y'] >= 0) & (df['ypred'] >= 0)]
    Y = np.median(abs(np.log10(df['ypred'] / df['y'])))
    return 100 * (math.e ** Y - 1)


def bias(y, ypred):
    # Calculate Bias
    df = pd.DataFrame({'y': y, 'ypred': ypred})
    df = df[(df['y'] >= 0) & (df['ypred'] >= 0)]
    z = np.median(np.log10(df['ypred'] / df['y']))
    return 100 * np.sign(z) * (math.e ** abs(z) - 1)


def r2_score_custom(y, ypred):
    # Calculate R² (coefficient of determination)
    return np.corrcoef(y, ypred)[0, 1] ** 2


def calculate_metrics(y, ypred):
    # Compute all performance metrics
    ei_index = ei(y, ypred)
    bias_index = bias(y, ypred)
    r2_index = r2_score_custom(y, ypred)
    rmse_index = np.sqrt(np.mean((ypred - y) ** 2))
    return ei_index, bias_index, r2_index, rmse_index


# Create a 2x2 grid of subplots
fig, axes = plt.subplots(2, 2, figsize=(8, 8), dpi=300)
axes = axes.flatten()  # Flatten the axes array for easier iteration


# Iterate through each model and its corresponding color
for idx, (model_name, prediction_file) in enumerate(models.items()):
    ax = axes[idx]
    color = input_colors[idx]

    # Check if the prediction result file exists
    if not os.path.exists(prediction_file):
        print(f"Prediction result file '{prediction_file}' does not exist. Skipping {model_name}.")
        ax.set_visible(False)
        continue

    # Read the prediction results
    data = pd.read_csv(prediction_file)
    in_situ = data['Actual']
    pred = data['Predicted']

    # Calculate performance metrics
    error, bias_val, r2_val, rmse_val = calculate_metrics(in_situ, pred)

    # Create scatter plot
    ax.scatter(in_situ, pred, s=20, c=color, alpha=0.5, edgecolor='none')
    ax.plot([1, 5000], [1, 5000], ls='--', c='k', alpha=0.8)

    # Set log scale for axes
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(1, 5000)
    ax.set_ylim(1, 5000)

    # Add kernel density estimation (KDE)
    lower_bound, upper_bound = 1, 5000  # Set reasonable bounds
    filtered_in_situ = in_situ[(in_situ >= lower_bound) & (in_situ <= upper_bound)]
    filtered_pred = pred[(pred >= lower_bound) & (pred <= upper_bound)]

    sns.kdeplot(x=filtered_in_situ, y=filtered_pred, levels=[0.5, 0.7, 0.9], color='k', linewidths=0.5, zorder=100, ls='--', ax=ax)

    # Add horizontal and vertical grid lines
    for val in [1, 10, 100, 1000]:
        ax.axhline(y=val, linestyle='-', color='gray', alpha=0.5, lw=0.3)
        ax.axvline(x=val, linestyle='-', color='gray', alpha=0.5, lw=0.3)

    # Annotate performance metrics
    ax.text(0.60, 0.06, '$\it{Error}$' + ' = ' + '{}%'.format(round(error, 2)), transform=ax.transAxes, zorder=200)
    ax.text(0.60, 0.20, '$\it{Bias}$' + ' = ' + '{}%'.format(round(bias_val, 2)), transform=ax.transAxes, zorder=200)
    ax.text(0.06, 0.88, '$\it{R²}$' + ' = ' + '{}'.format(round(r2_val, 2)), transform=ax.transAxes, zorder=200)
    ax.text(0.06, 0.74, '$\it{RMSE}$' + ' = ' + '{} mg/L'.format(round(rmse_val, 2)), transform=ax.transAxes,
            zorder=200)

    # Set axis labels and title
    ax.set_xlabel('Actual SSC (mg/L)')
    if idx == 0:
        ax.set_ylabel('Predicted SSC (mg/L)')
    ax.set_title(f'{model_name} Prediction')

# Adjust layout
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# Save the plot
plt.savefig('SSC_Prediction_Comparison_All_Models.png', dpi=300, bbox_inches='tight')

# Display the plot
plt.show()
