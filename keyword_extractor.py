# enhanced_keyword_extractor.py
import jieba
import jieba.posseg as pseg
import pandas as pd
from collections import Counter
import logging
from functools import lru_cache
from typing import List, Set
import re
from tqdm import tqdm


logger = logging.getLogger('ReportClassifier.EnhancedKeywordExtractor')

class EnhancedKeywordExtractor:
    """关键词提取器"""
    
    def __init__(self):
        self._init_jieba()
        self.geo_names = self._load_geo_names()
        self.stop_words = self._load_stop_words()
    
    def _init_jieba(self):
        """初始化jieba分词"""
        jieba.setLogLevel(jieba.logging.INFO)
        try:
            jieba.load_userdict(str(FILE_PATHS['professional_dict']))
            logger.info("专业词典加载成功")
        except Exception as e:
            logger.warning(f"专业词典加载失败: {e}")
    
    def _load_geo_names(self) -> Set[str]:
        """加载地名词典"""
        geo_names = set()
        
        # 常见地名列表
        common_geo_names = [
            # 省级行政区
            '北京', '上海', '天津', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江',
            '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南',
            '广东', '海南', '四川', '贵州', '云南', '陕西', '甘肃', '青海', '台湾',
            '内蒙古', '广西', '西藏', '宁夏', '新疆', '香港', '澳门',
            
            # 主要城市
            '北京市', '上海市', '广州市', '深圳市', '杭州市', '南京市', '武汉市',
            '成都市', '西安市', '天津市', '重庆市', '苏州市', '青岛市', '长沙市',
            
            # 常见地名后缀
            '省', '市', '县', '区', '镇', '乡', '村'
        ]
        
        geo_names.update(common_geo_names)
        
        # 从文件加载（如果存在）
        try:
            with open('geo_names.txt', 'r', encoding='utf-8') as f:
                file_geo_names = [line.strip() for line in f if line.strip()]
                geo_names.update(file_geo_names)
        except FileNotFoundError:
            logger.info("地名词典文件未找到，使用默认地名列表")
        
        return geo_names
    
    def _load_stop_words(self) -> Set[str]:
        """加载停用词"""
        stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
            '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着',
            '没有', '看', '好', '自己', '这', '那', '里', '就是', '还是', '为了'
        }
        return stop_words
    
    def _is_geo_name(self, word: str) -> bool:
        """判断是否为地名"""
        # 直接匹配
        if word in self.geo_names:
            return True
        
        # 正则表达式匹配
        geo_patterns = [
            r'.*[省市县区镇乡村]$',
            r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][省市县区]$'
        ]
        
        for pattern in geo_patterns:
            if re.match(pattern, word):
                return True
        
        return False
    
    @lru_cache(maxsize=CLASSIFICATION_CONFIG['cache_size'])
    def extract_keywords(self, text: str, top_n: int = 3) -> str:
        """关键词提取（排除地名）"""
        try:
            if not isinstance(text, str) or len(text.strip()) == 0:
                return ""
            
            # 词性过滤和地名过滤
            allow_pos = CLASSIFICATION_CONFIG['allow_pos']
            words = []
            
            for word, flag in pseg.cut(text):
                # 基本过滤条件
                if (len(word) <= 1 or 
                    flag[0] not in allow_pos or 
                    word in self.stop_words):
                    continue
                
                # 地名过滤
                if self._is_geo_name(word):
                    continue
                
                # 数字过滤
                if word.isdigit() or re.match(r'^\d+[年月日时分秒]$', word):
                    continue
                
                words.append(word)
            
            if not words:
                # 如果没有合适的词，返回原文的前50个字符（但仍然过滤地名）
                filtered_text = self._filter_geo_names_from_text(text[:100])
                return filtered_text[:50] if len(filtered_text) > 50 else filtered_text
            
            # 词频统计和排序
            word_counter = Counter(words)
            # 考虑词的位置权重（开头的词权重更高）
            position_weights = self._calculate_position_weights(text, words)
            
            # 综合排序：词频权重 + 位置权重
            weighted_keywords = []
            for word, freq in word_counter.items():
                position_weight = position_weights.get(word, 1.0)
                combined_score = freq * position_weight
                weighted_keywords.append((word, combined_score))
            
            keywords = sorted(weighted_keywords, key=lambda x: (-x[1], -len(x[0])))
            
            return '; '.join([w[0] for w in keywords[:top_n]])
            
        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return text[:50] if len(text) > 50 else text
    
    def _filter_geo_names_from_text(self, text: str) -> str:
        """从文本中过滤地名"""
        words = jieba.lcut(text)
        filtered_words = [word for word in words if not self._is_geo_name(word)]
        return ''.join(filtered_words)
    
    def _calculate_position_weights(self, text: str, words: List[str]) -> dict:
        """计算词的位置权重"""
        weights = {}
        text_length = len(text)
        
        for word in words:
            # 找到词在文本中的位置
            pos = text.find(word)
            if pos != -1:
                # 位置权重：越靠前权重越高
                position_ratio = pos / text_length
                weights[word] = 2.0 - position_ratio  # 前面的词权重更高
            else:
                weights[word] = 1.0
        
        return weights
    

class DomainSpecificKeywordExtractor(EnhancedKeywordExtractor):
    """领域特定关键词提取器"""
    
    def __init__(self):
        super().__init__()
        self.domain_keywords = self._load_domain_keywords()
    
    def _load_domain_keywords(self) -> Dict[str, Set[str]]:
        """加载领域关键词"""
        return {
            'technology': {
                '人工智能', '机器学习', '深度学习', '神经网络', '算法', '数据挖掘',
                '大数据', '云计算', '区块链', '物联网', '5G', '量子计算'
            },
            'business': {
                '市场营销', '财务管理', '人力资源', '供应链', '商业模式',
                '战略规划', '风险控制', '投资', '融资', '并购'
            },
            'research': {
                '实验', '研究', '开发', '创新', '专利', '技术', '方案',
                '可行性', '验证', '测试', '优化'
            }
        }
    
    def extract_domain_keywords(self, text: str, domain: str = None, top_n: int = 3) -> str:
        """提取领域特定关键词"""
        # 基础关键词提取
        basic_keywords = self.extract_keywords(text, top_n * 2)  # 多提取一些
        keyword_list = basic_keywords.split('; ') if basic_keywords else []
        
        # 领域关键词增强
        if domain and domain in self.domain_keywords:
            domain_words = self.domain_keywords[domain]
            enhanced_keywords = []
            
            # 优先选择领域相关关键词
            for keyword in keyword_list:
                if keyword in domain_words:
                    enhanced_keywords.append((keyword, 2.0))  # 领域词权重更高
                else:
                    enhanced_keywords.append((keyword, 1.0))
            
            # 按权重排序
            enhanced_keywords.sort(key=lambda x: (-x[1], -len(x[0])))
            final_keywords = [kw[0] for kw in enhanced_keywords[:top_n]]
            
            return '; '.join(final_keywords)
        
        return '; '.join(keyword_list[:top_n])