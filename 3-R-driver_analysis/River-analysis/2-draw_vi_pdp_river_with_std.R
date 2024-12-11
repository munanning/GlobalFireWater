# Load required libraries
library(DALEXtra)
library(dplyr)
library(ggplot2)
library(tidyr)
library(randomForest)
library(patchwork)
library(scales)

# Custom transformation function
half_scale_trans <- function() {
  trans_new(
    name = "half_scale",
    transform = function(x) ifelse(x > 10, 10 + (x - 10) / 1, x),
    inverse = function(x) ifelse(x > 10, 10 + (x - 10) * 1, x),
    domain = c(0, Inf)
  )
}

# === Step 1: Plot Feature Importance === #
# Load CSV data
importance_data <- read.csv("sorted_feature_importance_river.csv")

# Load mapping information
source("mappings.R")

# Map feature names and categories
importance_data$Feature <- sapply(importance_data$X, function(x) feature_name_mapping[[x]])
importance_data$Category <- sapply(importance_data$Feature, function(x) feature_category_mapping[[x]])

# Normalize standard deviation
importance_data$std_normalized <- importance_data$std / max(importance_data$std)

# Create feature importance plot using ggplot2, adding normalized standard deviation lines
vi_plot <- ggplot(importance_data, aes(x = X.IncMSE, y = reorder(Feature, X.IncMSE, FUN = mean))) +
  geom_bar(aes(fill = Category), color = 'black', stat = "identity", alpha = 0.7, width = 0.8) +
  geom_segment(aes(x = X.IncMSE - std_normalized, xend = X.IncMSE + std_normalized, y = reorder(Feature, X.IncMSE), yend = reorder(Feature, X.IncMSE)),
               color = "black", size = 0.8, alpha = 0.7) +  # Use normalized standard deviation
  scale_x_continuous(expand = c(0, 0), trans = half_scale_trans()) +  # Apply custom transformation
  scale_fill_manual(values = unlist(category_color_mapping), name = "Category") +
  theme_classic() +
  labs(x = "Importance (%IncMSE)", y = "", fill = "Category", title = "Driver Importance For Rivers") +
  theme(
    plot.background = element_rect(fill = "transparent", color = NA),
    legend.position = c(.85, .15),
    text = element_text(),
    axis.title.x = element_text(size = 11),
    axis.text = element_text(size = 10, color = "#000000"),
    axis.text.y = element_text(size = 11, color = "#000000"),
    legend.title = element_text(face = "bold", size = 12),
    legend.text = element_text(size = 11),
    plot.title = element_text(face = "bold", size = 16, hjust = 0.5)
  )

# Print the feature importance plot
print(vi_plot)

# Extract the order of features based on importance
ordered_features <- importance_data %>%
  arrange(desc(X.IncMSE)) %>%  # Sort by X.IncMSE in descending order
  pull(X)  # Extract feature names

# === Step 2: Load the Model === #
load("best_rf_model_river.RData")

# === Step 3: Load Data === #
df <- read.csv('../1-merged_river_precipitation_data.csv')

# Select specific features, excluding 'T'
selected_features <- c('Rainfall', 'duration', 'area', 'slope', 'land_cover',
                       'soil_30', 'clay_30', 'sand_30', 'silt_30', 'wind', 'dnbr',
                       'ndvi', 'max_prec', 'max_7_days_sum', 'first_7_days_sum',
                       'fire_area_per','slope_basin','MIN','MAX','MEAN')

df <- df[, c('change4', selected_features)]  # Retain target variable 'change4' and selected features

df_filtered <- df %>%
  drop_na()  # Remove rows with NA values

# === Step 4: Create an explainer object using DALEXtra's explain_tidymodels === #
explainer_rf <- explain_tidymodels(
  rf_model,  # Use the loaded model object
  data = dplyr::select(df_filtered, -change4),  # Filtered dataset, excluding the target variable
  y = df_filtered$change4,  # Target variable
  label = "random forest"  # Model label
)

# === Step 5: Generate Partial Dependence Data === #
pdp_rf <- model_profile(explainer_rf, N = NULL)

# === Step 6: Plot Partial Dependence Profiles for All Features === #
pdp_plot <- pdp_rf$agr_profiles %>%
  group_by(`_vname_`) %>%
  mutate(
    `_vname_` = factor(`_vname_`, levels = ordered_features),
    # Normalize x-axis
    `_x_` = (`_x_` - min(`_x_`)) / (max(`_x_`) - min(`_x_`)),

    # Normalize y-axis
    `_yhat_` = (`_yhat_` - min(`_yhat_`)) / (max(`_yhat_`) - min(`_yhat_`)),

    # Scale x-axis to avoid exceeding bar chart limits
    `_x_` = case_when(
      `_vname_` %in% c('duration', 'area',
                       'soil_30', 'clay_30', 'sand_30', 'silt_30', 'dnbr',
                       'ndvi', 'max_prec', 'max_7_days_sum', 'first_7_days_sum',
                       'fire_area_per') ~ 1 * `_x_`,
      `_vname_` %in% c("land_cover") ~ 0.7 * `_x_`,
      TRUE ~ `_x_`
    )
  ) %>%
  ungroup() %>%
  ggplot(aes(x = `_x_`, y = `_yhat_`)) +
  geom_line(color = "black", size = .5) +
  facet_wrap(~ `_vname_`, scales = "free_x", ncol = 1) +  # Keep x-axis independent for each feature
  theme_void() +  # Remove background and grid lines
  theme(
    legend.position = "none",
    strip.background = element_blank(),
    strip.text = element_blank(),
    axis.text = element_blank(),
    axis.ticks = element_blank(),
    axis.title = element_blank(),
    panel.spacing.y = unit(0.5, "lines"),  # Adjust spacing between subplots
    plot.margin = unit(c(0, 0, 0, 0), "cm")
  )

# Print the partial dependence plot
print(pdp_plot)

# === Step 7: Overlay PDP on Feature Importance Plot === #
vi_pdp_plot <- vi_plot +
  inset_element(pdp_plot, left = 0.0, bottom = 0.01, right = .38, top = 0.99)

# Print the combined plot
print(vi_pdp_plot)

# Save the combined plot
ggsave("vi_pdp_plot_combined_river_std_100-origin.png", vi_pdp_plot, width = 8, height = 10, dpi = 450, bg = "transparent")
