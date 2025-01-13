#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from datetime import datetime
import polib

def setup_logging():
    """设置日志系统"""
    log_dir = 'log'
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'compile_mo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def compile_po_files():
    """编译所有的 .po 文件为 .mo 文件"""
    logging.info("开始编译 .mo 文件")
    
    # 查找所有语言目录
    lang_dir = 'lang'
    if not os.path.exists(lang_dir):
        logging.error(f"找不到语言目录: {lang_dir}")
        return False
    
    success_count = 0
    error_count = 0
    
    for root, dirs, files in os.walk(lang_dir):
        for file in files:
            if file.endswith('.po'):
                po_path = os.path.join(root, file)
                # 使用相同目录的 messages.mo
                mo_path = os.path.join(os.path.dirname(po_path), 'messages.mo')
                
                try:
                    logging.info(f"正在编译: {po_path} -> {mo_path}")
                    
                    # 使用 polib 编译 .po 文件
                    po = polib.pofile(po_path)
                    po.save_as_mofile(mo_path)
                    
                    logging.info(f"编译成功: {mo_path}")
                    success_count += 1
                        
                except Exception as e:
                    logging.error(f"处理文件时出错: {po_path}")
                    logging.error(f"错误信息: {str(e)}")
                    error_count += 1
    
    logging.info(f"编译完成: 成功 {success_count} 个, 失败 {error_count} 个")
    return error_count == 0

def main():
    """主函数"""
    setup_logging()
    logging.info("=== 开始编译语言文件 ===")
    
    try:
        # 检查是否安装了 polib
        try:
            import polib
        except ImportError:
            logging.error("未找到 polib 库，正在安装...")
            import subprocess
            subprocess.check_call(['pip', 'install', 'polib'])
            logging.info("polib 安装成功")
            
        # 编译所有 .po 文件
        if compile_po_files():
            logging.info("所有文件编译成功")
            return 0
        else:
            logging.error("部分文件编译失败")
            return 1
            
    except Exception as e:
        logging.error(f"程序执行出错: {str(e)}")
        return 1
    finally:
        logging.info("=== 编译过程结束 ===")

if __name__ == "__main__":
    exit(main()) 