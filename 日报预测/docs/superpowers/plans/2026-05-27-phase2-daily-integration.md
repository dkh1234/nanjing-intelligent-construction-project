# 工期预测系统 Phase 2: 日报数据利用与模型改进 实施计划

> **For implementation:** Execute tasks in order. Steps use checkbox (`- [ ]`) syntax for tracking. Task 1-3 are diagnostics (read-only), Task 4-6 are implementation. Checkpoints at Task 3, 4, and 6.

**Goal:** 将2个日报项目（P001/P003）的天气/人力/机械特征纳入模型，使训练数据从5项目扩展到7项目，同时改进模型泛化能力。

**Architecture:** 分两个阶段推进。第一阶段（Task 1-3）纯诊断，不改模型——跑分析脚本、看数据、确认日报数据质量。第二阶段（Task 4-6）根据诊断结果选择路线：如果日报施工条目可追踪则构造伪标签联合训练，如果不行则日报仅做特征增强。每阶段结束有明确的决策检查点。

**Tech Stack:** Python 3, pandas, scikit-learn, XGBoost, openpyxl（已在 requirements.txt 中）

---

## 当前状态速查

| 文件 | 内容 | 关键字段 |
|------|------|----------|
| `data/processed/weekly_gantt.csv` | 5项目×501周，有标签 | active_tasks, delay_ratio, completed_this_week, ... |
| `data/processed/weekly_daily.csv` | 2项目×107周，无标签 | rain_days, avg_workers, avg_excavator, avg_items_per_day, ... |
| `data/processed/unified_tasks.csv` | 3520个甘特图叶子任务 | actual_start, actual_end, weight_norm, completion_pct |
| `models/weekly_xgboost_*.pkl` | 当前最佳模型 | CV MAE=0.0076, 工期误差±23周 |

**两表特征交集**（可直接对齐的列）：`project_code, week_start, week_end, week_num, month`

**甘特图独有**：`active_tasks, new_starts, overdue_tasks, delay_ratio_to_date, total_remaining_work, avg_task_dur, completed_this_week, cumulative_progress, weekly_progress`

**日报独有**：`n_days, rain_days, extreme_days, avg_temp, avg_workers, max_workers, sub_count, avg_excavator, avg_crane, avg_loader, avg_mobile_crane, total_equip, avg_items_per_day, total_items_week, cat_土建, cat_钢结构, cat_设备安装, cat_装修`

---

### Task 1: 日报数据质量审查

**Files:**
- Create: `src/inspect_daily.py`（一次性诊断脚本）

**Purpose:** 在决定怎么用日报之前，先搞清楚日报里到底有什么、质量如何。

- [ ] **Step 1: 写日报诊断脚本**

```python
# src/inspect_daily.py
"""日报数据质量诊断 —— 一次性分析脚本"""
import pandas as pd
import numpy as np

DAILY_PATH = r"D:\日报预测\data\processed\weekly_daily.csv"
GANTT_PATH = r"D:\日报预测\data\processed\weekly_gantt.csv"

daily = pd.read_csv(DAILY_PATH, encoding="utf-8-sig")
gantt = pd.read_csv(GANTT_PATH, encoding="utf-8-sig")

print("=" * 60)
print("日报周级数据质量报告")
print("=" * 60)

# 1. 基本统计
for proj in daily["project_code"].unique():
    p = daily[daily["project_code"] == proj]
    print(f"\n--- {proj}: {len(p)}周 ---")
    print(f"  日期: {p['week_start'].min()} ~ {p['week_start'].max()}")
    print(f"  每周天数: mean={p['n_days'].mean():.1f} (理想=7)")
    print(f"  降雨: {p['rain_days'].sum()}天, 降雨周比例={(p['rain_days']>0).mean():.1%}")
    print(f"  极端天气: {p['extreme_days'].sum()}天")
    print(f"  均温: {p['avg_temp'].mean():.1f}°C (min={p['avg_temp'].min():.0f}, max={p['avg_temp'].max():.0f})")
    print(f"  均人数: {p['avg_workers'].mean():.0f}人 (min={p['avg_workers'].min():.0f}, max={p['avg_workers'].max():.0f})")
    print(f"  零工人周: {(p['avg_workers'] == 0).sum()}")

# 2. 缺失值检查
print("\n--- 缺失值 ---")
for col in daily.columns:
    na = daily[col].isna().sum()
    if na > 0:
        print(f"  {col}: {na}/{len(daily)} ({na/len(daily):.1%})")

# 3. 施工活动多样性
print("\n--- 施工活动分布 ---")
cat_cols = [c for c in daily.columns if c.startswith("cat_")]
for col in cat_cols:
    nonzero = (daily[col] > 0).sum()
    print(f"  {col}: {nonzero}/{len(daily)}周有活动 ({nonzero/len(daily):.1%})")

# 4. 人员-机械相关性（日报内部验证）
print("\n--- 日报内部相关性 ---")
corr_cols = ["avg_workers", "avg_excavator", "avg_crane", "avg_items_per_day", "rain_days"]
corr = daily[corr_cols].corr()
print(corr.round(3))

# 5. 甘特图 vs 日报 数值范围对比
print("\n--- 甘特图 vs 日报 数值范围 ---")
print(f"  甘特图 active_tasks: {gantt['active_tasks'].mean():.0f} (范围 {gantt['active_tasks'].min():.0f}-{gantt['active_tasks'].max():.0f})")
print(f"  日报 avg_items_per_day: {daily['avg_items_per_day'].mean():.1f} (范围 {daily['avg_items_per_day'].min():.1f}-{daily['avg_items_per_day'].max():.1f})")
print(f"  日报 total_items_week: {daily['total_items_week'].mean():.1f}")
print(f"  甘特图 completed_this_week: {gantt['completed_this_week'].mean():.1f}")

print("\n" + "=" * 60)
print("报告结束。关键问题：")
print("1. 日报每周天数是否接近7？（日报应有连续记录）")
print("2. 天气/人力/机械数值是否合理范围？")
print("3. 施工活动覆盖面是否足够？")
print("4. 甘特图和日报的活跃度量级是否可比？")
print("=" * 60)
```

