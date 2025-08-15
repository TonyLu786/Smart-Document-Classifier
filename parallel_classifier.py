# -*- coding: utf-8 -*-
"""
并行分类器模块 - 大数据量性能优化核心
"""
import ahocorasick
import re
from difflib import SequenceMatcher
from typing import List, Optional, Tuple, Dict, Set
import logging
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing as mp
from functools import partial
import numpy as np
import pandas as pd
from config import PERFORMANCE_CONFIG, FUZZY_MATCH_CONFIG

logger = logging.getLogger('ReportClassifier.ParallelClassifier')

class OptimizedSubjectMatcher:
    """优化版主题匹配器"""
    
    def __init__(self, subjects: List[str]):
        self.subjects = subjects
        self.subject_array = np.array(subjects)  # 使用numpy数组加速
        self.subject_set = set(subjects)
        self.automatons = self._build_optimized_automatons()
        self.fuzzy_config = FUZZY_MATCH_CONFIG
        self._precompile_regex_patterns()
    
    def _build_optimized_automatons(self) -> Dict:
        """构建自动机"""
        automatons = {}
        
        # 1. 精确匹配自动机（优化版）
        exact_automaton = ahocorasick.Automaton()
        for i, subject in enumerate(self.subjects):
            exact_automaton.add_word(subject.lower(), (i, subject))
        exact_automaton.make_automaton()
        automatons['exact'] = exact_automaton
        
        # 2. 长度索引优化
        length_index = {}
        for subject in self.subjects:
            length = len(subject)
            if length not in length_index:
                length_index[length] = []
            length_index[length].append(subject)
        automatons['length_index'] = length_index
        
        return automatons
    
    def _precompile_regex_patterns(self):
        """预编译正则表达式模式"""
        self.context_patterns = {}
        base_patterns = {
            '项目': [r'(项目|工程|计划).*?(启动|实施|完成|进展|立项)'],
            '研发': [r'(研发|研究|开发|技术).*?(创新|方案|产品|实验)'],
            '市场': [r'(市场|营销|销售).*?(分析|调研|策略|推广)'],
            '财务': [r'(财务|资金|预算|成本).*?(管理|分析|规划|控制)'],
            '产品': [r'(产品|商品).*?(开发|设计|优化|上线)'],
            '分析': [r'(分析|统计|数据).*?(报告|结果|趋势|洞察)'],
            '评估': [r'(评估|评价|评审).*?(风险|价值|效果|成果)']
        }
        
        for subject, patterns in base_patterns.items():
            self.context_patterns[subject] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def match_batch(self, texts: List[str]) -> List[Optional[Tuple[str, str, float]]]:
        """批量匹配"""
        results = []
        
        # 向量化预处理
        texts_lower = [text.lower() if isinstance(text, str) else "" for text in texts]
        
        # 批量精确匹配
        exact_results = self._batch_exact_match(texts_lower)
        
        # 对未匹配的进行模糊匹配
        for i, text in enumerate(texts):
            if exact_results[i] is not None:
                results.append(exact_results[i])
            else:
                fuzzy_result = self._optimized_fuzzy_match(text)
                results.append(fuzzy_result)
        
        return results
    
    def _batch_exact_match(self, texts_lower: List[str]) -> List[Optional[Tuple[str, str, float]]]:
        """批量精确匹配优化"""
        results = [None] * len(texts_lower)
        
        for i, text_lower in enumerate(texts_lower):
            if len(text_lower) < 2:
                continue
                
            # 使用自动机快速匹配
            matches = []
            for _, (idx, subject) in self.automatons['exact'].iter(text_lower):
                matches.append((subject, 1.0))
            
            if matches:
                # 返回最长的匹配
                matches.sort(key=lambda x: len(x[0]), reverse=True)
                results[i] = (matches[0][0], 'exact', 0.95)
        
        return results
    
    def _optimized_fuzzy_match(self, text: str) -> Optional[Tuple[str, str, float]]:
        """优化模糊匹配"""
        if not isinstance(text, str) or len(text.strip()) < 2:
            return None
        
        text_lower = text.lower()
        
        # 早期精确匹配检查
        exact_match = self._quick_exact_check(text_lower)
        if exact_match:
            return (exact_match[0], 'exact', 0.95)
        
        # 快速上下文匹配
        context_result = self._fast_context_match(text)
        if context_result:
            return context_result
        
        # 如果启用了复杂模糊匹配
        if self.fuzzy_config['enable_word_combination']:
            return self._complex_fuzzy_match(text_lower)
        else:
            # 简化版模糊匹配（性能优先）
            return self._simple_fuzzy_match(text_lower)
    
    def _quick_exact_check(self, text_lower: str) -> Optional[Tuple[str, float]]:
        """快速精确检查"""
        # 按长度快速查找
        text_len = len(text_lower)
        length_index = self.automatons.get('length_index', {})
        
        # 检查相同长度的主题
        if text_len in length_index:
            candidates = length_index[text_len]
            for subject in candidates:
                if subject.lower() == text_lower:
                    return (subject, 1.0)
        
        return None
    
    def _fast_context_match(self, text: str) -> Optional[Tuple[str, str, float]]:
        """快速上下文匹配"""
        for subject, patterns in self.context_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    return (subject, 'context', 0.7)
        return None
    
    def _simple_fuzzy_match(self, text_lower: str) -> Optional[Tuple[str, str, float]]:
        """简化版模糊匹配"""
        best_match = None
        best_score = 0.0
        
        # 只检查前N个最可能的主题（性能优化）
        check_limit = min(50, len(self.subjects))  # 限制检查数量
        
        for subject in self.subjects[:check_limit]:
            subject_lower = subject.lower()
            
            # 快速包含检查
            if subject_lower in text_lower:
                return (subject, 'contains', 0.85)
            
            # 快速相似度检查（只对长度相近的计算）
            if abs(len(subject_lower) - len(text_lower)) <= 10:
                similarity = self._fast_similarity(text_lower, subject_lower)
                if similarity > best_score and similarity >= self.fuzzy_config['min_similarity']:
                    best_score = similarity
                    best_match = subject
        
        if best_match and best_score > 0:
            confidence = min(0.8, max(0.6, best_score))
            return (best_match, 'similarity', confidence)
        
        return None
    
    def _fast_similarity(self, s1: str, s2: str) -> float:
        """快速相似度计算"""
        # 使用更快速的算法
        if len(s1) == 0 or len(s2) == 0:
            return 0.0
        
        # 简化的相似度计算
        common_chars = len(set(s1) & set(s2))
        total_chars = len(set(s1) | set(s2))
        
        if total_chars == 0:
            return 0.0
        
        return common_chars / total_chars
    
    def _complex_fuzzy_match(self, text_lower: str) -> Optional[Tuple[str, str, float]]:
        """复杂模糊匹配（当enable_word_combination=True时使用）"""
        # 原有的复杂匹配逻辑
        # 这里为了性能，默认不启用
        return self._simple_fuzzy_match(text_lower)

