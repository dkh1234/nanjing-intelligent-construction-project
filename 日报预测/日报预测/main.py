#!/usr/bin/env python3
"""
建筑工程项目工期预测系统 - 主入口
一键运行: 甘特图处理 → 日报处理 → 模型训练

用法:
  python main.py                        # 运行全流程
  python main.py --skip-daily           # 跳过日报处理
  python main.py --gantt-only           # 仅处理甘特图
"""
import os
import sys
import argparse

# 确保 src 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from process_gantt import process as process_gantt
from process_daily import process as process_daily
from train_model import train as train_model


# ---- 默认路径配置 ----
GANTT_INPUT = r"C:\Users\Kevin\Desktop\项目staff\甘特图表"
DAILY_INPUT = os.path.join(os.path.dirname(__file__), "data", "daily")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "data", "processed")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")


def main():
    parser = argparse.ArgumentParser(description="建筑工程项目工期预测系统")
    parser.add_argument("--skip-daily", action="store_true", help="跳过日报处理")
    parser.add_argument("--gantt-only", action="store_true", help="仅处理甘特图")
    parser.add_argument("--gantt-input", default=GANTT_INPUT, help="甘特图目录")
    parser.add_argument("--daily-input", default=DAILY_INPUT, help="日报目录")
    args = parser.parse_args()

    print("=" * 70)
    print("  建筑工程项目工期预测系统")
    print("=" * 70)

    # ---- Step 1: 甘特图处理 ----
    print("\n" + "█" * 70)
    print("  STEP 1/3: 甘特图 → 周级训练集")
    print("█" * 70)

    if not os.path.isdir(args.gantt_input):
        print(f"  [ERROR] 甘特图目录不存在: {args.gantt_input}")
        print(f"  请将5个甘特图xlsx放入该目录，或用 --gantt-input 指定路径")
        sys.exit(1)

    tasks, weekly_gantt = process_gantt(
        input_dir=args.gantt_input,
        output_dir=PROCESSED_DIR,
    )

    if args.gantt_only:
        print("\n甘特图处理完成，退出。")
        return

    # ---- Step 2: 日报处理 ----
    if args.skip_daily:
        print("\n[SKIP] 跳过日报处理")
    else:
        print("\n" + "█" * 70)
        print("  STEP 2/3: 日报 → 周级特征")
        print("█" * 70)

        if not os.path.isdir(args.daily_input):
            print(f"  [WARN] 日报目录不存在: {args.daily_input}, 跳过")
        else:
            process_daily(
                input_dir=args.daily_input,
                output_dir=PROCESSED_DIR,
            )

    # ---- Step 3: 模型训练 ----
    print("\n" + "█" * 70)
    print("  STEP 3/3: 模型训练")
    print("█" * 70)

    model, features = train_model(
        data_dir=PROCESSED_DIR,
        model_dir=MODEL_DIR,
    )

    print(f"\n{'='*70}")
    print(f"  全流程完成!")
    print(f"  处理后的数据: {PROCESSED_DIR}")
    print(f"  训练好的模型: {MODEL_DIR}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