- [ ] **Step 2: 运行诊断**

```bash
cd D:/日报预测 && python src/inspect_daily.py
```

- [ ] **Step 3: 记录发现**

将输出保存为 `docs/daily_data_report.txt`，标记任何异常值（零工人周过多、缺失值占比>10%、施工活动全为0等）。

```bash
cd D:/日报预测 && python src/inspect_daily.py > docs/daily_data_report.txt
```

- [ ] **Step 4: 提交**

```bash
cd D:/日报预测 && git add src/inspect_daily.py docs/daily_data_report.txt && git commit -m "diagnostic: daily data quality report for P001/P003"
```

**检查点:** 审阅报告后决定：日报质量是否足够好？如果有>20%的周关键字段缺失或异常，需要先修 `process_daily.py` 的解析逻辑。

---

### Task 2: 甘特图模型逐项目误差分析

**Files:**
- Create: `src/analyze_errors.py`（一次性诊断脚本）

**Purpose:** 理解当前模型在哪类项目上表现好、哪类差，为改进提供方向。

- [ ] **Step 1: 写误差分析脚本**

```python
# src/analyze_errors.py
"""逐项目/逐周误差分析"""
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error
import sys
sys.path.insert(0, "src")
from train_model import build_features, GANTT_FEATURES

GANTT_PATH = r"D:\日报预测\data\processed\weekly_gantt.csv"

df = pd.read_csv(GANTT_PATH, encoding="utf-8-sig")
df["week_start"] = pd.to_datetime(df["week_start"])
df = build_features(df)

# 用已训练模型做预测（如果有保存的话）
# 这里只做描述性分析，不依赖模型

print("=" * 60)
print("甘特图项目特征分布分析")
print("=" * 60)

# 1. 每个项目的进度曲线形态
for proj, grp in df.groupby("project_code"):
    p = grp.sort_values("week_num")
    print(f"\n--- {proj}: {len(p)}周 ---")
    print(f"  周均进度: {p['weekly_progress'].mean():.4f}")
    print(f"  进度标准差: {p['weekly_progress'].std():.4f}")
    print(f"  零进度周: {(p['weekly_progress']==0).sum()} ({(p['weekly_progress']==0).mean():.1%})")
    print(f"  最大单周: {p['weekly_progress'].max():.4f} (第{p['weekly_progress'].idxmax()-p.index[0]+1}周)")
    print(f"  active_tasks均值: {p['active_tasks'].mean():.1f}")
    print(f"  前10周均值 vs 后10周均值: "
          f"{p['weekly_progress'].head(10).mean():.4f} vs {p['weekly_progress'].tail(10).mean():.4f}")
    # S曲线形态：累计进度达25%/50%/75%时的周数
    c = p["cumulative_progress"]
    for pct in [0.25, 0.50, 0.75]:
        if c.max() >= pct:
            week_at = p[c >= pct]["week_num"].min()
            print(f"  达{pct:.0%}进度: 第{week_at}周 ({week_at/len(p):.1%}位置)")

# 2. 项目间特征差异
print("\n--- 项目间特征变异系数 ---")
feat_cols = [c for c in GANTT_FEATURES if c in df.columns]
for col in feat_cols:
    proj_means = df.groupby("project_code")[col].mean()
    cv = proj_means.std() / (proj_means.mean() + 1e-8)
    if abs(cv) > 0.5:  # 高变异特征
        print(f"  {col}: CV={cv:.2f} (各项目均值: {proj_means.round(3).to_dict()})")

# 3. 项目间相似度
print("\n--- 项目间特征欧氏距离 ---")
from sklearn.preprocessing import StandardScaler
feat_data = df[feat_cols].fillna(0)
scaler = StandardScaler().fit(feat_data)
scaled = scaler.transform(feat_data)
proj_ids = df["project_code"].values
for proj_a in df["project_code"].unique():
    mask_a = proj_ids == proj_a
    centroid_a = scaled[mask_a].mean(axis=0)
    distances = []
    for proj_b in df["project_code"].unique():
        if proj_a >= proj_b:
            continue
        mask_b = proj_ids == proj_b
        centroid_b = scaled[mask_b].mean(axis=0)
        dist = np.linalg.norm(centroid_a - centroid_b)
        distances.append((proj_a, proj_b, dist))
    for a, b, d in sorted(distances, key=lambda x: x[2]):
        print(f"  {a} <-> {b}: {d:.2f}")

print("\n" + "=" * 60)
print("报告结束。关键问题：")
print("1. 哪个项目的进度模式最特殊？（可能是最难预测的）")
print("2. 哪些特征在项目间变异最大？（可能是项目特有而非通用的）")
print("3. 哪些项目对最相似？（合并训练可能效果好）")
print("=" * 60)
```

