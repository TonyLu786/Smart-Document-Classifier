# -*- coding: utf-8 -*-
"""
报告主题分类系统主程序
"""
import time
import pandas as pd
import logging
import os
import sys
from pathlib import Path
from config import FILE_PATHS, CLASSIFICATION_CONFIG
from data_loader import load_reports_df, save_reports_df, get_input_excel_file
from enhanced_subject_loader import EnhancedSubjectLoader
from enhanced_classifier import classify_reports_professional
from enhanced_keyword_extractor import extract_keywords_selective
from utils import setup_logger
from performance_monitor import PerformanceMonitor

def validate_environment():
    """验证运行环境"""
    logger = logging.getLogger('ReportClassifier.Environment')
    
    required_dirs = [
        FILE_PATHS['input_dir'],
        FILE_PATHS['output_dir'],
        FILE_PATHS['sample_dir']
    ]
    
    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            logger.info(f"创建目录: {path}")
            path.mkdir(parents=True, exist_ok=True)
    
    logger.info("✅ 环境验证通过")

def check_file_permissions(file_path: str) -> bool:
    """检查文件权限"""
    path = Path(file_path)
    if not path.exists():
        # 文件不存在，检查目录权限
        return path.parent.exists() and os.access(path.parent, os.W_OK)
    else:
        # 文件存在，检查读写权限
        return os.access(path, os.R_OK | os.W_OK)

def main():
    """主函数 - 增强错误处理版"""
    logger = setup_logger()
    logger.info("🚀 程序启动：报告主题分类系统 v8.2 ")
    logger.info(f"🖥️  运行平台: {sys.platform}")
    logger.info(f"📂 工作目录: {Path.cwd()}")
    
    validate_environment()
    
    perf_monitor = PerformanceMonitor()
    perf_monitor.start_monitoring()
    
    start_time = time.time()
    
    try:
        file_path = get_input_excel_file()
        if not file_path:
            logger.error("程序退出：未找到可处理的Excel文件")
            logger.info("请按照上述指南放置文件后重新运行")
            return 1
        
        logger.info(f"📄 开始处理文件: {Path(file_path).name}")
        
        # 检查文件权限
        if not check_file_permissions(file_path):
            logger.warning(f"⚠️ 检测到文件权限问题: {file_path}")
            logger.info("💡 建议:")
            logger.info("  1. 确保文件不在系统保护目录中")
            logger.info("  2. 以管理员权限运行程序")
            logger.info("  3. 将文件复制到项目目录处理")
        
        # 加载主题库
        logger.info("📚 加载主题库...")
        subject_loader = EnhancedSubjectLoader()
        subjects = subject_loader.build_enhanced_subject_library()
        
        # 加载报告数据
        logger.info("📊 加载报告数据...")
        df = load_reports_df(file_path)
        
        # 分类处理
        logger.info("🤖 开始智能分类处理...")
        df_classified = classify_reports_professional(df, subjects)
        
        # 关键词提取
        logger.info("🔑 开始关键词提取...")
        df_final = extract_keywords_selective(df_classified)
        
        # 保存结果（增强版）
        logger.info("💾 保存处理结果...")
        try:
            save_reports_df(df_final, file_path)
        except PermissionError:
            logger.error("❌ 文件保存失败：权限被拒绝")
            logger.info("💡 解决方案:")
            logger.info("  1. 确保Excel文件已完全关闭")
            logger.info("  2. 检查文件是否被其他程序占用")
            logger.info("  3. 尝试以管理员权限运行程序")
            logger.info("  4. 将文件复制到其他位置处理")
            raise
        except Exception as e:
            logger.error(f"❌ 保存过程中出现错误: {e}")
            raise
        
        # 性能统计
        exec_time = time.time() - start_time
        perf_stats = perf_monitor.stop_monitoring()
        
        total_rows = len(df_final)
        matched_rows = len(df_final[df_final['分类结果'] != '未识别'])
        exact_matches = len(df_final[df_final['匹配类型'] == 'exact'])
        fuzzy_matches = len(df_final[df_final['匹配类型'].isin(['contains', 'similarity', 'word_overlap', 'edit_distance'])])
        context_matches = len(df_final[df_final['匹配类型'] == 'context'])
        unmatched_rows = len(df_final[df_final['分类结果'] == '未识别'])
        
        expected_speed = total_rows / max(1, exec_time) if exec_time > 0 else 0
        
        logger.info("=" * 60)
        logger.info("🎯 处理完成统计:")
        logger.info(f"  📊 总处理数: {total_rows:,}")
        logger.info(f"  ✅ 精确匹配: {exact_matches:,}")
        logger.info(f"  🔍 模糊匹配: {fuzzy_matches:,}")
        logger.info(f"  📝 上下文匹配: {context_matches:,}")
        logger.info(f"  🎯 匹配总数: {matched_rows:,}")
        logger.info(f"  📈 匹配率: {matched_rows/max(1, total_rows):.1%}")
        logger.info(f"  ❌ 未匹配数: {unmatched_rows:,}")
        logger.info(f"  ⏱️  处理耗时: {exec_time:.2f}s")
        logger.info(f"  ⚡ 处理速度: {expected_speed:.1f}条/秒")
        if 'peak_memory_mb' in perf_stats:
            logger.info(f"  💾 内存使用: {perf_stats['peak_memory_mb']:.1f}MB")
        logger.info("=" * 60)
        
        logger.info("🎉 程序执行成功完成！")
        return 0
        
    except KeyboardInterrupt:
        logger.info("⚠️  用户中断程序执行")
        return 1
    except PermissionError as e:
        logger.critical(f"🔐 权限错误: {e}")
        logger.info("🔧 解决方案:")
        logger.info("  1. 确保Excel文件已完全关闭")
        logger.info("  2. 检查杀毒软件是否锁定文件")
        logger.info("  3. 以管理员权限运行程序")
        logger.info("  4. 将文件复制到项目input_files目录处理")
        return 1
    except Exception as e:
        logger.critical(f"💥 系统错误: {e}", exc_info=True)
        logger.info("🔧 建议检查:")
        logger.info("  1. Excel文件格式是否正确")
        logger.info("  2. 文件是否被其他程序占用")
        logger.info("  3. 是否有足够的磁盘空间")
        logger.info("  4. 杀毒软件是否干扰文件操作")
        return 1
    finally:
        logger.info("🔚 程序结束")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)