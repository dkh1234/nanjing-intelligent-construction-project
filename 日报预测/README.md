# 建筑工程项目工期预测系统

基于甘特图任务数据和日报执行数据，按周预测项目进度，最终输出预计完工日期。

## 项目结构

```
日报预测/
├── data/
│   ├── gantt/                  # 原始甘特图xlsx（5个项目）
│   ├── daily/                  # 原始日报txt（2个项目，按项目ID分目录）
│   └── processed/              # 处理后的中间数据
├── src/
│   ├── process_gantt.py        # 甘特图→任务表→周级训练集
│   ├── process_daily.py        # 日报→解析→周级特征聚合
│   ├── train_model.py          # 模型训练（主数据=甘特图，补充特征=日报）
│   └── utils.py                # 工具函数
├── models/                     # 训练好的模型文件
├── main.py                     # 一键运行全流程
└── requirements.txt
```

## 数据流

```
5个甘特图xlsx ──→ process_gantt.py ──→ unified_tasks.csv ──→ weekly_gantt.csv ──┐
                                                                                 ├──→ train_model.py ──→ 模型 + 预测结果
2个日报txt ────→ process_daily.py ──→ weekly_daily.csv ────────────────────────┘
```

## 核心设计

- **标签来源**：甘特图的任务权重完成率（唯一真实进度数据）
- **日报角色**：提供天气/人力/机械等"执行强度"特征（无标签）
- **粒度**：按周聚合，平衡信号稳定性与数据量
- **验证**：GroupKFold Leave-One-Project-Out，5折
- **预测**：逐周滚动预测进度增量 → 累计进度达100%时的周数 = 预测工期