- [ ] **Step 2: 运行分析**

```bash
cd D:/日报预测 && python src/analyze_errors.py
```

- [ ] **Step 3: 记录发现**

```bash
cd D:/日报预测 && python src/analyze_errors.py > docs/gantt_analysis.txt
```

- [ ] **Step 4: 提交**

```bash
cd D:/日报预测 && git add src/analyze_errors.py docs/gantt_analysis.txt && git commit -m "diagnostic: per-project error and feature analysis"
```

**检查点:** 审阅后决定：是否有明显异常的项目需要单独建模？是否有项目间特征差异大到建议分组建模（如水泥厂 vs 矿山）？

---

### Task 3: 日报施工活动可追踪性验证

**Files:**
- Create: `src/track_activities.py`（一次性分析脚本）

**Purpose:** 日报的 `cat_土建`/`cat_钢结构` 等字段能否像甘特图任务一样追踪"首次出现→最后出现"的时间线？这是决定能否构造伪标签的关键。

- [ ] **Step 1: 写活动追踪脚本**

```python
# src/track_activities.py
"""验证日报施工活动是否可追踪——能否从中提取伪进度标签"""
import os
import re
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import timedelta

RAW_DIR = r"D:\日报\清洗数据\dataClean\data\raw"
CAT_KEYWORDS = {
    "土建":    ["开挖", "回填", "浇筑", "混凝土", "砼", "钢筋", "模板", "抹灰", "砌筑",
                "基槽", "基坑", "桩基", "桩头", "承台", "地面", "道路", "碾压", "土方"],
    "钢结构":  ["钢结构", "钢构", "钢梁", "钢柱", "预埋件", "焊接", "牛腿", "框柱", "彩板", "屋面板"],
    "设备安装": ["安装", "设备", "管道", "风管", "电缆", "桥架", "配电", "机械", "调试"],
    "装修":    ["装饰", "装修", "涂料", "防水", "保温", "门窗", "瓷砖", "吊顶"],
}

def extract_activity_signatures(text):
    """从日报文本中提取活动特征签名"""
    sigs = []
    # 找"地点/区域 + 动作"模式
    # 例如: "机修车间6.977米牛腿预埋件安装"
    activity_pattern = re.findall(
        r'([一-龥]{2,10}(?:车间|库|房|区域|道路|堆棚|场|站|楼|坑|沟|塔|窑|仓|廊))'
        r'[^，。；\n]{0,30}'
        r'([一-龥]{2,6}(?:安装|施工|浇筑|开挖|回填|拆除|绑扎|焊接|铺设|碾压|涂刷|搭设|砌筑|抹灰|养护|验收|清理|破除|吊装|调试))',
        text
    )
    for loc, action in activity_pattern:
        sigs.append(f"{loc}-{action}")
    return list(set(sigs))  # 去重

def categorize_sig(sig):
    """判断活动签名属于哪类工序"""
    for cat, kws in CAT_KEYWORDS.items():
        if any(kw in sig for kw in kws):
            return cat
    return "其他"

def track_project(proj_dir, proj_code):
    """追踪一个项目所有活动签名的起止时间"""
    files = sorted([f for f in os.listdir(proj_dir) if f.endswith(".txt")])
    
    # 每个活动签名的首次/末次出现日期
    sig_first = {}
    sig_last = {}
    daily_sigs = {}  # date -> [sigs]
    
    for fname in files:
        # 从文件名提取日期
        date_str = fname.replace(".txt", "")
        try:
            date = pd.to_datetime(date_str).date()
        except:
            continue
        
        path = os.path.join(proj_dir, fname)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except:
            continue
        
        sigs = extract_activity_signatures(text)
        daily_sigs[date] = sigs
        
        for sig in sigs:
            if sig not in sig_first:
                sig_first[sig] = date
            sig_last[sig] = date
    
    # 计算每周的"活动生命周期"指标
    all_dates = sorted(daily_sigs.keys())
    if len(all_dates) < 7:
        return None
    
    start_d = all_dates[0]
    end_d = all_dates[-1]
    
    # 生成周
    weeks_data = []
    current = start_d
    while current <= end_d:
        w_end = current + timedelta(days=6)
        week_dates = [d for d in all_dates if current <= d <= w_end]
        
        # 本周新出现的签名
        new_sigs = sum(1 for sig, first in sig_first.items() if current <= first <= w_end)
        # 本周结束的签名（最后出现后连续2周不再出现视为结束）
        ended_sigs = 0
        two_weeks_later = w_end + timedelta(days=14)
        for sig, last in sig_last.items():
            if current <= last <= w_end:
                # 检查之后是否真的不再出现
                later_appearances = [d for d in all_dates if d > w_end and d <= two_weeks_later]
                if not later_appearances:
                    ended_sigs += 1
                else:
                    reappeared = any(sig in daily_sigs.get(d, []) for d in later_appearances)
                    if not reappeared:
                        ended_sigs += 1
        
        # 活跃签名总数
        active = sum(1 for sig in sig_first if sig_first[sig] <= w_end and sig_last[sig] >= current)
        
        weeks_data.append({
            "project_code": proj_code,
            "week_start": current,
            "week_end": w_end,
            "total_sigs": len(sig_first),
            "active_sigs": active,
            "new_sigs": new_sigs,
            "ended_sigs": ended_sigs,
            "cumulative_sigs": sum(1 for sig in sig_first if sig_first[sig] <= w_end),
        })
        
        current += timedelta(days=7)
    
    wdf = pd.DataFrame(weeks_data)
    
    # 用累计出现的签名比例作为伪进度
    total_unique = len(sig_first)
    wdf["pseudo_progress"] = wdf["cumulative_sigs"] / total_unique
    wdf["pseudo_weekly"] = wdf["new_sigs"] / total_unique
    
    return wdf, len(sig_first)

print("=" * 60)
print("日报施工活动可追踪性验证")
print("=" * 60)

for proj_dir_name in ["P001", "P003"]:
    proj_dir = os.path.join(RAW_DIR, proj_dir_name)
    if not os.path.isdir(proj_dir):
        print(f"\n{proj_dir_name}: 目录不存在")
        continue
    
    result = track_project(proj_dir, proj_dir_name)
    if result is None:
        print(f"\n{proj_dir_name}: 数据不足")
        continue
    
    wdf, total_sigs = result
    print(f"\n--- {proj_dir_name} ---")
    print(f"  提取活动签名: {total_sigs}个")
    print(f"  生成周数: {len(wdf)}")
    print(f"  活跃签名均值: {wdf['active_sigs'].mean():.1f}")
    print(f"  周均新签名: {wdf['new_sigs'].mean():.1f}")
    print(f"  周均结束签名: {wdf['ended_sigs'].mean():.1f}")
    print(f"  伪累计进度: {wdf['pseudo_progress'].min():.1%} -> {wdf['pseudo_progress'].max():.1%}")
    
    # 与甘特图的进度曲线对比（检查形态是否合理）
    zero_progress_weeks = (wdf['pseudo_weekly'] == 0).sum()
    print(f"  零伪进度周: {zero_progress_weeks}/{len(wdf)} ({zero_progress_weeks/len(wdf):.1%})")
    print(f"  （甘特图零进度周参考值: ~27%）")
    
    # 前5周和后5周的伪进度
    print(f"  前5周伪进度: {wdf['pseudo_weekly'].head(5).tolist()}")
    print(f"  后5周伪进度: {wdf['pseudo_weekly'].tail(5).tolist()}")

print("\n" + "=" * 60)
print("报告结束。关键问题：")
print("1. 提取的活动签名数是否足够？（至少50个才有意义）")
print("2. 伪进度曲线形态是否与甘特图S曲线类似？")
print("3. 零进度周比例是否合理（不是全0或全非0）？")
print("4. 如果活动签名追踪效果差，考虑备选方案：用 avg_items_per_day 做简单归一化")
print("=" * 60)
```

