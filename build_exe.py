import os
import sys
import shutil
import subprocess
import logging
from datetime import datetime

# 配置日志
def setup_logging():
    log_dir = 'log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'build_exe_{timestamp}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_file

def check_required_files():
    """检查必需的文件是否存在"""
    required_files = {
        'aria2c.exe': '请从 https://github.com/aria2/aria2/releases 下载 aria2c.exe',
        'icons/Blender-VMT [256x256].ico': '请确保图标文件存在于 icons 目录',
        'lang': '请确保语言文件目录存在',
        'blender_version_manager.py': '主程序文件缺失'
    }
    
    missing_files = []
    for file_path, message in required_files.items():
        if not os.path.exists(file_path):
            missing_files.append(f"{file_path}: {message}")
    
    return missing_files

def create_license():
    """创建许可证文件"""
    license_content = """Blender版本管理器 - 一个用于管理 Blender 版本的工具
Copyright (C) 2024 dhjs0000

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
    
    with open('LICENSE', 'w', encoding='utf-8') as f:
        f.write(license_content)
    logging.info("创建许可证文件成功")

def build_exe():
    try:
        # 检查必需文件
        missing_files = check_required_files()
        if missing_files:
            for missing in missing_files:
                logging.error(f"缺少必需文件: {missing}")
            raise FileNotFoundError("缺少必需文件，请查看日志了解详情")
        
        # 创建许可证文件
        create_license()
        
        # 安装必要的包
        logging.info("正在安装必要的包...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pyinstaller'])
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'aria2p'])
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'PyQt6'])
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'beautifulsoup4'])
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'psutil'])
        
        # 卸载 PyQt5 以避免冲突
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'uninstall', '-y', 'PyQt5'])
            logging.info("已卸载 PyQt5")
        except:
            logging.info("PyQt5 未安装或卸载失败")
        
        # 定义需要包含的文件和文件夹
        additional_files = [
            ('icons/*', 'icons'),  # 图标文件夹
            ('lang/*', 'lang'),    # 语言文件夹
            ('aria2c.exe', '.'),   # aria2c 可执行文件
            ('LICENSE', '.'),      # 简短版权声明
            ('LICENSE.txt', '.'),  # 完整的 GPL-3.0 许可证
            ('runtime_hook.py', '.')  # 运行时钩子
        ]
            
        # 构建 PyInstaller 命令
        cmd = [
            'pyinstaller',
            '--noconfirm',
            '--clean',
            '--windowed',  # 使用 GUI 模式
            '--name=Blender版本管理器',
            '--icon=icons/Blender-VMT [256x256].ico',
            '--runtime-hook=runtime_hook.py',  # 添加运行时钩子
            '--add-data=icons;icons',  # 添加图标文件夹
            '--add-data=lang;lang',    # 添加语言文件夹
            '--add-data=aria2c.exe;.', # 添加 aria2c
            '--add-data=LICENSE;.',    # 添加许可证
            '--hidden-import=aria2p',
            '--hidden-import=requests',
            '--hidden-import=bs4',
            '--hidden-import=configparser',
            '--hidden-import=gettext',
            '--hidden-import=PyQt6',
            '--hidden-import=psutil',
            '--hidden-import=signal',
            '--collect-all=PyQt6',
            # 排除 PyQt5
            '--exclude-module=PyQt5',
            'blender_version_manager.py'
        ]
        
        # 执行打包命令
        logging.info("开始执行打包命令...")
        subprocess.check_call(cmd)
        
        logging.info("打包完成！")
        
        # 复制额外文件到 dist 目录
        dist_dir = os.path.join('dist', 'Blender版本管理器')
        logging.info(f"正在复制额外文件到 {dist_dir}...")
        
        for src, dst in additional_files:
            if '*' in src:
                # 处理文件夹
                folder_name = src.split('/')[0]
                dst_folder = os.path.join(dist_dir, dst)
                if not os.path.exists(dst_folder):
                    os.makedirs(dst_folder)
                for file in os.listdir(folder_name):
                    src_file = os.path.join(folder_name, file)
                    if os.path.isfile(src_file):
                        src_file = os.path.join(folder_name, file)
                        if os.path.exists(src_file):
                            dst_path = os.path.join(dist_dir, dst)
                            if not os.path.exists(os.path.dirname(dst_path)):
                                os.makedirs(os.path.dirname(dst_path))
                            if os.path.exists(dst_path):
                                os.remove(dst_path)  # 如果目标文件已存在，先删除
                            shutil.copy2(src_file, dst_path)
                            logging.info(f"已复制: {src_file} -> {dst_path}")
            else:
                # 处理单个文件
                if os.path.exists(src):
                    dst_path = os.path.join(dist_dir, dst)
                    if not os.path.exists(os.path.dirname(dst_path)):
                        os.makedirs(os.path.dirname(dst_path))
                    if os.path.exists(dst_path):
                        os.remove(dst_path)  # 如果目标文件已存在，先删除
                    shutil.copy2(src, dst_path)
                    logging.info(f"已复制: {src} -> {dst_path}")
        
        logging.info("额外文件复制完成！")
        
    except subprocess.CalledProcessError as e:
        logging.error(f"打包过程中出错: {e}")
        raise
    except Exception as e:
        logging.error(f"发生错误: {e}")
        raise

if __name__ == '__main__':
    log_file = setup_logging()
    logging.info("开始打包过程...")
    
    try:
        build_exe()
        logging.info(f"打包成功完成！日志文件��存在: {log_file}")
    except Exception as e:
        logging.error(f"打包失败: {e}")
        sys.exit(1)