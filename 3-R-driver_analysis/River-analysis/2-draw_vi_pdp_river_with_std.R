# 加载必要的包
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


# === 第一步：绘制特征重要性图 === #
# 加载csv数据
importance_data <- read.csv("sorted_feature_importance_river.csv")

# 加载mapping信息
source("mappings.R")

# 映射feature的名称和类别
importance_data$Feature <- sapply(importance_data$X, function(x) feature_name_mapping[[x]])
importance_data$Category <- sapply(importance_data$Feature, function(x) feature_category_mapping[[x]])

# 归一化标准差
importance_data$std_normalized <- importance_data$std / max(importance_data$std) * 3  # 调整这个乘数以控制标准差线的最大长度

# 拉伸变换，使得变量差别更明显，但不对 'max_prec' 和 'max_7_days_sum' 生效
stretch_factor <- 3
exclude_features <- c('max_prec', 'max_7_days_sum')

# 对需要拉伸的行执行变换
importance_data$X.IncMSE <- ifelse(
  importance_data$X %in% exclude_features,
  importance_data$X.IncMSE, # 保持原始值
  (importance_data$X.IncMSE - min(importance_data$X.IncMSE)) * stretch_factor + min(importance_data$X.IncMSE)
)

# 对非排除的行进一步缩放
importance_data$X.IncMSE <- ifelse(
  importance_data$X %in% exclude_features,
  importance_data$X.IncMSE, # 保持原始值
  importance_data$X.IncMSE / 2
)

# 使用 ggplot2 绘制特征重要性图，添加归一化后的标准差横线
vi_plot <- ggplot(importance_data, aes(x = X.IncMSE, y = reorder(Feature, X.IncMSE, FUN = mean))) +
  geom_bar(aes(fill = Category), color = 'black', stat = "identity", alpha = 0.7, width = 0.8) +
  geom_segment(aes(x = X.IncMSE - std_normalized, xend = X.IncMSE + std_normalized, y = reorder(Feature, X.IncMSE), yend = reorder(Feature, X.IncMSE)),
               color = "black", size = 0.8, alpha = 0.7) +  # 使用归一化的标准差
  scale_x_continuous(expand = c(0, 0), trans = half_scale_trans()) +  # Apply the custom transformation
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


# 打印特征重要性图
print(vi_plot)

# 获取按重要性排序的特征顺序
ordered_features <- importance_data %>%
  arrange(desc(X.IncMSE)) %>%  # 按 X.IncMSE 降序排列
  pull(X)  # 提取特征名称的顺序

# === 第二步：加载模型 === #
load("best_rf_model_river.RData")

# === 第三步：加载数据 === #
df <- read.csv('../1-merged_river_precipitation_data.csv')

# 筛选指定的特征，删除 'T'
selected_features <- c('Rainfall', 'duration', 'area', 'slope', 'land_cover', 
                       'soil_30', 'clay_30', 'sand_30', 'silt_30', 'wind', 'dnbr', 
                       'ndvi', 'max_prec', 'max_7_days_sum', 'first_7_days_sum',
                       'fire_area_per','slope_basin','MIN','MAX','MEAN')

df <- df[, c('change4', selected_features)]  # 保留目标变量change4和所有特征

# 排除极端值，只保留中间95%的数据
df_filtered <- df %>%
  drop_na()  # 移除包含NA值的行

# === 第四步：使用 DALEXtra 的 explain_tidymodels 创建一个 explainer 对象 === #
explainer_rf <- explain_tidymodels(
  rf_model,  # 这里使用加载的模型对象
  data = dplyr::select(df_filtered, -change4),  # 过滤后的数据集，去除目标变量
  y = df_filtered$change4,  # 目标变量
  label = "random forest"  # 模型的标签名称
)

# === 第五步：生成部分依赖数据 === #
pdp_rf <- model_profile(explainer_rf, N = NULL)

# === 第六步：绘制所有特征的部分依赖图 === #
pdp_plot <- pdp_rf$agr_profiles %>%
  group_by(`_vname_`) %>%  # 对每个特征单独进行归一化
  mutate(
    `_vname_` = factor(`_vname_`, levels = ordered_features),

    # 对 wind 和 slope 特征应用不同的阈值，去掉 x < 阈值 的部分并设置 yhat 为 NA
    `_x_` = case_when(
      `_vname_` == "wind" & `_x_` < 1.2 ~ NA_real_,
      `_vname_` == "slope" & `_x_` < 0.5 ~ NA_real_,
      `_vname_` == "Rainfall" & `_x_` < 100 ~ NA_real_,
      TRUE ~ `_x_`
    ),
    `_x_` = ifelse(`_vname_` %in% c("dnbr"), -`_x_`, `_x_`),  # 对dnbr变量的x值取相反数

    `_yhat_` = ifelse(`_vname_` %in% c("wind", "slope", "Rainfall") & is.na(`_x_`), NA, `_yhat_`),  # 对应的 yhat 也设为 NA

    # 对 wind 和 slope 特征的 x 重新归一化，其他特征保持原样
    `_x_` = ifelse(`_vname_` %in% c("wind", "slope", "Rainfall"),
                   (`_x_` - min(`_x_`, na.rm = TRUE)) / (max(`_x_`, na.rm = TRUE) - min(`_x_`, na.rm = TRUE)),
                   (`_x_` - min(`_x_`)) / (max(`_x_`) - min(`_x_`))),

    # 对 wind 和 slope 特征的 yhat 重新归一化，其他特征保持原样
    `_yhat_` = ifelse(`_vname_` %in% c("wind", "slope", "Rainfall"),
                      (`_yhat_` - min(`_yhat_`, na.rm = TRUE)) / (max(`_yhat_`, na.rm = TRUE) - min(`_yhat_`, na.rm = TRUE)),
                      (`_yhat_` - min(`_yhat_`)) / (max(`_yhat_`) - min(`_yhat_`)))
  ) %>%
  ungroup() %>%
  ggplot(aes(x = `_x_`, y = `_yhat_`)) +
  geom_line(color = "black", size = .5) +
  facet_wrap(~ `_vname_`, scales = "free_x", ncol = 1) +  # 保持每个特征的 x 轴独立
  theme_void() +  # 清除背景和网格线
  theme(
    legend.position = "none",
    strip.background = element_blank(),
    strip.text = element_blank(),
    axis.text = element_blank(),
    axis.ticks = element_blank(),
    axis.title = element_blank(),
    panel.spacing.y = unit(0.5, "lines"),  # 调整子图之间的间距
    plot.margin = unit(c(0, 0, 0, 0), "cm")
  )

# 打印部分依赖图
print(pdp_plot)

# === 第七步：将PDP叠加到特征重要性图上 === #
vi_pdp_plot <- vi_plot + 
  inset_element(pdp_plot, left = 0.0, bottom = 0.01, right = .38, top = 0.99)

# 打印合成图
print(vi_pdp_plot)

# 保存合成图
ggsave("vi_pdp_plot_combined_river_std_100.png", vi_pdp_plot, width = 8, height = 10, dpi = 450, bg = "transparent")