- [ ] **Step 2: 运行验证**

```bash
cd D:/日报预测 && python src/track_activities.py
```

- [ ] **Step 3: 记录结果**

```bash
cd D:/日报预测 && python src/track_activities.py > docs/track_activities_result.txt
```

- [ ] **Step 4: 提交**

```bash
cd D:/日报预测 && git add src/track_activities.py docs/track_activities_result.txt && git commit -m "diagnostic: activity tracking feasibility for daily reports"
```

**决策检查点（重要）:** 这是整个 Phase 2 最关键的分叉点。

- **如果活动签名 >= 50 个且伪进度曲线形态合理** → 走路线 A：构造伪标签，将 P001/P003 加入训练集
- **如果活动签名 < 30 个或伪进度全是噪声** → 走路线 B：日报仅做特征增强，训练仍只用甘特图
- **不确定** → 两条路各走一步（Task 4A 和 4B 都跑），对比后决定

---

### Task 4A: 路线A —— 构造日报伪标签并联合训练

**前置条件:** Task 3 确认活动追踪可行

**Files:**
- Create: `src/add_pseudo_labels.py`
- Modify: `src/train_model.py:200-320`（联合训练逻辑）

**Purpose:** 将日报的施工活动签名转化为伪进度标签，与甘特图数据合并训练。

