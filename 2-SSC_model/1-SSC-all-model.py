import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

# Set random state
random_state = 42

# 1. Read train_data.csv and test_data.csv
train_file = './train_data.csv'
test_file = './test_data.csv'

try:
    train_data = pd.read_csv(train_file)
    test_data = pd.read_csv(test_file)
except FileNotFoundError as e:
    print(f"File not found: {e.filename}")
    exit()
except Exception as e:
    print(f"Error reading file: {e}")
    exit()

# 2. Separate features and target variable 'ssc'
X_train = train_data.drop(columns=['ssc'])
y_train = train_data['ssc']
X_test = test_data.drop(columns=['ssc'])
y_test = test_data['ssc']

# 3. Define different models and their parameters
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

# 8. Read the existing performance metrics CSV file
performance_file = 'model_performance.csv'
try:
    performance_df = pd.read_csv(performance_file)
except FileNotFoundError:
    # If the file does not exist, create a new DataFrame
    performance_df = pd.DataFrame(columns=['Model', 'MAE', 'MSE', 'R2'])
except Exception as e:
    print(f"Error reading performance file: {e}")
    exit()

# 4. Iterate through each model for training, prediction, and saving
for model_name, config in models.items():
    print(f"\nProcessing model: {model_name}")
    model = config['model']

    # Train the model
    model.fit(X_train, y_train)

    # Make predictions
    y_pred = model.predict(X_test)

    # Calculate performance metrics
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f'{model_name} - Mean Absolute Error (MAE): {mae}')
    print(f'{model_name} - Mean Squared Error (MSE): {mse}')
    print(f'{model_name} - R-squared (R²): {r2}')

    # 6. Save prediction results to a CSV file
    results = pd.DataFrame({'Actual': y_test, 'Predicted': y_pred})
    prediction_file = config['prediction_file']
    results.to_csv(prediction_file, index=False)
    print(f"Prediction results saved to '{prediction_file}'")

    # 7. Save the model with a filename that includes the R² value
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
    print(f"Model saved as '{model_filename}'")

    # 9. Update or add model performance metrics
    model_identifier = f'{model_name}_random_state_{random_state}'
    if model_identifier in performance_df['Model'].values:
        # If the model already exists, update its performance metrics
        performance_df.loc[performance_df['Model'] == model_identifier, ['MAE', 'MSE', 'R2']] = [mae, mse, r2]
    else:
        # If the model does not exist, add a new row
        new_row = pd.DataFrame({
            'Model': [model_identifier],
            'MAE': [mae],
            'MSE': [mse],
            'R2': [r2]
        })
        performance_df = pd.concat([performance_df, new_row], ignore_index=True)

# 10. Save the updated performance metrics to a CSV file
performance_df.to_csv(performance_file, index=False)
print(f"\nAll model performance metrics have been updated and saved to '{performance_file}'")
