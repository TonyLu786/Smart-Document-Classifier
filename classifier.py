# -*- coding: utf-8 -*-
"""
分类器核心模块
"""
import ahocorasick
import logging
import pandas as pd
from typing import List, Optional, Tuple, Dict
from tqdm import tqdm
from config import CLASSIFICATION_CONFIG
import re

logger = logging.getLogger('ReportClassifier.EnhancedClassifier')

class MultiLevelSubjectMatcher:
    """多层次主题匹配器"""
    
    def __init__(self, subjects: List[str]):
        self.subjects = subjects
        self.automatons = self._build_multi_level_automatons()
    
    def _build_multi_level_automatons(self) -> Dict[str, ahocorasick.Automaton]:
        """构建多层次自动机"""
        automatons = {}
        
        # 1. 精确匹配自动机
        exact_automaton = ahocorasick.Automaton()
        for subject in self.subjects:
            exact_automaton.add_word(subject.lower(), subject)
        exact_automaton.make_automaton()
        automatons['exact'] = exact_automaton
        
        # 2. 模糊匹配模式（包含常见变体）
        fuzzy_patterns = {}
        for subject in self.subjects:
            # 生成模糊匹配模式
            patterns = self._generate_fuzzy_patterns(subject)
            fuzzy_patterns[subject] = patterns
        automatons['fuzzy_patterns'] = fuzzy_patterns
        
        # 3. 上下文匹配模式
        context_patterns = self._build_context_patterns()
        automatons['context'] = context_patterns
        
        return automatons
    
    def _generate_fuzzy_patterns(self, subject: str) -> List[str]:
        """生成模糊匹配模式"""
        patterns = [subject]
        
        # 添加常见后缀
        suffixes = ['项目', '方案', '计划', '报告', '总结', '分析']
        for suffix in suffixes:
            if not subject.endswith(suffix):
                patterns.append(f"{subject}{suffix}")
        
        # 添加常见前缀
        prefixes = ['关于', '有关', '关于对', '针对']
        for prefix in prefixes:
            patterns.append(f"{prefix}{subject}")
        
        return patterns
    
    def _build_context_patterns(self) -> Dict[str, re.Pattern]:
        """构建上下文匹配模式"""
        patterns = {
            'project': re.compile(r'(项目|工程|计划).*?(启动|实施|完成|进展)'),
            'research': re.compile(r'(研发|研究|开发).*?(技术|产品|方案)'),
            'market': re.compile(r'(市场|营销|销售).*?(分析|调研|策略)'),
            'finance': re.compile(r'(财务|资金|预算).*?(管理|分析|规划)'),
            'product': re.compile(r'(产品|商品).*?(开发|设计|优化)')
        }
        return patterns
    
    def match(self, text: str) -> Optional[Tuple[str, str]]:
        """多层次匹配"""
        if not isinstance(text, str) or len(text.strip()) < 2:
            return None
        
        text_lower = text.lower()
        
        # 1. 精确匹配（最高优先级）
        exact_match = self._exact_match(text_lower)
        if exact_match:
            return (exact_match, 'exact')
        
        # 2. 模糊匹配
        fuzzy_match = self._fuzzy_match(text)
        if fuzzy_match:
            return (fuzzy_match, 'fuzzy')
        
        # 3. 上下文匹配
        context_match = self._context_match(text)
        if context_match:
            return (context_match, 'context')
        
        return None
    
    def _exact_match(self, text_lower: str) -> Optional[str]:
        """精确匹配"""
        for _, subject in self.automatons['exact'].iter(text_lower):
            return subject
        return None
    
    def _fuzzy_match(self, text: str) -> Optional[str]:
        """模糊匹配"""
        for subject, patterns in self.automatons['fuzzy_patterns'].items():
            for pattern in patterns:
                if pattern.lower() in text.lower():
                    return subject
        return None
    
    def _context_match(self, text: str) -> Optional[str]:
        """上下文匹配"""
        # 可以根据业务需求扩展
        for subject_type, pattern in self.automatons['context'].items():
            if pattern.search(text):
                # 映射到具体主题
                type_mapping = {
                    'project': '项目',
                    'research': '研发', 
                    'market': '市场',
                    'finance': '财务',
                    'product': '产品'
                }
                return type_mapping.get(subject_type)
        return None