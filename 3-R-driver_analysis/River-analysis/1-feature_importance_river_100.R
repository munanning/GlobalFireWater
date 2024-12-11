# 安装并加载必要的包
if(!require(randomForest)) install.packages('randomForest', dependencies=TRUE)
library(randomForest)

if(!require(progress)) install.packages('progress', dependencies=TRUE)
library(progress)

# 读取数据
df <- read.csv('../1-merged_river_precipitation_data.csv')

# 筛选指定的特征，删除 'T'
selected_features <- c('Rainfall', 'duration', 'area', 'slope', 'land_cover', 
                       'soil_30', 'clay_30', 'sand_30', 'silt_30', 'wind', 'dnbr', 
                       'ndvi', 'max_prec', 'max_7_days_sum', 'first_7_days_sum',
                       'fire_area_per','slope_basin','MIN','MAX','MEAN')

df <- df[, c('change4', selected_features)]  # 保留目标变量change4和所有特征

# 提取目标变量和特征
target <- df$change4  # change4 作为目标变量
features <- df[, selected_features]  # 剩余的列作为特征

# 初始化存储变量
num_runs <- 100
feature_names <- selected_features  # 特征名称
incmse_matrix <- matrix(NA, nrow=length(feature_names), ncol=num_runs)
rownames(incmse_matrix) <- feature_names
colnames(incmse_matrix) <- paste0("Run", 1:num_runs)

# 初始化最佳模型相关变量
best_oob_mse <- Inf  # 初始化为正无穷大
best_run <- NA  # 最佳运行的索引

# 设置初始随机种子
initial_seed <- 123

# 创建进度条
pb <- progress_bar$new(
  format = "  运行进度 [:bar] :percent 完成，当前运行：:current/:total，预计剩余时间：:eta",
  total = num_runs, clear = FALSE, width=60
)

# 循环运行随机森林模型
for (i in 1:num_runs) {
  # 更新进度条
  pb$tick()
  
  # 设置不同的随机种子
  set.seed(initial_seed + i)
  
  # 构建随机森林模型
  rf_model <- randomForest(features, target, importance=TRUE, ntree=500)
  
  # 记录 %IncMSE
  incmse <- importance(rf_model, type=1)[, "%IncMSE"]
  incmse_matrix[, i] <- incmse
  
  # 获取当前运行的 OOB MSE（最后一个 MSE 值）
  current_oob_mse <- tail(rf_model$mse, n=1)
  
  # 检查是否为当前最佳模型
  if (current_oob_mse < best_oob_mse) {
    best_oob_mse <- current_oob_mse
    best_run <- i
    # 保存当前最佳模型，覆盖之前的最佳模型
    save(rf_model, file = "best_rf_model_river.RData")
  }
  
  # 清理当前模型以释放内存
  rm(rf_model)
  gc()  # 垃圾回收，释放内存
}

# 计算每个特征的中位数和标准差
median_incMSE <- apply(incmse_matrix, 1, median, na.rm=TRUE)
std_incMSE <- apply(incmse_matrix, 1, sd, na.rm=TRUE)

# 创建结果数据框
result_df <- data.frame(
  X = names(median_incMSE),
  X.IncMSE = median_incMSE,
  std = std_incMSE,
  stringsAsFactors = FALSE
)

# 按 X.IncMSE 降序排序
result_df <- result_df[order(-result_df$X.IncMSE), ]

# 保存结果为 CSV 文件，列名为 "X","X.IncMSE","std"
write.csv(result_df, 'sorted_feature_importance_river.csv', row.names=FALSE)

# 输出相关信息
cat("中位数和标准差的 %IncMSE 已保存到 'sorted_feature_importance_river.csv'\n")
cat(paste("OOB MSE 最小的模型（Run", best_run, "）已保存为 'best_rf_model_river.RData'\n"))