- [ ] **Step 1: 写伪标签生成器**

```python
# src/add_pseudo_labels.py
"""为日报项目生成伪进度标签，基于施工活动签名追踪"""
import os
import re
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import timedelta

from process_daily import parse_project_daily, aggregate_to_weekly

RAW_DIR = r"D:\日报\清洗数据\dataClean\data\raw"
OUTPUT_DIR = r"D:\日报预测\data\processed"

def extract_activity_signatures(text):
    """与 track_activities.py 相同的逻辑"""
    sigs = []
    activity_pattern = re.findall(
        r'([一-龥]{2,10}(?:车间|库|房|区域|道路|堆棚|场|站|楼|坑|沟|塔|窑|仓|廊))'
        r'[^，。；\n]{0,30}'
        r'([一-龥]{2,6}(?:安装|施工|浇筑|开挖|回填|拆除|绑扎|焊接|铺设|碾压|涂刷|搭设|砌筑|抹灰|养护|验收|清理|破除|吊装|调试))',
        text
    )
    return list(set([f"{loc}-{action}" for loc, action in activity_patterns]))

def build_pseudo_labels(proj_dir, proj_code):
    """为单个日报项目构造伪进度标签"""
    files = sorted([f for f in os.listdir(proj_dir) if f.endswith(".txt")])
    
    # 追踪每个活动签名的首次/末次出现
    sig_first = {}
    sig_last = {}
    
    for fname in files:
        date_str = fname.replace(".txt", "")
        try:
            date = pd.to_datetime(date_str).date()
        except:
            continue
        
        path = os.path.join(proj_dir, fname)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except:
            continue
        
        sigs = extract_activity_signatures(text)
        for sig in sigs:
            if sig not in sig_first:
                sig_first[sig] = date
            sig_last[sig] = date
    
    total_sigs = len(sig_first)
    if total_sigs < 30:
        print(f"  [WARN] {proj_code}: 仅{total_sigs}个活动签名, 伪标签可能不可靠")
    
    # 加载已有的周级特征
    daily_path = os.path.join(OUTPUT_DIR, "weekly_daily.csv")
    daily = pd.read_csv(daily_path, encoding="utf-8-sig")
    daily["week_start"] = pd.to_datetime(daily["week_start"])
    
    proj_weekly = daily[daily["project_code"] == proj_code].copy()
    
    # 对每周计算伪进度
    pseudo_progress = []
    pseudo_cumulative = []
    for _, row in proj_weekly.iterrows():
        ws = pd.to_datetime(row["week_start"]).date()
        we = pd.to_datetime(row["week_end"]).date()
        
        # 本周新出现的签名 → 伪进度增量
        new_count = sum(1 for sig, first in sig_first.items() if ws <= first <= we)
        
        # 截至本周的累计签名 → 伪累计进度
        cum_count = sum(1 for sig, first in sig_first.items() if first <= we)
        
        pseudo_progress.append(new_count / total_sigs)
        pseudo_cumulative.append(cum_count / total_sigs)
    
    proj_weekly["weekly_progress"] = pseudo_progress
    proj_weekly["cumulative_progress"] = pseudo_cumulative
    
    return proj_weekly

def add_pseudo_labels():
    """主入口: 为所有日报项目生成伪标签并更新 weekly_daily.csv"""
    daily = pd.read_csv(
        os.path.join(OUTPUT_DIR, "weekly_daily.csv"), encoding="utf-8-sig"
    )
    daily["week_start"] = pd.to_datetime(daily["week_start"])
    
    updated_dfs = []
    for proj_code in daily["project_code"].unique():
        proj_dir = os.path.join(RAW_DIR, proj_code)
        if os.path.isdir(proj_dir):
            labeled = build_pseudo_labels(proj_dir, proj_code)
            updated_dfs.append(labeled)
            print(f"  {proj_code}: 伪标签注入完成, "
                  f"周均进度={labeled['weekly_progress'].mean():.4f}")
    
    result = pd.concat(updated_dfs, ignore_index=True)
    
    # 覆盖写回
    out_path = os.path.join(OUTPUT_DIR, "weekly_daily_labeled.csv")
    result.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n输出: {out_path}")
    return result

if __name__ == "__main__":
    add_pseudo_labels()
```

- [ ] **Step 2: 运行生成伪标签**

```bash
cd D:/日报预测 && python src/add_pseudo_labels.py
```

预期输出 P001 和 P003 各有伪标签后的周级数据，保存在 `weekly_daily_labeled.csv`。

- [ ] **Step 3: 验证伪标签质量**

```python
# 在 Python 中快速验证
import pandas as pd
labeled = pd.read_csv(r"D:\日报预测\data\processed\weekly_daily_labeled.csv")
gantt = pd.read_csv(r"D:\日报预测\data\processed\weekly_gantt.csv")
print("日报伪标签 vs 甘特图真标签对比:")
print(f"  日报周均进度: {labeled['weekly_progress'].mean():.4f} (甘特图: {gantt['weekly_progress'].mean():.4f})")
print(f"  日报零进度率: {(labeled['weekly_progress']==0).mean():.1%} (甘特图: {(gantt['weekly_progress']==0).mean():.1%})")
print(f"  日报进度std: {labeled['weekly_progress'].std():.4f} (甘特图: {gantt['weekly_progress'].std():.4f})")
# 关键: 分布形态应该大体相似, 但不需要完全一致
```

