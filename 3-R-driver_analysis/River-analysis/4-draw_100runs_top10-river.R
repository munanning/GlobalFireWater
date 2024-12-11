# 安装并加载必要的包
if(!require(ggplot2)) install.packages('ggplot2', dependencies=TRUE)
library(ggplot2)

# 设置文件夹路径
folder_path <- "100runs_river"

# 设置感兴趣的特征
target_features <- c('Rainfall', 'slope', 'MEAN', 'fire_area_per')

# 初始化一个数据框来存储每个特征的出现次数
feature_counts <- data.frame(
  Feature = target_features,
  Count = rep(0, length(target_features)),  # 初始出现次数为0
  stringsAsFactors = FALSE
)

# 获取文件夹内所有的csv文件
csv_files <- list.files(folder_path, pattern = "^Run_\\d+_IncMSE.csv$", full.names = TRUE)

# 循环读取每个 CSV 文件
for (file in csv_files) {
  # 读取当前 CSV 文件
  result_df <- read.csv(file)
  
  # 获取前11行，并统计感兴趣特征的出现次数
  top_features <- result_df$Feature[1:11]
  
  # 对于每个特征，检查它是否出现在前11行中
  for (i in 1:length(target_features)) {
    feature <- target_features[i]
    if (feature %in% top_features) {
      feature_counts$Count[i] <- feature_counts$Count[i] + 1  # 如果出现在前11行，计数+1
    }
  }
}

# 计算每个特征出现的比例
feature_counts$Proportion <- feature_counts$Count / length(csv_files)

# 加载映射信息
source("mappings.R")  # 加载 mappings.R 中的所有映射

# 映射feature的名称和类别
feature_counts$Feature <- sapply(feature_counts$Feature, function(x) feature_name_mapping[[x]])
feature_counts$Category <- sapply(feature_counts$Feature, function(x) feature_category_mapping[[x]])

# 使用 ggplot2 绘制柱状图
vi_plot <- ggplot(feature_counts, aes(x = Proportion, y = reorder(Feature, Proportion), fill = Category)) +
  scale_x_continuous(expand = c(0, 0)) +  # Apply the custom transformation
  geom_bar(stat = "identity", color = 'black', width = 0.8, alpha = 0.7) +
  scale_fill_manual(values = unlist(category_color_mapping)) +  # 使用颜色映射
  labs(x = "Proportion", y = NULL, title = "Frequency in Top 10 Importance for Rivers") +
  theme_classic() +  # 使用经典主题，自动去除网格线
  theme(
    axis.text.x = element_text(size = 11, color = "#000000"),
    axis.text.y = element_text(size = 11, color = "#000000"),
    legend.position = "none",  # 不显示图例
    plot.title = element_text(face = "bold", size = 16, hjust = 0.5),
    axis.title.x = element_text(size = 11),
    plot.background = element_rect(fill = "transparent", color = NA),
    plot.margin = margin(10, 10, 10, 10)           # 增加右侧的margin
  )

# 打印图表
print(vi_plot)

ggsave("feature_importance_frequency_River.png", plot = vi_plot, width = 7, height = 4, dpi = 300)

