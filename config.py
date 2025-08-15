# -*- coding: utf-8 -*-
"""
配置管理模块
"""
import os
from pathlib import Path
import sys

def get_project_root():
    """获取项目根目录"""
    # 方法1: 从当前文件位置向上查找
    current_file = Path(__file__).resolve()
    
    # 向上查找直到找到项目根目录标识
    current_path = current_file.parent
    max_depth = 10  # 最大查找深度
    
    for _ in range(max_depth):
        # 检查是否为项目根目录（包含关键文件）
        if (current_path / "README.md").exists() or \
           (current_path / "main.py").exists() or \
           (current_path / "requirements.txt").exists():
            return current_path
        current_path = current_path.parent
        if current_path == current_path.parent:  # 到达文件系统根目录
            break
    
    # 方法2: 使用当前工作目录
    cwd = Path.cwd().resolve()
    if (cwd / "main.py").exists():
        return cwd
    
    # 方法3: 返回当前文件所在目录
    return current_file.parent

# 项目根目录
PROJECT_ROOT = get_project_root()

# 标准化目录结构
DIRECTORIES = {
    'input': PROJECT_ROOT / "input_files",
    'output': PROJECT_ROOT / "output_files", 
    'sample': PROJECT_ROOT / "sample_data",
    'logs': PROJECT_ROOT / "logs",
    'data': PROJECT_ROOT / "data",
    'docs': PROJECT_ROOT / "docs"
}

# 确保所有目录存在
for dir_name, dir_path in DIRECTORIES.items():
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        # print(f"✅ 确保目录存在: {dir_path}")
    except Exception as e:
        print(f"⚠️  创建目录失败 {dir_path}: {e}")

# 文件路径配置 - 完全基于项目根目录
FILE_PATHS = {
    'project_root': PROJECT_ROOT,
    'input_dir': DIRECTORIES['input'],
    'output_dir': DIRECTORIES['output'],
    'sample_dir': DIRECTORIES['sample'],
    'log_dir': DIRECTORIES['logs'],
    'data_dir': DIRECTORIES['data'],
    'docs_dir': DIRECTORIES['docs'],
    'professional_dict': PROJECT_ROOT / 'professional_terms.txt',
    'geo_names': PROJECT_ROOT / 'geo_names.txt',
    'enhanced_subjects': PROJECT_ROOT / 'enhanced_subjects.json',
    'log_file': DIRECTORIES['logs'] / 'report_classifier.log'
}

def get_smart_input_file():
    """智能获取输入文件 - 项目根目录优化"""
    input_dir = DIRECTORIES['input']
    
    # 支持的Excel文件扩展名
    excel_extensions = {'.xlsx', '.xls', '.xlsm'}
    
    # 查找所有Excel文件
    excel_files = []
    try:
        if input_dir.exists():
            for file_path in input_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in excel_extensions:
                    # 排除示例文件和备份文件
                    if not any(keyword in file_path.name.lower() 
                              for keyword in ['sample', 'example', 'backup', 'template']):
                        excel_files.append(file_path)
    except Exception as e:
        print(f"扫描输入目录时出错: {e}")
    
    # 按修改时间排序（最新的在前）
    excel_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    if excel_files:
        return str(excel_files[0])
    
    # 如果没有找到用户文件，检查示例文件
    sample_files = []
    try:
        sample_dir = DIRECTORIES['sample']
        if sample_dir.exists():
            for file_path in sample_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in excel_extensions:
                    sample_files.append(file_path)
    except Exception as e:
        print(f"扫描示例目录时出错: {e}")
    
    if sample_files:
        return str(sample_files[0])
    
    return None

def get_default_config_paths():
    """获取默认配置路径"""
    return {
        'main_excel': get_smart_input_file(),
        'input_directory': str(DIRECTORIES['input']),
        'output_directory': str(DIRECTORIES['output'])
    }

# 动态配置路径
DYNAMIC_PATHS = get_default_config_paths()

# 合并所有路径配置
FILE_PATHS.update(DYNAMIC_PATHS)

# 分类配置
CLASSIFICATION_CONFIG = {
    'base_subjects': ['项目', '研发', '市场', '财务', '产品', '分析', '评估'],
    'allow_pos': {'n', 'vn', 'an', 'nz', 'eng'},
    'keyword_top_n': 3,
    'min_text_length': 2,
    'cache_size': 20000,
    'min_confidence_threshold': 0.8
}

# 性能优化配置
PERFORMANCE_CONFIG = {
    'use_parallel': True,
    'max_workers': max(1, os.cpu_count() - 1),  # 保留一个CPU核心
    'batch_size': 1000,
    'enable_vectorization': True,
    'precompile_patterns': True,
    'use_memory_mapping': True,
    'chunk_size': 5000
}

# 模糊匹配配置
FUZZY_MATCH_CONFIG = {
    'min_similarity': 0.4,
    'max_edit_distance': 5,
    'context_window_size': 50,
    'enable_word_combination': True,
    'enable_partial_matching': True,
    'early_termination_threshold': 0.95,
    'min_overlap_ratio': 0.2,
    'confidence_boost_factor': 1.2
}

# 领域关键词配置
DOMAIN_KEYWORDS = {
    'technology': {
        '人工智能', '机器学习', '深度学习', '神经网络', '算法', '数据挖掘',
        '大数据', '云计算', '区块链', '物联网', '5G', '量子计算',
        'AI', 'ML', 'DL', '算法优化', '模型训练', '特征工程'
    },
    'business': {
        '市场营销', '财务管理', '人力资源', '供应链', '商业模式',
        '战略规划', '风险控制', '投资', '融资', '并购',
        '销售', '预算', '成本控制', '利润', '营收'
    },
    'research': {
        '实验', '研究', '开发', '创新', '专利', '技术', '方案',
        '可行性', '验证', '测试', '优化', '调研', '分析'
    }
}

# 打印配置信息（调试用）
def print_config_info():
    """打印配置信息"""
    print("=" * 50)
    print("📊 项目配置信息")
    print("=" * 50)
    print(f"🏠 项目根目录: {PROJECT_ROOT}")
    print(f"📥 输入目录: {DIRECTORIES['input']}")
    print(f"📤 输出目录: {DIRECTORIES['output']}")
    print(f"📝 日志目录: {DIRECTORIES['logs']}")
    print(f"📋 当前输入文件: {DYNAMIC_PATHS['main_excel'] or '未找到'}")
    print("=" * 50)

# 在模块导入时打印配置（可选）
# print_config_info()