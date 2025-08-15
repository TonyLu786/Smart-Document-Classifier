# -*- coding: utf-8 -*-
"""
性能监控模块
"""
import time
import psutil
import logging
from typing import Dict, Any
import functools

logger = logging.getLogger('ReportClassifier.PerformanceMonitor')

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.start_time = None
        self.start_memory = None
    
    def start_monitoring(self):
        """开始监控"""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        logger.info("开始性能监控")
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """停止监控并返回统计信息"""
        if not self.start_time:
            return {}
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        elapsed_time = end_time - self.start_time
        memory_used = end_memory - self.start_memory
        
        stats = {
            'elapsed_time': elapsed_time,
            'memory_used_mb': memory_used,
            'peak_memory_mb': end_memory
        }
        
        logger.info(f"性能统计 | 耗时: {elapsed_time:.2f}s | 内存使用: {memory_used:.1f}MB | 峰值内存: {end_memory:.1f}MB")
        
        return stats

def performance_timer(func):
    """性能计时装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            end_memory = process.memory_info().rss / 1024 / 1024
            
            elapsed_time = end_time - start_time
            memory_used = end_memory - start_memory
            
            logger.info(f"{func.__name__} | 耗时: {elapsed_time:.2f}s | 内存变化: {memory_used:.1f}MB")
    
    return wrapper