# -*- coding: utf-8 -*-
"""
关键词提取模块
"""
import jieba
import jieba.posseg as pseg
from collections import Counter
import logging
from functools import lru_cache
from typing import List, Set, Dict, Optional
import re
import pandas as pd
from tqdm import tqdm
from config import CLASSIFICATION_CONFIG, FILE_PATHS, DOMAIN_KEYWORDS

logger = logging.getLogger('ReportClassifier.EnhancedKeywordExtractor')

class EnhancedKeywordExtractor:
    """关键词提取器"""
    
    def __init__(self):
        self._init_jieba()
        self.geo_names = self._load_geo_names()
        self.stop_words = self._load_stop_words()
        self.domain_keywords = DOMAIN_KEYWORDS
    
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
            
            # 主要城市（部分）
            '北京市', '上海市', '广州市', '深圳市', '杭州市', '南京市', '武汉市',
            '成都市', '西安市', '天津市', '重庆市', '苏州市', '青岛市', '长沙市',
            '大连市', '厦门市', '宁波市', '无锡市', '合肥市', '太原市', '沈阳市',
            
            # 常见地名后缀
            '省', '市', '县', '区', '镇', '乡', '村'
        ]
        
        geo_names.update(common_geo_names)
        
        # 从文件加载（如果存在）
        try:
            with open(FILE_PATHS['geo_names'], 'r', encoding='utf-8') as f:
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
            '没有', '看', '好', '自己', '这', '那', '里', '就是', '还是', '为了',
            '可以', '应该', '能够', '已经', '现在', '这个', '那个', '这些', '那些'
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
    
    def _infer_domain_from_text(self, text: str) -> Optional[str]:
        """从文本推断领域"""
        domain_scores = {}
        
        for domain, keywords in self.domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            domain_scores[domain] = score
        
        if domain_scores:
            best_domain = max(domain_scores.items(), key=lambda x: x[1])
            if best_domain[1] > 0:
                return best_domain[0]
        
        return None
    
    @lru_cache(maxsize=CLASSIFICATION_CONFIG['cache_size'])
    def extract_keywords(self, text: str, top_n: int = 3, domain: str = None) -> str:
        """增强版关键词提取（排除地名）"""
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
                
                # 特殊字符过滤
                if re.match(r'^[^\u4e00-\u9fa5a-zA-Z0-9]+$', word):
                    continue
                
                words.append(word)
            
            if not words:
                # 如果没有合适的词，返回原文的前50个字符（但仍然过滤地名）
                filtered_text = self._filter_geo_names_from_text(text[:100])
                return filtered_text[:50] if len(filtered_text) > 50 else filtered_text
            
            # 词频统计
            word_counter = Counter(words)
            
            # 领域关键词增强
            if domain and domain in self.domain_keywords:
                domain_words = self.domain_keywords[domain]
                enhanced_scores = {}
                
                for word, freq in word_counter.items():
                    if word in domain_words:
                        enhanced_scores[word] = freq * 2.0  # 领域词权重更高
                    else:
                        enhanced_scores[word] = freq
                
                # 按增强权重排序
                sorted_keywords = sorted(enhanced_scores.items(), key=lambda x: (-x[1], -len(x[0])))
            else:
                # 按词频排序
                sorted_keywords = sorted(word_counter.items(), key=lambda x: (-x[1], -len(x[0])))
            
            return '; '.join([w[0] for w in sorted_keywords[:top_n]])
            
        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return text[:50] if len(text) > 50 else text
    
    def _filter_geo_names_from_text(self, text: str) -> str:
        """从文本中过滤地名"""
        words = jieba.lcut(text)
        filtered_words = [word for word in words if not self._is_geo_name(word)]
        return ''.join(filtered_words)

def extract_keywords_selective(df: pd.DataFrame) -> pd.DataFrame:
    """选择性关键词提取（只对低置信度结果提取）"""
    extractor = EnhancedKeywordExtractor()
    keyword_count = 0
    min_confidence = CLASSIFICATION_CONFIG['min_confidence_threshold']
    
    logger.info("开始选择性关键词提取...")
    
    # 只对未匹配或低置信度的结果提取关键词
    need_keyword_mask = (
        (df['分类结果'] == '未识别') | 
        (df['匹配置信度'] < min_confidence) |
        df['匹配置信度'].isna()
    )
    
    need_keyword_indices = df[need_keyword_mask].index
    
    logger.info(f"需要提取关键词的记录数: {len(need_keyword_indices)}")
    
    # 使用tqdm显示进度
    for idx in tqdm(need_keyword_indices, desc="关键词提取中"):
        try:
            if pd.isna(df.at[idx, '关键词']) or df.at[idx, '关键词'] == '':
                report_text = str(df.at[idx, df.columns[2]]) if len(df.columns) > 2 else ""
                
                # 推断领域
                domain = extractor._infer_domain_from_text(report_text)
                
                # 提取关键词
                keywords = extractor.extract_keywords(report_text, domain=domain)
                df.at[idx, '关键词'] = keywords
                keyword_count += 1
        except Exception as e:
            logger.error(f"提取第{idx+1}行关键词时出错: {e}")
            continue
    
    logger.info(f"关键词提取完成 | 处理数: {keyword_count}")
    return df