def process_chunk(chunk_data: Tuple[List[str], List[str]]) -> List[Optional[Tuple[str, str, float]]]:
    """处理数据块的函数-并行处理"""
    texts, subjects = chunk_data
    matcher = OptimizedSubjectMatcher(subjects)
    return matcher.match_batch(texts)

class ParallelClassifier:
    """并行分类器"""
    
    def __init__(self, subjects: List[str]):
        self.subjects = subjects
        self.matcher = OptimizedSubjectMatcher(subjects)
        self.use_parallel = PERFORMANCE_CONFIG['use_parallel']
        self.max_workers = min(PERFORMANCE_CONFIG['max_workers'], mp.cpu_count())
        self.batch_size = PERFORMANCE_CONFIG['batch_size']
    
    def classify_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """并行分类DataFrame"""
        # 初始化结果列
        df['分类结果'] = '未识别'
        df['匹配置信度'] = 0.0
        df['匹配类型'] = ''
        
        # 获取待处理文本
        texts = []
        valid_indices = []
        
        for idx, row in df.iterrows():
            try:
                report_text = str(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else ""
                if report_text and len(report_text.strip()) >= 2:
                    texts.append(report_text)
                    valid_indices.append(idx)
            except Exception as e:
                logger.warning(f"跳过第{idx+1}行数据: {e}")
                continue
        
        logger.info(f"开始处理 {len(texts)} 条有效记录...")
        
        if not texts:
            return df
        
        # 根据数据量选择处理策略
        if len(texts) < 1000 or not self.use_parallel:
            # 小数据量或禁用并行时使用串行处理
            results = self._serial_process(texts)
        else:
            # 大数据量使用并行处理
            results = self._parallel_process(texts)
        
        # 应用结果
        self._apply_results(df, valid_indices, results)
        
        return df
    
    def _serial_process(self, texts: List[str]) -> List[Optional[Tuple[str, str, float]]]:
        """串行处理"""
        logger.info("使用串行处理模式...")
        return self.matcher.match_batch(texts)
    
    def _parallel_process(self, texts: List[str]) -> List[Optional[Tuple[str, str, float]]]:
        """并行处理"""
        logger.info(f"使用并行处理模式 | 工作进程数: {self.max_workers}")
        
        # 数据分块
        chunks = self._create_chunks(texts)
        logger.info(f"数据分块完成 | 块数: {len(chunks)}")
        
        results = []
        
        try:
            # 使用进程池并行处理
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # 准备任务数据
                task_data = [(chunk, self.subjects) for chunk in chunks]
                
                # 执行并行处理
                chunk_results = list(executor.map(process_chunk, task_data))
                
                # 合并结果
                for chunk_result in chunk_results:
                    results.extend(chunk_result)
                    
        except Exception as e:
            logger.warning(f"并行处理失败，回退到串行处理: {e}")
            results = self._serial_process(texts)
        
        return results
    
    def _create_chunks(self, texts: List[str]) -> List[List[str]]:
        """创建数据块"""
        chunk_size = self.batch_size
        chunks = []
        
        for i in range(0, len(texts), chunk_size):
            chunk = texts[i:i + chunk_size]
            chunks.append(chunk)
        
        return chunks
    
    def _apply_results(self, df: pd.DataFrame, indices: List[int], results: List[Optional[Tuple[str, str, float]]]):
        """应用处理结果到DataFrame"""
        stats = {'matched': 0, 'exact': 0, 'fuzzy': 0, 'context': 0, 'unmatched': 0}
        
        for idx, result in zip(indices, results):
            if result:
                subject, match_type, confidence = result
                df.at[idx, '分类结果'] = subject
                df.at[idx, '匹配置信度'] = confidence
                df.at[idx, '匹配类型'] = match_type
                
                stats['matched'] += 1
                if match_type == 'exact':
                    stats['exact'] += 1
                elif match_type in ['similarity', 'contains']:
                    stats['fuzzy'] += 1
                elif match_type == 'context':
                    stats['context'] += 1
            else:
                df.at[idx, '分类结果'] = '未识别'
                df.at[idx, '匹配置信度'] = 0.0
                df.at[idx, '匹配类型'] = 'none'
                stats['unmatched'] += 1
        
        logger.info(f"分类统计 | 总计: {len(indices)} | 精确: {stats['exact']} | 模糊: {stats['fuzzy']} | 上下文: {stats['context']} | 未匹配: {stats['unmatched']}")