如果伪标签分布与甘特图标签分布在同一数量级，说明可用。

- [ ] **Step 4: 合并训练集**

修改 `src/train_model.py` 的 `train()` 函数，添加日报数据加载逻辑。在加载 `weekly_gantt.csv` 后追加：

```python
# 在 train() 函数中, 加载日报标签数据
daily_labeled_path = os.path.join(data_dir, "weekly_daily_labeled.csv")
if os.path.exists(daily_labeled_path):
    daily = pd.read_csv(daily_labeled_path, encoding="utf-8-sig")
    daily["week_start"] = pd.to_datetime(daily["week_start"])
    
    # 对齐特征: 日报用甘特图特征集的子集（缺失的填0）
    shared = [c for c in GANTT_FEATURES if c in daily.columns]
    daily_aligned = daily[shared].copy()
    for c in GANTT_FEATURES:
        if c not in daily_aligned.columns:
            daily_aligned[c] = 0
    
    # 补充日报独有特征到特征列表
    extra_features = []
    for c in DAILY_FEATURES:
        if c in daily.columns and c not in GANTT_FEATURES:
            daily_aligned[c] = daily[c]
            extra_features.append(c)
    
    # 合并
    df_aligned = pd.concat([
        df[GANTT_FEATURES + ["project_code"]], 
        daily_aligned[GANTT_FEATURES + extra_features + ["project_code"]]
    ], ignore_index=True)
    
    # 更新特征列表
    all_features = GANTT_FEATURES + extra_features
    print(f"  合并日报数据: {len(daily_aligned)}周, 特征{len(all_features)}个")
```

- [ ] **Step 5: 重新训练并对比**

```bash
cd D:/日报预测 && python -c "
import sys; sys.path.insert(0, 'src')
from train_model import train
train(data_dir=r'D:\日报预测\data\processed', model_dir=r'D:\日报预测\models')
"
```

对比指标：CV MAE 是否低于之前的 0.0076？工期预测误差是否低于 23 周？

- [ ] **Step 6: 提交**

```bash
cd D:/日报预测 && git add src/add_pseudo_labels.py src/train_model.py data/processed/weekly_daily_labeled.csv && git commit -m "feat: pseudo-labels for daily projects, joint training with 7 projects"
```

---

### Task 4B: 路线B —— 日报仅做特征增强（不构造伪标签）

**前置条件:** Task 3 确认活动追踪不可行，或用户选择保守路线

**Files:**
- Modify: `src/process_gantt.py:160-190`（添加日报特征嫁接）
- Modify: `src/train_model.py:200-250`（对齐特征训练）

**Purpose:** 日报不提供标签，但将其天气/人力/机械特征按项目相似度嫁接到甘特图训练集上。

- [ ] **Step 1: 写特征对齐脚本**

```python
# src/align_features.py
"""将日报的天气/人力/机械特征嫁接到甘特图项目"""
import pandas as pd
import numpy as np

GANTT_PATH = r"D:\日报预测\data\processed\weekly_gantt.csv"
DAILY_PATH = r"D:\日报预测\data\processed\weekly_daily.csv"
OUTPUT_PATH = r"D:\日报预测\data\processed\weekly_merged.csv"

gantt = pd.read_csv(GANTT_PATH, encoding="utf-8-sig")
daily = pd.read_csv(DAILY_PATH, encoding="utf-8-sig")
gantt["week_start"] = pd.to_datetime(gantt["week_start"])
daily["week_start"] = pd.to_datetime(daily["week_start"])

# 日报项目级统计（均值）
daily_stats = {}
for col in ["rain_days", "avg_temp", "avg_workers", "total_equip",
            "avg_items_per_day", "cat_土建", "cat_钢结构", "cat_设备安装", "cat_装修"]:
    if col in daily.columns:
        daily_stats[col] = daily[col].mean()

print("日报特征均值:")
for k, v in daily_stats.items():
    print(f"  {k}: {v:.2f}")

# 对每个甘特图项目，根据其工序类型推断日报特征值
# 简单方案: 直接将日报均值赋值给甘特图（作为"典型值"）
# 进阶方案: 根据甘特图 active_tasks 和日报 avg_items_per_day 的比例缩放

# 简单方案实现
for col, mean_val in daily_stats.items():
    gantt[col] = mean_val

# 标记特征来源（日报推断的标记为 True）
gantt["daily_features_inferred"] = True

gantt.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
print(f"\n输出: {OUTPUT_PATH}")
print(f"甘特图 + 日报特征合并: {len(gantt)}周, {len(gantt.columns)}列")
```

- [ ] **Step 2: 运行对齐**

```bash
cd D:/日报预测 && python src/align_features.py
```

- [ ] **Step 3: 扩展特征列表并重新训练**

