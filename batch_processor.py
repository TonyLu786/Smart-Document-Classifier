# -*- coding: utf-8 -*-
"""
批量处理器 
"""
import pandas as pd
import logging
from typing import List, Generator
from config import PERFORMANCE_CONFIG

logger = logging.getLogger('ReportClassifier.BatchProcessor')

class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, chunk_size: int = None):
        self.chunk_size = chunk_size or PERFORMANCE_CONFIG['chunk_size']
    
    def process_in_chunks(self, df: pd.DataFrame, processor_func) -> pd.DataFrame:
        """分块处理DataFrame"""
        if len(df) <= self.chunk_size:
            # 数据量小，直接处理
            return processor_func(df)
        
        logger.info(f"启用分块处理 | 总行数: {len(df)} | 块大小: {self.chunk_size}")
        
        processed_chunks = []
        total_chunks = (len(df) + self.chunk_size - 1) // self.chunk_size
        
        for i in range(0, len(df), self.chunk_size):
            chunk = df.iloc[i:i + self.chunk_size].copy()
            logger.info(f"处理第 {i//self.chunk_size + 1}/{total_chunks} 块")
            
            try:
                processed_chunk = processor_func(chunk)
                processed_chunks.append(processed_chunk)
            except Exception as e:
                logger.error(f"处理第 {i//self.chunk_size + 1} 块时出错: {e}")
                processed_chunks.append(chunk)  # 保留原始数据
        
        # 合并所有块
        logger.info("合并处理结果...")
        result_df = pd.concat(processed_chunks, ignore_index=True)
        logger.info("分块处理完成")
        
        return result_df
    
    def memory_efficient_iter(self, df: pd.DataFrame) -> Generator[pd.DataFrame, None, None]:
        """内存高效迭代"""
        for i in range(0, len(df), self.chunk_size):
            yield df.iloc[i:i + self.chunk_size]