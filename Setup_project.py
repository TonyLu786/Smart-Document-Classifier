# -*- coding: utf-8 -*-
"""
项目初始化脚本 - 创建标准目录结构
"""
from pathlib import Path
import sys

def setup_project_structure():
    """创建项目标准目录结构"""
    # 获取当前目录作为项目根目录
    project_root = Path.cwd()
    
    print(f"🚀 开始初始化项目目录结构...")
    print(f"🏠 项目根目录: {project_root}")
    
    # 定义标准目录结构
    directories = [
        "input_files",
        "output_files", 
        "sample_data",
        "logs",
        "data",
        "docs"
    ]
    
    # 创建目录
    created_dirs = []
    for dir_name in directories:
        dir_path = project_root / dir_name
        try:
            dir_path.mkdir(exist_ok=True)
            created_dirs.append(dir_name)
            print(f"✅ 创建目录: {dir_name}")
        except Exception as e:
            print(f"❌ 创建目录失败 {dir_name}: {e}")
    
    # 创建必要的文件
    files_to_create = {
        "input_files/README.txt": """📊 报告分类系统 - 使用说明

📌 简单三步使用：
1. 将您的Excel文件放在此目录
2. 运行主程序 (python main.py)  
3. 查看处理结果

支持格式: .xlsx, .xls, .xlsm
""",
        "sample_data/sample_report.xlsx": "",  # 占位符
        ".gitignore": """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
.venv/

# Logs  
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Backup
*_backup_*
"""
    }
    
    created_files = []
    for file_path, content in files_to_create.items():
        full_path = project_root / file_path
        try:
            # 确保父目录存在
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建文件
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            created_files.append(file_path)
            print(f"✅ 创建文件: {file_path}")
        except Exception as e:
            print(f"❌ 创建文件失败 {file_path}: {e}")
    
    print(f"\n🎉 项目初始化完成！")
    print(f"📁 创建了 {len(created_dirs)} 个目录")
    print(f"📄 创建了 {len(created_files)} 个文件")
    print(f"\n💡 下一步:")
    print(f"1. 将您的Excel文件放入 input_files 目录")
    print(f"2. 运行: python main.py")

if __name__ == "__main__":
    setup_project_structure()