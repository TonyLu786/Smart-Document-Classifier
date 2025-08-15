# -*- coding: utf-8 -*-
"""
数据加载模块 - 权限错误修复版
"""
import pandas as pd
import logging
from typing import List, Optional
from pathlib import Path
import os
import shutil
from datetime import datetime
import time
from config import FILE_PATHS, CLASSIFICATION_CONFIG, DIRECTORIES

logger = logging.getLogger('ReportClassifier.DataLoader')

def find_excel_files(directory: Path, exclude_patterns: List[str] = None) -> List[Path]:
    """查找目录下的所有Excel文件"""
    if exclude_patterns is None:
        exclude_patterns = ['sample', 'example', 'backup', 'template', '~$']
    
    excel_extensions = {'.xlsx', '.xls', '.xlsm'}
    excel_files = []
    
    if directory.exists() and directory.is_dir():
        try:
            for file_path in directory.iterdir():
                if (file_path.is_file() and 
                    file_path.suffix.lower() in excel_extensions and
                    not any(pattern in file_path.name.lower() for pattern in exclude_patterns)):
                    excel_files.append(file_path)
        except PermissionError as e:
            logger.warning(f"无权限访问目录 {directory}: {e}")
        except Exception as e:
            logger.error(f"扫描目录 {directory} 时出错: {e}")
    
    # 按修改时间排序（最新的在前）
    return sorted(excel_files, key=lambda x: x.stat().st_mtime, reverse=True)

def get_input_excel_file() -> Optional[str]:
    """智能获取待处理的Excel文件路径"""
    # 1. 首先检查input_files文件夹
    input_dir = Path(FILE_PATHS['input_dir'])
    input_files = find_excel_files(input_dir)
    
    if input_files:
        if len(input_files) > 1:
            logger.info(f"📁 input_files文件夹中发现 {len(input_files)} 个Excel文件:")
            for i, file in enumerate(input_files[:5]):
                logger.info(f"  {i+1}. {file.name}")
            logger.info("💡 将使用最新修改的文件")
        
        selected_file = input_files[0]
        logger.info(f"✅ 找到待处理文件: {selected_file.name}")
        return str(selected_file)
    
    # 2. 检查sample_data文件夹
    sample_dir = Path(FILE_PATHS['sample_dir'])
    sample_files = find_excel_files(sample_dir)
    
    if sample_files:
        logger.info("💡 使用示例数据文件进行演示")
        logger.info("💡 请将您的Excel文件放入 input_files 文件夹以处理真实数据")
        return str(sample_files[0])
    
    # 3. 都没有找到，提供清晰的用户指导
    logger.error("❌ 未找到可处理的Excel文件！")
    logger.info("=" * 60)
    logger.info("📋 简单使用指南：")
    logger.info(f"1. 📁 请将待处理的Excel文件放入项目目录下的 'input_files' 文件夹")
    logger.info(f"   路径: {input_dir}")
    logger.info(f"2. ✅ 支持的文件格式: .xlsx, .xls, .xlsm")
    logger.info(f"3. 🔄 程序会自动处理最新修改的文件")
    logger.info("=" * 60)
    
    create_user_friendly_files(input_dir)
    
    return None

def create_user_friendly_files(directory: Path):
    """创建用户友好的提示文件"""
    try:
        readme_path = directory / "README.txt"
        if not readme_path.exists():
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write("""📊 报告分类系统 - 文件放置说明

📌 简单使用步骤：
1. 将您的Excel文件放在此目录中
2. 运行主程序 (python main.py)
3. 处理结果将保存在原文件中

📋 文件格式要求：
- Sheet1: 报告数据表（第3列包含待分类文本）
- Sheet2: 主题词表（第2列包含自定义主题词，可选）

✅ 支持的格式：
- Microsoft Excel: .xlsx, .xls, .xlsm

💡 小贴士：
- 程序会自动处理最新修改的文件
- 原文件会自动备份
- 支持中文文件名

有任何问题请查看项目文档或联系开发者。
""")
            logger.info(f"💡 已创建使用说明文件: {readme_path}")

    except Exception as e:
        logger.warning(f"创建用户友好文件失败: {e}")

def load_subjects(file_path: str) -> List[str]:
    """加载主题库"""
    try:
        logger.debug("📚 开始加载主题简称库...")
        df_subjects = pd.read_excel(file_path, sheet_name='Sheet2', usecols='B')
        base_subjects = CLASSIFICATION_CONFIG['base_subjects']
        subjects = list(set(df_subjects.dropna().iloc[:, 0].tolist() + base_subjects))
        subjects.sort(key=len, reverse=True)
        logger.info(f"✅ 主题库加载完成 | 主题数: {len(subjects)}")
        return subjects
    except FileNotFoundError:
        logger.warning("⚠️ 主题库Sheet2未找到，使用基础主题词")
        return CLASSIFICATION_CONFIG['base_subjects']
    except Exception as e:
        logger.error(f"❌ 加载主题库失败: {e}")
        return CLASSIFICATION_CONFIG['base_subjects']