修改 `train_model.py` 中 `GANTT_FEATURES` 列表，追加日报特征：

```python
GANTT_FEATURES = [
    # ...原有特征...
] + [
    "rain_days", "avg_temp", "avg_workers", "total_equip",
    "avg_items_per_day", "cat_土建", "cat_钢结构", "cat_设备安装", "cat_装修",
]
```

然后用新特征重新训练，加载 `weekly_merged.csv` 而非 `weekly_gantt.csv`。

```bash
cd D:/日报预测 && python -c "
import sys; sys.path.insert(0, 'src')
from train_model import train
# 临时修改: 加载 weekly_merged.csv
train(data_dir=r'D:\日报预测\data\processed', model_dir=r'D:\日报预测\models')
"
```

- [ ] **Step 4: 对比日报特征是否改善模型**

检查新特征的 importance：如果 `rain_days`, `avg_workers` 等日报特征排进 TOP10，说明它们提供了有用信号。如果全排在尾部（importance < 0.01），说明日报特征在当前数据量下帮助不大。

- [ ] **Step 5: 提交**

```bash
cd D:/日报预测 && git add src/align_features.py src/train_model.py data/processed/weekly_merged.csv && git commit -m "feat: align daily weather/manpower features to gantt training set"
```

---

### Task 5: 清洗周期过长的零进度前导段

**Files:**
- Modify: `src/process_gantt.py:180-200`（周级展开的裁剪逻辑）

**Purpose:** N825 项目前 50 周几乎零进度（76个缺日期任务回填导致），这种长零段在训练中会产生大量无信息样本。需要清理。

- [ ] **Step 1: 写前导零段检测与裁剪**

修改 `src/process_gantt.py` 中 `expand_to_weekly()` 函数的裁剪部分。在现有裁剪逻辑（去除首尾空周）之后，添加：

```python
# 在 expand_to_weekly() 中, 现有裁剪逻辑之后添加:

# 裁剪过长的零进度前导段
# 找到第一个 cumulative_progress > 1% 的周, 以及第一个 weekly_progress > 0.1% 的周
# 如果前面有超过 20 周零进度, 只保留最后 4 周零段作为"预热期"
if len(wdf) > 20:
    first_real = wdf[wdf["cumulative_progress"] > wdf["cumulative_progress"].max() * 0.01].index
    first_activity = wdf[wdf["weekly_progress"] > wdf["weekly_progress"].max() * 0.005].index
    
    if len(first_real) > 0:
        cutoff = min(first_real[0], first_activity[0] if len(first_activity) > 0 else first_real[0])
        if cutoff > 24:  # 前面超过24周(约半年)几乎零进度
            keep_tail = max(0, cutoff - 4)  # 保留最后4周零段
            wdf = wdf.iloc[keep_tail:].reset_index(drop=True)
            wdf["week_num"] = range(1, len(wdf) + 1)
            print(f"    {proj}: 裁剪{keep_tail}周零进度前导段")
```

- [ ] **Step 2: 重新运行甘特图处理并验证**

```bash
cd D:/日报预测 && python -c "
import sys; sys.path.insert(0, 'src')
from process_gantt import process
process(
    input_dir=r'C:\Users\Kevin\Desktop\项目staff\甘特图表',
    output_dir=r'D:\日报预测\data\processed',
)
"
```

检查 N825 的周数是否从 142 减少到一个更合理的数字。

- [ ] **Step 3: 重新训练对比**

```bash
cd D:/日报预测 && python -c "
import sys; sys.path.insert(0, 'src')
from train_model import train
train(data_dir=r'D:\日报预测\data\processed', model_dir=r'D:\日报预测\models')
"
```

检查 N825 折的 R2 是否改善（之前只有 0.15）。

- [ ] **Step 4: 提交**

```bash
cd D:/日报预测 && git add src/process_gantt.py data/processed/weekly_gantt.csv models/ && git commit -m "fix: trim excessively long zero-progress lead periods in weekly expansion"
```

---

### Task 6: 输出最终模型与预测接口

**Files:**
- Create: `src/predict_project.py`
- Modify: `README.md`

**Purpose:** 提供一个干净的预测接口，输入新项目的甘特图或周级特征，输出预计完工日期。

- [ ] **Step 1: 写预测脚本**

