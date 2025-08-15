# -*- coding: utf-8 -*-
"""
增强版分类器模块
"""
import ahocorasick
import re
from difflib import SequenceMatcher
from typing import List, Optional, Tuple, Dict, Set
import logging
from tqdm import tqdm
import pandas as pd
import numpy as np
from config import FUZZY_MATCH_CONFIG, CLASSIFICATION_CONFIG

logger = logging.getLogger('ReportClassifier.EnhancedClassifier')

class ProfessionalSubjectMatcher:
    """专业级主题匹配器"""
    
    def __init__(self, subjects: List[str]):
        self.subjects = subjects
        self.subject_set = set(subjects)
        self.automatons = self._build_professional_automatons()
        self.fuzzy_config = FUZZY_MATCH_CONFIG
        self._precompile_patterns()
        self._build_similarity_index()
    
    def _build_professional_automatons(self) -> Dict:
        """构建自动机"""
        automatons = {}
        
        # 1. 精确匹配自动机
        exact_automaton = ahocorasick.Automaton()
        for i, subject in enumerate(self.subjects):
            exact_automaton.add_word(subject.lower(), (i, subject))
        exact_automaton.make_automaton()
        automatons['exact'] = exact_automaton
        
        # 2. 分词自动机（用于模糊匹配）
        word_automaton = ahocorasick.Automaton()
        all_words = set()
        for subject in self.subjects:
            # 分词：单字 + 常用词组
            words = self._smart_tokenize(subject)
            all_words.update(words)
        
        for word in all_words:
            word_automaton.add_word(word.lower(), word)
        word_automaton.make_automaton()
        automatons['word'] = word_automaton
        
        # 3. 长度索引（用于快速筛选）
        length_index = {}
        for subject in self.subjects:
            length = len(subject)
            if length not in length_index:
                length_index[length] = []
            length_index[length].append(subject)
        automatons['length_index'] = length_index
        
        return automatons
    
    def _smart_tokenize(self, text: str) -> List[str]:
        """智能分词"""
        words = []
        
        # 添加完整词
        words.append(text)
        
        # 添加单字
        words.extend(list(text))
        
        # 添加2-3字组合（滑动窗口）
        for window_size in [2, 3]:
            if len(text) >= window_size:
                for i in range(len(text) - window_size + 1):
                    words.append(text[i:i + window_size])
        
        # 添加首尾词（常见模式）
        if len(text) > 2:
            words.append(text[:2])  # 前两字
            words.append(text[-2:])  # 后两字
            words.append(text[0] + text[-1])  # 首尾字
        
        return list(set(words))  # 去重
    
    def _precompile_patterns(self):
        """预编译模式匹配"""
        self.context_patterns = {
            '项目': [
                re.compile(r'(项目|工程|计划|方案).*?(启动|实施|完成|进展|立项|开展)', re.IGNORECASE),
                re.compile(r'(关于|有关).*?项目', re.IGNORECASE)
            ],
            '研发': [
                re.compile(r'(研发|研究|开发|技术).*?(创新|方案|产品|实验|算法)', re.IGNORECASE),
                re.compile(r'(AI|ML|DL|人工智能|机器学习).*?(研究|开发)', re.IGNORECASE)
            ],
            '市场': [
                re.compile(r'(市场|营销|销售).*?(分析|调研|策略|推广|客户)', re.IGNORECASE),
                re.compile(r'(用户|客户).*?(需求|调研|分析)', re.IGNORECASE)
            ],
            '财务': [
                re.compile(r'(财务|资金|预算|成本|收入).*?(管理|分析|规划|控制)', re.IGNORECASE),
                re.compile(r'(利润|营收|支出).*?(统计|分析)', re.IGNORECASE)
            ],
            '产品': [
                re.compile(r'(产品|商品).*?(开发|设计|优化|上线|迭代)', re.IGNORECASE),
                re.compile(r'(功能|特性).*?(设计|开发)', re.IGNORECASE)
            ],
            '分析': [
                re.compile(r'(分析|统计|数据).*?(报告|结果|趋势|洞察|可视化)', re.IGNORECASE),
                re.compile(r'(数据|指标).*?(分析|统计)', re.IGNORECASE)
            ],
            '评估': [
                re.compile(r'(评估|评价|评审|考核).*?(风险|价值|效果|成果)', re.IGNORECASE),
                re.compile(r'(绩效|表现).*?(评估|评价)', re.IGNORECASE)
            ]
        }
    
    def _build_similarity_index(self):
        """构建相似度索引（用于加速模糊匹配）"""
        # 预计算主题词的特征向量
        self.subject_features = {}
        for subject in self.subjects:
            self.subject_features[subject] = self._extract_features(subject)
    
    def _extract_features(self, text: str) -> Dict[str, float]:
        """提取文本特征"""
        features = {
            'length': len(text),
            'char_set': set(text.lower()),
            'first_char': text[0].lower() if text else '',
            'last_char': text[-1].lower() if text else '',
            'word_count': len(text.split())
        }
        return features
    
    def match(self, text: str) -> Optional[Tuple[str, str, float]]:
        """专业级匹配"""
        if not isinstance(text, str) or len(text.strip()) < CLASSIFICATION_CONFIG['min_text_length']:
            return None
        
        # 1. 精确匹配（最高优先级）
        exact_result = self._exact_match(text)
        if exact_result:
            return exact_result
        
        # 2. 模糊匹配（核心修复）
        fuzzy_result = self._professional_fuzzy_match(text)
        if fuzzy_result and fuzzy_result[2] > 0:  # 确保置信度大于0
            return fuzzy_result
        
        # 3. 上下文匹配（兜底）
        context_result = self._context_match(text)
        if context_result:
            return context_result
        
        return None
    
    def _exact_match(self, text: str) -> Optional[Tuple[str, str, float]]:
        """精确匹配"""
        text_lower = text.lower()
        matches = []
        
        for _, (idx, subject) in self.automatons['exact'].iter(text_lower):
            matches.append((subject, 'exact', 0.95))
        
        if matches:
            # 返回最长的匹配（更具体）
            matches.sort(key=lambda x: len(x[0]), reverse=True)
            return matches[0]
        
        return None
    
    def _professional_fuzzy_match(self, text: str) -> Optional[Tuple[str, str, float]]:
        """专业级模糊匹配"""
        if not isinstance(text, str) or len(text.strip()) < 2:
            return None
        
        text_lower = text.lower().strip()
        best_matches = []
        
        # 1. 包含匹配（最简单有效）
        for subject in self.subjects:
            subject_lower = subject.lower()
            if subject_lower in text_lower and len(subject_lower) >= 2:
                # 计算包含度
                overlap_ratio = len(subject_lower) / len(text_lower)
                confidence = min(0.85, 0.6 + overlap_ratio * 0.3)
                best_matches.append((subject, 'contains', confidence))
        
        # 2. 相似度匹配
        similarity_matches = self._similarity_based_match(text_lower)
        best_matches.extend(similarity_matches)
        
        # 3. 分词匹配
        word_matches = self._word_based_match(text_lower)
        best_matches.extend(word_matches)
        
        # 4. 编辑距离匹配
        edit_distance_matches = self._edit_distance_match(text_lower)
        best_matches.extend(edit_distance_matches)
        
        if best_matches:
            # 按置信度排序
            best_matches.sort(key=lambda x: x[2], reverse=True)
            best_match = best_matches[0]
            
            # 确保最小置信度
            if best_match[2] > 0:
                return best_match
        
        return None
    
    def _similarity_based_match(self, text_lower: str) -> List[Tuple[str, str, float]]:
        """基于相似度的匹配"""
        matches = []
        
        for subject in self.subjects:
            subject_lower = subject.lower()
            
            # 快速过滤：长度差异过大则跳过
            if abs(len(subject_lower) - len(text_lower)) > max(len(subject_lower), len(text_lower)) * 0.8:
                continue
            
            # 计算多种相似度
            ratio_similarity = SequenceMatcher(None, text_lower, subject_lower).ratio()
            
            # 字符集合相似度
            text_chars = set(text_lower)
            subject_chars = set(subject_lower)
            if text_chars and subject_chars:
                char_similarity = len(text_chars & subject_chars) / len(text_chars | subject_chars)
            else:
                char_similarity = 0
            
            # 综合相似度
            combined_similarity = (ratio_similarity * 0.7 + char_similarity * 0.3)
            
            if combined_similarity >= self.fuzzy_config['min_similarity'] * 0.7:  # 降低阈值
                confidence = min(0.8, max(0.4, combined_similarity))
                matches.append((subject, 'similarity', confidence))
        
        return matches
    
    def _word_based_match(self, text_lower: str) -> List[Tuple[str, str, float]]:
        """基于分词的匹配"""
        matches = []
        
        # 找到文本中的所有相关词汇
        found_words = set()
        for _, word in self.automatons['word'].iter(text_lower):
            if len(word) >= 2:  # 过滤单字
                found_words.add(word.lower())
        
        for subject in self.subjects:
            subject_words = set([w.lower() for w in self._smart_tokenize(subject) if len(w) >= 2])
            
            if subject_words and found_words:
                # 计算词汇重叠度
                common_words = found_words.intersection(subject_words)
                if common_words:
                    overlap_ratio = len(common_words) / len(subject_words)
                    if overlap_ratio >= 0.3:  # 降低重叠要求
                        confidence = min(0.75, max(0.3, overlap_ratio * 0.9))
                        matches.append((subject, 'word_overlap', confidence))
        
        return matches
    
    def _edit_distance_match(self, text_lower: str) -> List[Tuple[str, str, float]]:
        """基于编辑距离的匹配"""
        matches = []
        
        for subject in self.subjects:
            subject_lower = subject.lower()
            
            # 只对长度相近的词计算编辑距离
            if abs(len(subject_lower) - len(text_lower)) <= 5:
                distance = self._levenshtein_distance(text_lower, subject_lower)
                max_len = max(len(text_lower), len(subject_lower))
                
                if max_len > 0:
                    similarity = 1 - (distance / max_len)
                    if similarity >= self.fuzzy_config['min_similarity'] * 0.8:
                        confidence = min(0.7, max(0.2, similarity * 0.8))
                        matches.append((subject, 'edit_distance', confidence))
        
        return matches
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算编辑距离"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _context_match(self, text: str) -> Optional[Tuple[str, str, float]]:
        """上下文匹配"""
        for subject, patterns in self.context_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    return (subject, 'context', 0.65)  # 适中置信度
        
        return None

