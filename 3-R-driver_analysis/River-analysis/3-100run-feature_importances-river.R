# 安装并加载必要的包
if(!require(randomForest)) install.packages('randomForest', dependencies=TRUE)
library(randomForest)

if(!require(progress)) install.packages('progress', dependencies=TRUE)
library(progress)

# 读取数据
df <- read.csv('../1-merged_lake_precipitation_data.csv')

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

# 设置初始随机种子
initial_seed <- 123

# 创建文件夹，如果不存在
if (!dir.exists("100runs_lake")) {
  dir.create("100runs_lake")
}

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
  
  # 创建结果数据框并按 %IncMSE 降序排列
  result_df <- data.frame(
    Feature = feature_names,
    IncMSE = incmse,
    stringsAsFactors = FALSE
  )
  result_df <- result_df[order(-result_df$IncMSE), ]
  
  # 保存每次运行的结果为 CSV 文件
  output_filename <- paste0("100runs_lake/Run_", i, "_IncMSE.csv")
  write.csv(result_df, output_filename, row.names=FALSE)
  
  # 清理当前模型以释放内存
  rm(rf_model)
  gc()  # 垃圾回收，释放内存
}

cat("每次运行的结果已保存到 '100runs_lake' 文件夹中，每个文件名包含对应的序号。\n")