def load_reports_df(file_path: str) -> pd.DataFrame:
    """使用pandas加载报告数据"""
    try:
        logger.info("📊 开始加载报告数据...")
        df = pd.read_excel(file_path, sheet_name='Sheet1')
        logger.info(f"✅ 报告数据加载完成 | 行数: {len(df):,}")
        return df
    except FileNotFoundError:
        logger.error(f"❌ 文件未找到: {file_path}")
        raise
    except Exception as e:
        logger.error(f"❌ 加载报告数据失败: {e}")
        raise

def save_reports_df(df: pd.DataFrame, file_path: str, sheet_name: str = 'Sheet1'):
    """保存处理后的数据 - 权限错误修复版"""
    try:
        output_path = Path(file_path)
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 检查文件是否被占用
        if output_path.exists():
            if is_file_locked(output_path):
                logger.warning(f"⚠️ 检测到文件可能被其他程序占用: {output_path.name}")
                logger.info("💡 解决方案:")
                logger.info("  1. 请关闭正在打开该Excel文件的程序")
                logger.info("  2. 或者程序将自动创建新的输出文件")
                
                # 创建新的输出文件
                new_file_path = create_safe_output_file(output_path, df)
                logger.info(f"✅ 已创建新文件: {new_file_path}")
                return
        
        # 生成备份文件名
        backup_path = None
        if output_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = output_path.parent / f"{output_path.stem}_backup_{timestamp}{output_path.suffix}"
            
            # 尝试创建备份（带重试机制）
            backup_path = create_backup_with_retry(output_path, backup_path)
        
        # 保存处理结果（带重试机制）
        save_with_retry(df, file_path, sheet_name)
        
        logger.info(f"✅ 数据保存完成: {output_path.name}")
        if backup_path and backup_path.exists():
            logger.info(f"   📎 原文件已备份: {backup_path.name}")
            
    except Exception as e:
        logger.error(f"❌ 保存数据失败: {e}")
        # 提供替代方案
        alternative_save(df, file_path)
        raise

def is_file_locked(file_path: Path) -> bool:
    """检查文件是否被锁定"""
    try:
        # 尝试以独占模式打开文件
        with open(file_path, 'r+b') as f:
            pass
        return False
    except (PermissionError, IOError):
        return True
    except Exception:
        # 其他错误不确定是否锁定
        return False

def create_backup_with_retry(original_path: Path, backup_path: Path, max_retries: int = 3) -> Optional[Path]:
    """带重试机制的备份创建"""
    for attempt in range(max_retries):
        try:
            shutil.copy2(str(original_path), str(backup_path))
            logger.info(f"💾 已创建备份文件: {backup_path.name}")
            return backup_path
        except PermissionError:
            if attempt < max_retries - 1:
                logger.warning(f"⚠️ 备份创建失败，{2 ** attempt}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)  # 指数退避
            else:
                logger.error(f"❌ 备份创建失败: 无法访问原文件")
                return None
        except Exception as e:
            logger.error(f"❌ 备份创建异常: {e}")
            return None
    return None

def save_with_retry(df: pd.DataFrame, file_path: str, sheet_name: str, max_retries: int = 3):
    """带重试机制的文件保存"""
    for attempt in range(max_retries):
        try:
            logger.info("💾 开始保存处理结果...")
            with pd.ExcelWriter(file_path, engine='openpyxl', mode='w') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            return
        except PermissionError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"⚠️ 文件保存失败，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                logger.info("💡 请确保Excel文件已关闭")
                time.sleep(wait_time)
            else:
                logger.error(f"❌ 文件保存失败: 权限被拒绝")
                raise e
        except Exception as e:
            logger.error(f"❌ 文件保存异常: {e}")
            raise e

def create_safe_output_file(original_path: Path, df: pd.DataFrame) -> str:
    """创建安全的输出文件（当原文件被占用时）"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_file_path = original_path.parent / f"{original_path.stem}_processed_{timestamp}{original_path.suffix}"
    
    try:
        # 直接创建新文件
        with pd.ExcelWriter(str(safe_file_path), engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        logger.info(f"✅ 成功创建处理结果文件: {safe_file_path.name}")
        return str(safe_file_path)
    except Exception as e:
        logger.error(f"❌ 创建安全输出文件失败: {e}")
        raise

def alternative_save(df: pd.DataFrame, original_file_path: str):
    """替代保存方案"""
    try:
        original_path = Path(original_file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 方案1: 保存到output目录
        output_dir = Path(FILE_PATHS.get('output_dir', original_path.parent / 'output_files'))
        output_dir.mkdir(exist_ok=True)
        
        alt_file_path = output_dir / f"{original_path.stem}_processed_{timestamp}{original_path.suffix}"
        
        with pd.ExcelWriter(str(alt_file_path), engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        logger.info(f"💡 文件已保存到替代位置: {alt_file_path}")
        logger.info("💡 建议手动将结果复制到原文件")
        
    except Exception as e:
        logger.error(f"❌ 替代保存方案也失败: {e}")
        # 最后的方案：保存为CSV
        try:
            csv_path = Path(original_file_path).with_suffix('.csv')
            df.to_csv(str(csv_path), index=False, encoding='utf-8-sig')
            logger.info(f"💡 最终方案：已保存为CSV格式: {csv_path}")
        except Exception as csv_e:
            logger.error(f"❌ 所有保存方案都失败: {csv_e}")