```python
# src/predict_project.py
"""工期预测接口: 加载模型, 输入周级特征, 输出预计完工周数"""
import os
import numpy as np
import pandas as pd
import joblib

MODEL_DIR = r"D:\日报预测\models"

def load_latest_model():
    """加载最新的训练模型和特征列表"""
    # 找最新的 pkl 文件
    pkl_files = [f for f in os.listdir(MODEL_DIR) if f.endswith(".pkl")]
    if not pkl_files:
        raise FileNotFoundError(f"{MODEL_DIR} 中未找到模型文件")
    latest = sorted(pkl_files)[-1]
    model = joblib.load(os.path.join(MODEL_DIR, latest))
    
    feat_path = os.path.join(MODEL_DIR, "feature_columns.txt")
    with open(feat_path, encoding="utf-8") as f:
        features = [line.strip() for line in f if line.strip()]
    
    print(f"加载模型: {latest}")
    print(f"特征数: {len(features)}")
    return model, features


def predict_duration(model, feature_cols, weekly_data, max_extra_weeks=50):
    """
    逐周滚动预测直到累计进度 >= 99%。
    
    weekly_data: DataFrame, 至少包含 feature_cols 中的特征。
                 需要按 week_num 排序, 包含 cumulative_progress。
                 前3周用于初始化lag特征。
    
    返回: {predicted_weeks, final_cumulative, weekly_predictions}
    """
    df = weekly_data.sort_values("week_num").copy()
    
    # 特征工程（与 train_model.py 中 build_features 一致）
    from train_model import build_features
    df = build_features(df)
    
    if len(df) < 3:
        raise ValueError("至少需要3周数据来初始化lag特征")
    
    cum = df["cumulative_progress"].iloc[2]  # 前3周初始化
    pred_weeks = 3
    predictions = []
    
    for i in range(3, len(df) + max_extra_weeks):
        if cum >= 0.99:
            break
        
        if i < len(df):
            row = df.iloc[i:i+1][feature_cols].fillna(0)
        else:
            # 用最后一周特征近似
            row = df.iloc[-1:][feature_cols].copy()
            row["week_num"] = i + 1
            row["cumulative_progress"] = cum
            row["cum_sqrt"] = np.sqrt(max(cum, 0))
            row["cum_sq"] = cum ** 2
            row["remaining"] = 1.0 - cum
            row = row.fillna(0)
        
        pred = model.predict(row)[0]
        cum += max(pred, 0)
        pred_weeks += 1
        predictions.append({"week": i+1, "predicted_progress": pred, "cumulative": cum})
    
    return {
        "predicted_weeks": pred_weeks,
        "final_cumulative": cum,
        "weekly_predictions": pd.DataFrame(predictions),
    }


if __name__ == "__main__":
    model, features = load_latest_model()
    
    # 示例: 对甘特图项目做预测
    gantt = pd.read_csv(
        r"D:\日报预测\data\processed\weekly_gantt.csv", encoding="utf-8-sig"
    )
    gantt["week_start"] = pd.to_datetime(gantt["week_start"])
    
    print("\n工期预测结果:")
    for proj in sorted(gantt["project_code"].unique()):
        proj_data = gantt[gantt["project_code"] == proj]
        result = predict_duration(model, features, proj_data)
        actual = len(proj_data)
        print(f"  {proj}: 实际{actual}周, 预测{result['predicted_weeks']}周, "
              f"误差{result['predicted_weeks']-actual:+d}周")
```

- [ ] **Step 2: 测试预测接口**

```bash
cd D:/日报预测 && python src/predict_project.py
```

预期输出与 `train_model.py` 中 `simulate_project` 的结果一致。

- [ ] **Step 3: 更新 README.md 使用说明**

在 README.md 末尾追加:

```markdown
## 使用方式

### 对新项目预测工期

```python
from src.predict_project import load_latest_model, predict_duration

model, features = load_latest_model()
# weekly_data 是包含周级特征的 DataFrame
result = predict_duration(model, features, weekly_data)
print(f"预计完工: {result['predicted_weeks']}周")
```

### 数据要求

- 甘特图项目: 需要至少3周的周级特征（由 process_gantt.py 生成）
- 日报项目: 需要至少3周的天气/人力/机械特征（由 process_daily.py 生成）
- 所有特征列名需与 models/feature_columns.txt 一致
```

- [ ] **Step 4: 提交**

```bash
cd D:/日报预测 && git add src/predict_project.py README.md && git commit -m "feat: prediction interface and usage docs"
```

---

## 实施路线图

```
Task 1 (日报诊断) ──→ Task 2 (甘特图诊断) ──→ Task 3 (活动追踪验证)
                                                    │
                                    ┌───────────────┴───────────────┐
                                    ▼                               ▼
                              Task 4A (伪标签+联合训练)       Task 4B (特征嫁接)
                                    │                               │
                                    └───────────────┬───────────────┘
                                                    ▼
                                              Task 5 (清洗零段)
                                                    │
                                                    ▼
                                              Task 6 (预测接口)
```

**建议执行节奏:**
1. 先跑 Task 1-3（纯诊断，不改任何模型代码）→ 用户审阅诊断报告
2. 根据 Task 3 的结果选择 4A 或 4B
3. Task 5 和 6 在任何路线之后都要做

---

## 风险与回退

- **Task 3 活动签名提取质量差**: 退回到 Task 4B（特征嫁接），日报不参与训练
- **Task 4A 伪标签训练效果差**: 伪标签 MAE 远高于真标签 → 降低伪标签样本权重（设为甘特图的 0.5 倍）
- **Task 5 裁剪后模型更差**: 回退裁剪，保留原始周数
- **任何阶段想回退**: 当前模型（`models/weekly_xgboost_*.pkl`）和训练数据（`weekly_gantt.csv`）均有备份
