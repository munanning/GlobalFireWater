import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# 设置随机状态
random_state = 42

# 1. 读取 train_data.csv 和 test_data.csv
train_file = './train_data.csv'
test_file = './test_data.csv'

try:
    train_data = pd.read_csv(train_file)
    test_data = pd.read_csv(test_file)
except FileNotFoundError as e:
    print(f"文件未找到: {e.filename}")
    exit()
except Exception as e:
    print(f"读取文件时出错: {e}")
    exit()

# 2. 分离特征和目标变量 'ssc'
X_train = train_data.drop(columns=['ssc'])
y_train = train_data['ssc']
X_test = test_data.drop(columns=['ssc'])
y_test = test_data['ssc']

# 3. 定义不同的模型及其参数
models = {
    'RandomForest': {
        'model': RandomForestRegressor(
            n_estimators=50,
            max_depth=20,
            min_samples_split=5,
            random_state=random_state
        ),
        'prediction_file': 'RFmodel_prediction_results.csv'
    },
    'XGBoost': {
        'model': XGBRegressor(
            n_estimators=50,
            max_depth=20,
            learning_rate=0.1,
            random_state=random_state,
            verbosity=0
        ),
        'prediction_file': 'XGBoost_model_prediction_results.csv'
    },
    'SVR': {
        'model': SVR(
            kernel='rbf',
            C=100,
            epsilon=0.1
        ),
        'prediction_file': 'SVR_model_prediction_results.csv'
    },
    'DNN': {
        'model': MLPRegressor(
            hidden_layer_sizes=(100, 100),
            activation='relu',
            solver='adam',
            max_iter=500,
            random_state=random_state
        ),
        'prediction_file': 'DNN_model_prediction_results.csv'
    }
}

# 8. 读取现有的性能指标 CSV 文件
performance_file = 'model_performance.csv'
try:
    performance_df = pd.read_csv(performance_file)
except FileNotFoundError:
    # 如果文件不存在，创建一个新的 DataFrame
    performance_df = pd.DataFrame(columns=['Model', 'MAE', 'MSE', 'R2'])
except Exception as e:
    print(f"读取性能指标文件时出错: {e}")
    exit()

# 4. 迭代每个模型进行训练、预测和保存
for model_name, config in models.items():
    print(f"\n正在处理模型: {model_name}")
    model = config['model']

    # 训练模型
    model.fit(X_train, y_train)

    # 预测
    y_pred = model.predict(X_test)

    # 计算性能指标
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f'{model_name} - Mean Absolute Error (MAE): {mae}')
    print(f'{model_name} - Mean Squared Error (MSE): {mse}')
    print(f'{model_name} - R-squared (R²): {r2}')

    # 6. 保存预测结果到 CSV
    results = pd.DataFrame({'Actual': y_test, 'Predicted': y_pred})
    prediction_file = config['prediction_file']
    results.to_csv(prediction_file, index=False)
    print(f"预测结果已保存到 '{prediction_file}'")

    # 7. 保存模型，文件名包含 R² 值
    if model_name == 'RandomForest':
        model_filename = f'RandomForest_model_R2_{r2:.2f}.joblib'
    elif model_name == 'XGBoost':
        model_filename = f'XGBoost_model_R2_{r2:.2f}.joblib'
    elif model_name == 'SVR':
        model_filename = f'SVR_model_R2_{r2:.2f}.joblib'
    elif model_name == 'DNN':
        model_filename = f'DNN_model_R2_{r2:.2f}.joblib'
    else:
        model_filename = f'{model_name}_model_R2_{r2:.2f}.joblib'

    joblib.dump(model, model_filename)
    print(f"模型已保存为 '{model_filename}'")

    # 9. 更新或添加模型性能指标
    model_identifier = f'{model_name}_random_state_{random_state}'
    if model_identifier in performance_df['Model'].values:
        # 如果模型已存在，更新其性能指标
        performance_df.loc[performance_df['Model'] == model_identifier, ['MAE', 'MSE', 'R2']] = [mae, mse, r2]
    else:
        # 如果模型不存在，添加新的行
        new_row = pd.DataFrame({
            'Model': [model_identifier],
            'MAE': [mae],
            'MSE': [mse],
            'R2': [r2]
        })
        performance_df = pd.concat([performance_df, new_row], ignore_index=True)

# 10. 保存更新后的性能指标到 CSV
performance_df.to_csv(performance_file, index=False)
print(f"\n所有模型的性能已更新保存到 '{performance_file}'")
