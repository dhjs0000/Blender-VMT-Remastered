import os
import sys

def runtime_hook():
    # 确保正确设置工作目录
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        os.chdir(application_path)
        
        # 添加必要的环境变量
        os.environ['PATH'] = application_path + os.pathsep + os.environ.get('PATH', '')