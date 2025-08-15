# -*- coding: utf-8 -*-
"""
工具函数模块
"""
import logging
import time
import pandas as pd
from pathlib import Path
from typing import Dict, Any
from config import FILE_PATHS

def setup_logger() -> logging.Logger:
    """配置日志系统"""
    logger = logging.getLogger('ReportClassifier')
    logger.setLevel(logging.DEBUG)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 文件处理器
    file_handler = logging.FileHandler(FILE_PATHS['log_file'], encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | [%(name)s.%(funcName)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def add_statistics_to_df(df: pd.DataFrame, stats: Dict[str, Any], exec_time: float) -> pd.DataFrame:
    """添加统计信息到DataFrame"""
    try:
        # 创建统计信息DataFrame
        stats_data = [
            ["==== 处理统计 ===="],
            [f"处理时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"],
            [f"总处理数: {stats.get('total', 0)}"],
            [f"匹配数: {stats.get('matched', 0)}"],
            [f"精确匹配: {stats.get('exact_match', 0)}"],
            [f"模糊匹配: {stats.get('fuzzy_match', 0)}"],
            [f"匹配率: {stats.get('matched', 0)/max(1, stats.get('total', 1)):.1%}"],
            [f"未匹配数: {stats.get('unmatched', 0)}"],
            [f"处理速度: {stats.get('total', 0)/max(1, exec_time):.1f} 行/秒"]
        ]
        
        stats_df = pd.DataFrame(stats_data, columns=['统计信息'])
        
        # 合并到原数据
        result_df = pd.concat([df, pd.DataFrame([{}]), stats_df], ignore_index=True)
        return result_df
        
    except Exception as e:
        logging.getLogger('ReportClassifier.Utils').error(f"添加统计信息失败: {e}")
        return df