def classify_reports_professional(df: pd.DataFrame, subjects: List[str]) -> pd.DataFrame:
    """专业级批量分类报告"""
    matcher = ProfessionalSubjectMatcher(subjects)
    
    # 初始化结果列
    df['分类结果'] = '未识别'
    df['匹配置信度'] = 0.0
    df['匹配类型'] = ''
    df['关键词'] = ''
    
    stats = {
        'total': len(df),
        'matched': 0,
        'unmatched': 0,
        'exact_match': 0,
        'fuzzy_match': 0,
        'context_match': 0
    }
    
    logger.info(f"开始专业分类处理 {stats['total']} 条记录...")
    
    # 使用tqdm显示进度
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="专业分类处理中"):
        try:
            report_text = str(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else ""
            
            if not report_text or len(report_text.strip()) < CLASSIFICATION_CONFIG['min_text_length']:
                continue
                
            # 主题匹配
            match_result = matcher.match(report_text)
            if match_result:
                subject, match_type, confidence = match_result
                
                df.at[idx, '分类结果'] = subject
                df.at[idx, '匹配置信度'] = float(confidence)  # 确保是float类型
                df.at[idx, '匹配类型'] = match_type
                stats['matched'] += 1
                
                # 统计各类匹配
                if match_type == 'exact':
                    stats['exact_match'] += 1
                elif match_type in ['contains', 'similarity', 'word_overlap', 'edit_distance']:
                    stats['fuzzy_match'] += 1
                elif match_type == 'context':
                    stats['context_match'] += 1
            else:
                df.at[idx, '分类结果'] = '未识别'
                df.at[idx, '匹配置信度'] = 0.0
                df.at[idx, '匹配类型'] = 'none'
                stats['unmatched'] += 1
                
        except Exception as e:
            logger.error(f"处理第{idx+1}行时出错: {e}")
            continue
    
    logger.info(f"专业分类完成 | 总计: {stats['total']} | 精确: {stats['exact_match']} | 模糊: {stats['fuzzy_match']} | 上下文: {stats['context_match']} | 未匹配: {stats['unmatched']}")
    
    # 计算匹配率
    match_rate = stats['matched'] / max(1, stats['total'])
    logger.info(f"总体匹配率: {match_rate:.1%}")
    
    return df