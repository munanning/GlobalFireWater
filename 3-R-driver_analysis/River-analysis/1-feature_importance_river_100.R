# Install and load necessary packages
if(!require(randomForest)) install.packages('randomForest', dependencies=TRUE)
library(randomForest)

if(!require(progress)) install.packages('progress', dependencies=TRUE)
library(progress)

# Load data
df <- read.csv('../1-merged_river_precipitation_data.csv')

# Select specific features, excluding 'T'
selected_features <- c('Rainfall', 'duration', 'area', 'slope', 'land_cover',
                       'soil_30', 'clay_30', 'sand_30', 'silt_30', 'wind', 'dnbr',
                       'ndvi', 'max_prec', 'max_7_days_sum', 'first_7_days_sum',
                       'fire_area_per','slope_basin','MIN','MAX','MEAN')

df <- df[, c('change4', selected_features)]  # Retain target variable 'change4' and selected features

# Extract target variable and features
target <- df$change4  # Use 'change4' as the target variable
features <- df[, selected_features]  # Use remaining columns as features

# Initialize storage variables
num_runs <- 100
feature_names <- selected_features  # Feature names
incmse_matrix <- matrix(NA, nrow=length(feature_names), ncol=num_runs)
rownames(incmse_matrix) <- feature_names
colnames(incmse_matrix) <- paste0("Run", 1:num_runs)

# Initialize variables for the best model
best_oob_mse <- Inf  # Set to positive infinity initially
best_run <- NA  # Index of the best run

# Set initial random seed
initial_seed <- 123

# Create progress bar
pb <- progress_bar$new(
  format = "  Progress [:bar] :percent completed, current run: :current/:total, estimated time left: :eta",
  total = num_runs, clear = FALSE, width=60
)

# Loop to train Random Forest models
for (i in 1:num_runs) {
  # Update progress bar
  pb$tick()

  # Set different random seeds
  set.seed(initial_seed + i)

  # Train the Random Forest model
  rf_model <- randomForest(features, target, importance=TRUE, ntree=500)

  # Record %IncMSE
  incmse <- importance(rf_model, type=1)[, "%IncMSE"]
  incmse_matrix[, i] <- incmse

  # Get the OOB MSE of the current run (last MSE value)
  current_oob_mse <- tail(rf_model$mse, n=1)

  # Check if this is the best model so far
  if (current_oob_mse < best_oob_mse) {
    best_oob_mse <- current_oob_mse
    best_run <- i
    # Save the current best model, overwriting the previous one
    save(rf_model, file = "best_rf_model_river.RData")
  }

  # Clean up the current model to free memory
  rm(rf_model)
  gc()  # Garbage collection to free memory
}

# Calculate median and standard deviation for each feature
median_incMSE <- apply(incmse_matrix, 1, median, na.rm=TRUE)
std_incMSE <- apply(incmse_matrix, 1, sd, na.rm=TRUE)

# Create a result data frame
result_df <- data.frame(
  X = names(median_incMSE),
  X.IncMSE = median_incMSE,
  std = std_incMSE,
  stringsAsFactors = FALSE
)

# Sort by X.IncMSE in descending order
result_df <- result_df[order(-result_df$X.IncMSE), ]

# Save results to a CSV file with column names "X", "X.IncMSE", "std"
write.csv(result_df, 'sorted_feature_importance_river.csv', row.names=FALSE)

# Output relevant information
cat("Median and standard deviation of %IncMSE have been saved to 'sorted_feature_importance_river.csv'\n")
cat(paste("The model with the lowest OOB MSE (Run", best_run, ") has been saved as 'best_rf_model_river.RData'\n"))
