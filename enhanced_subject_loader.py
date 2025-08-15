# -*- coding: utf-8 -*-
"""
主题库加载器
"""
import pandas as pd
import json
from typing import List, Dict, Set
import logging
from config import FILE_PATHS

logger = logging.getLogger('ReportClassifier.EnhancedSubjectLoader')

class EnhancedSubjectLoader:
    """主题库加载器"""
    
    def __init__(self):
        self.base_subjects = ['项目', '研发', '市场', '财务', '产品', '分析', '评估']
        self.subject_weights = {}
    
    def load_from_excel(self, file_path: str, sheet_name: str = 'Sheet2') -> List[str]:
        """从Excel加载主题"""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, usecols='B')
            subjects = df.dropna().iloc[:, 0].astype(str).tolist()
            logger.info(f"从Excel加载主题: {len(subjects)}个")
            return subjects
        except Exception as e:
            logger.error(f"Excel加载失败: {e}")
            return []
    
    def load_from_json(self, file_path: str) -> Dict:
        """从JSON文件加载主题和权重"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"从JSON加载主题配置")
                return data
        except Exception as e:
            logger.error(f"JSON加载失败: {e}")
            return {'subjects': [], 'weights': {}}
    
    def preprocess_subjects(self, subjects: List[str]) -> List[str]:
        """主题预处理"""
        processed = set()
        
        for subject in subjects:
            # 清理空白字符
            subject = subject.strip()
            
            # 过滤过短的词
            if len(subject) < 2:
                continue
            
            # 过滤纯数字
            if subject.isdigit():
                continue
            
            processed.add(subject)
        
        return list(processed)
    
    def build_enhanced_subject_library(self) -> List[str]:
        """构建主题库"""
        all_subjects = set(self.base_subjects)
        
        # 从Excel加载
        excel_subjects = self.load_from_excel(FILE_PATHS['main_excel'])
        all_subjects.update(excel_subjects)
        
        # 从JSON加载（如果存在）
        try:
            json_data = self.load_from_json(FILE_PATHS['enhanced_subjects'])
            json_subjects = json_data.get('subjects', [])
            self.subject_weights.update(json_data.get('weights', {}))
            all_subjects.update(json_subjects)
        except Exception as e:
            logger.info("JSON主题文件未找到，使用默认配置")
        
        # 预处理
        processed_subjects = self.preprocess_subjects(list(all_subjects))
        
        # 按权重和长度排序
        def sort_key(subject):
            weight = self.subject_weights.get(subject, 1.0)
            return (-weight, -len(subject))  # 权重高、长度长的优先
        
        processed_subjects.sort(key=sort_key)
        
        logger.info(f"主题库构建完成 | 总数: {len(processed_subjects)}")
        return processed_subjects