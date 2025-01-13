# -*- coding: utf-8 -*-

import os
import configparser
import requests
import zipfile
import io
from bs4 import BeautifulSoup
import threading
import shutil
import time
import subprocess
import gettext
from concurrent.futures import ThreadPoolExecutor
import datetime
import tempfile
import sys
import logging
import aria2p
import atexit
import signal
import locale
import psutil
from PyQt6.QtNetwork import QLocalSocket, QLocalServer

# 设置控制台编码为 UTF-8
if sys.platform == 'win32':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleCP(65001)
    kernel32.SetConsoleOutputCP(65001)
    # 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['LANG'] = 'zh_CN.UTF-8'
    
    # 设置 locale
    try:
        locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'Chinese_China.UTF8')
        except locale.Error:
            pass

# 重定向标准输出和错误输出
try:
    import codecs
    # 检查是否需要重定向
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
except Exception as e:
    print(f"Warning: 无法重定向标准输出: {e}")

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QListWidget, QTabWidget, QMessageBox, QFileDialog,
                            QProgressDialog, QDialog, QCheckBox, QComboBox,
                            QMenuBar, QMenu, QListView, QProgressBar, QTreeWidget,
                            QTextEdit, QInputDialog, QDialogButtonBox, QTreeWidgetItem,
                            QGroupBox, QSpinBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QMetaObject, Q_ARG, pyqtSlot
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPalette

# 配置日志系统
def setup_logging():
    try:
        # 使用绝对路径创建根日志目录
        root_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
        os.makedirs(root_log_dir, exist_ok=True)
        
        # 获取当前日期和创建日志目录
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        existing_dirs = [d for d in os.listdir(root_log_dir) 
                        if os.path.isdir(os.path.join(root_log_dir, d)) and 
                        d.startswith(date_str)]
        increment = len(existing_dirs) + 1
        log_dir_name = f"{date_str}_{increment}"
        log_dir = os.path.join(root_log_dir, log_dir_name)
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置日志文件路径
        vmt_log = os.path.join(log_dir, f"VMT-{log_dir_name}.log")
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s,%(msecs)03d - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 创建VMT日志处理器，添加 BOM 标记
        vmt_handler = logging.FileHandler(
            vmt_log, 
            mode='w',  # 使用 'w' 模式以便写入 BOM
            encoding='utf-8-sig',  # 使用 utf-8-sig 来添加 BOM
            errors='replace'
        )
        vmt_handler.setFormatter(formatter)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)  # 指定输出到 stdout
        console_handler.setFormatter(formatter)
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            if hasattr(handler, 'close'):
                handler.close()
        
        # 添加处理器
        root_logger.addHandler(vmt_handler)
        root_logger.addHandler(console_handler)
        
        # 保存日志相关信息到全局变量
        global CURRENT_LOG_DIR, VMT_LOG_FILE, LOG_DIR_NAME
        CURRENT_LOG_DIR = log_dir
        VMT_LOG_FILE = vmt_log
        LOG_DIR_NAME = log_dir_name
        
        logging.info(f"日志系统已初始化")
        logging.info(f"日志目录: {log_dir}")
        
    except Exception as e:
        print(f"设置日志系统失败: {str(e)}")
        raise

def merge_logs():
    """在程序退出时合并所有日志文件"""
    try:
        # 获取所有需要合并的日志文件
        vmt_log = VMT_LOG_FILE
        aria2c_logs = [f for f in os.listdir(CURRENT_LOG_DIR) if f.startswith('aria2c_')]
        
        # 创建合并后的日志文件
        merged_log = os.path.join(CURRENT_LOG_DIR, f"{LOG_DIR_NAME}.log")
        
        # 读取所有日志条目
        log_entries = []
        
        # 修改时间戳解析
        def parse_timestamp(line):
            try:
                # 处理可能存在的 BOM
                line = line.lstrip('\ufeff')
                # 提取时间戳部分
                timestamp_str = line[:19]  # 获取 "YYYY-MM-DD HH:MM:SS" 部分
                # 确保秒数是两位数
                if len(timestamp_str) == 18:  # 如果秒数只有一位
                    timestamp_str = timestamp_str + '0'
                return datetime.datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except Exception as e:
                logging.error(f"解析时间戳失败: {line[:30]}... - {e}")
                return None

        # 读取VMT日志
        if os.path.exists(vmt_log):
            with open(vmt_log, 'r', encoding='utf-8-sig', errors='replace') as f:
                for line in f:
                    timestamp = parse_timestamp(line)
                    if timestamp:
                        log_entries.append((timestamp, line))
        
        # 读取所有aria2c日志
        for aria2c_log in aria2c_logs:
            log_path = os.path.join(CURRENT_LOG_DIR, aria2c_log)
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                    for line in f:
                        timestamp = parse_timestamp(line)
                        if timestamp:
                            log_entries.append((timestamp, line))
        
        # 按时间戳排序
        log_entries.sort(key=lambda x: x[0])
        
        # 写入合并后的日志文件时添加 BOM
        with open(merged_log, 'w', encoding='utf-8-sig', errors='replace') as f:
            for _, line in log_entries:
                f.write(line)
        
        logging.info(f"日志合并完成: {merged_log}")
        
    except Exception as e:
        logging.error(f"合并日志失败: {e}")

# 添加恢复标准输出和标准错误的函数
def restore_stdout_stderr():
    """恢复标准输出和标准错误"""
    if hasattr(sys, '__stdout__'):
        sys.stdout = sys.__stdout__
    if hasattr(sys, '__stderr__'):
        sys.stderr = sys.__stderr__

# 在程序退出时注册清理函数
atexit.register(restore_stdout_stderr)

# 检查并安装失的库
def check_and_install(package):
    try:
        __import__(package)
    except ImportError:
        logging.info(f"未安装{package}，安装中...")
        print(f"未安装{package}，安���中...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        except Exception as e:
            logging.error(f"安装{package}失败: {e}")
            print(f"安装{package}失败: {e}，如果bpy安装失败，请安装Blender后再使用本软件")

for package in ['bpy', 'requests', 'bs4']:
    check_and_install(package)

# 设置语言环境
LOCALE_DIR = './lang'
DEFAULT_LANGUAGE = 'zh_CN'  # 默认语言

def set_language(language):
    gettext.bindtextdomain('messages', LOCALE_DIR)
    gettext.textdomain('messages')
    lang = gettext.translation('messages', LOCALE_DIR, languages=[language], fallback=True)
    lang.install()
    global _
    _ = lang.gettext

# 获取用户目录路径
USER_DIR = os.path.expanduser("~")
CONFIG_FILE = os.path.join(USER_DIR, "blender_version_manager_config.ini")

set_language(DEFAULT_LANGUAGE)

# 常量定义
ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Blender-VMT [256x256].ico")  # 修复括号
DEFAULT_THEME = 'System'
SOURCE_URL = 'https://mirrors.aliyun.com/blender/release/'
VERSION_MANAGER_NAME = _("Blender 版管理器")
VERSION_MANAGER_VERSION = "v0.1.5"
VERSION_MANAGER_DESCRIPTION = _("一个用于管理 Blender 版本的工具。\n\n本软件完全免费开源、禁止在没有许可的情况下商用。")
VERSION_MANAGER_COPYRIGHT = "(C) 2024 dhjs0000"
VERSION_MANAGER_WEBSITE = "https://space.bilibili.com/430218185"

# 添加全局变量存储 aria2c 进程
ARIA2C_PROCESS = None

def start_aria2c():
    """启动 aria2c 服务"""
    global ARIA2C_PROCESS
    try:
        # 检查 aria2c 是否已经在运行
        aria2c_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aria2c.exe")
        if not os.path.exists(aria2c_path):
            logging.error("找不到 aria2c.exe")
            return False
        
        # 使用当前日志目录创建aria2c日志文件
        aria2c_log = os.path.join(
            CURRENT_LOG_DIR, 
            f'aria2c_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
        
        # 创建全局文件对象，使用 utf-8-sig 编码
        global ARIA2C_LOG_FILE
        ARIA2C_LOG_FILE = open(aria2c_log, 'w', encoding='utf-8-sig')
        
        ARIA2C_PROCESS = subprocess.Popen(
            [aria2c_path, 
             "--enable-rpc", 
             "--rpc-listen-all=true", 
             "--rpc-allow-origin-all",
             f"--log={aria2c_log}",  # 指定日志文件
             "--log-level=debug",     # 设置日志级别
             "--console-log-level=debug"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding='utf-8'
        )
        
        # 创建线程来读取和记录aria2c的输出
        def log_output(pipe, level):
            try:
                for line in pipe:
                    line = line.strip()
                    if line:
                        # 写入到aria2c专用日志文件
                        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ARIA2C_LOG_FILE.write(f"{timestamp} - {line}\n")
                        ARIA2C_LOG_FILE.flush()
                        
                        # 通过logging模块记录到主日志系统
                        if level == logging.ERROR:
                            logging.error(f"Aria2c: {line}")
                        else:
                            logging.info(f"Aria2c: {line}")
            except Exception as e:
                logging.error(f"Aria2c日志记录失败: {e}")
        
        # 启动输出监控线程
        threading.Thread(target=log_output, args=(ARIA2C_PROCESS.stdout, logging.INFO), daemon=True).start()
        threading.Thread(target=log_output, args=(ARIA2C_PROCESS.stderr, logging.ERROR), daemon=True).start()
        
        # 记录启动信息
        startup_msg = f"aria2c 服务已启动，日志文件: {aria2c_log}"
        logging.info(startup_msg)
        ARIA2C_LOG_FILE.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - {startup_msg}\n")
        ARIA2C_LOG_FILE.flush()
        
        return True
        
    except Exception as e:
        error_msg = f"启动 aria2c 服务失败: {e}"
        logging.error(error_msg)
        if 'ARIA2C_LOG_FILE' in globals():
            ARIA2C_LOG_FILE.close()
        return False

def stop_aria2c():
    """停止所有 aria2c 进程"""
    global ARIA2C_PROCESS
    
    try:
        # 使用 psutil 查找并终止所有 aria2c 进程
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'aria2c' in proc.name().lower():
                    proc.terminate()
                    proc.wait(timeout=3)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                try:
                    proc.kill()
                except:
                    pass
        
        # 清理主进程引用
        if ARIA2C_PROCESS:
            try:
                ARIA2C_PROCESS.terminate()
                ARIA2C_PROCESS.wait(timeout=3)
            except:
                try:
                    ARIA2C_PROCESS.kill()
                except:
                    pass
            finally:
                ARIA2C_PROCESS = None
                
    except Exception as e:
        logging.error(f"停止 aria2c 进程失败: {e}")
        raise

class BlenderVersionManager(QMainWindow):
    def __init__(self):
        logging.info("初始化 Blender 版本管理器")
        super().__init__()
        self.setWindowTitle(_("Blender 版本管理器"))
        self.setGeometry(100, 100, 600, 400)
        
        # 先初始化配置
        self.config_file = CONFIG_FILE
        self.config = configparser.ConfigParser()
        self.load_config()
        
        # 然后检测系主题
        self.is_dark_mode = self.check_system_theme()
        
        # 设置窗口图标
        self.setWindowIcon(QIcon(ICON_PATH))
        
        self.init_ui()
        self.apply_theme(self.config.get('PREFERENCES', 'Theme', fallback=DEFAULT_THEME))
        self.center()
        self.show()
    
    def check_system_theme(self):
        # 检查系统是否为深色主题
        if self.config.get('PREFERENCES', 'Theme', fallback='System') == 'Dark':
            return True
        elif self.config.get('PREFERENCES', 'Theme', fallback='System') == 'System':
            # 在 Windows 上检���系统主题
            if sys.platform == 'win32':
                try:
                    import winreg
                    registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                    key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    return value == 0  # 0 表示深色主题
                except Exception as e:
                    logging.error(f"获取系统主题失败: {e}")
                    return False
        return False
    
    def get_themed_icon(self, icon_name):
        # 根据主题返回对应的图标
        if self.config.get('PREFERENCES', 'Theme', fallback='System') == 'Dark':
            # 如果用户明确选择了Dark主题
            theme_folder = "Dark"
        elif self.config.get('PREFERENCES', 'Theme', fallback='System') == 'System':
            # 在 Windows 上检查系统主题
            if sys.platform == 'win32':
                try:
                    import winreg
                    registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                    key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    theme_folder = "Light" if value == 1 else "Dark"
                except Exception as e:
                    logging.error(f"获取系统主题失败: {e}")
                    theme_folder = "Light"
            else:
                # 其他系统默认使用浅色图标
                theme_folder = "Light"
        else:
            # 默认使用Light主题
            theme_folder = "Light"
        
        icon_path = f"icons/{theme_folder}/{icon_name}"
        if not os.path.exists(icon_path):
            icon_path = f"icons/{icon_name}"  # 回退到默认图标
        return QIcon(icon_path)
    
    def center(self):
        # 将窗口居中示
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
    
    def init_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 版本管理标签页
        version_management_widget = QWidget()
        self.init_version_management_ui(version_management_widget)
        tab_widget.addTab(version_management_widget, _("版本管理"))
        
        # 用户设置管理标签页
        user_settings_widget = QWidget()
        self.init_user_settings_ui(user_settings_widget)
        tab_widget.addTab(user_settings_widget, _("用户设置管理"))
        
        # 版本插件管理标签页
        plugin_management_widget = QWidget()
        self.init_plugin_management_ui(plugin_management_widget)
        tab_widget.addTab(plugin_management_widget, _("版本插件管理"))
        
        main_layout.addWidget(tab_widget)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        self.populate_versions()
    
    def create_menu_bar(self):
        # 创建菜单栏
        menubar = self.menuBar()  # 用 self.menuBar() 而不是创建新的 QMenuBar
        
        # 文件菜单
        file_menu = menubar.addMenu(_("文件"))  # 直接添加到菜单栏
        preferences_item = file_menu.addAction(_('偏好设置'))
        preferences_item.triggered.connect(self.open_preferences)
        
        exit_item = file_menu.addAction(_("退出"))
        exit_item.triggered.connect(self.on_exit)
        
        # 帮助菜单
        help_menu = menubar.addMenu(_("帮助"))  # 直接添加到菜单栏
        about_item = help_menu.addAction(_("关于"))
        about_item.triggered.connect(self.on_about)
    
    def on_exit(self, event):
        self.close()
    
    def on_about(self, event):
        QMessageBox.information(self, _("关于"), _("Blender 版本管理器\n版本: 0.1.5"))
    
    def open_preferences(self, event=None):  # 添加默认参数 None
        # 打开偏好设置对话框
        pref_dialog = PreferencesDialog(self, _("偏好设置"), self.config)
        if pref_dialog.exec() == QDialog.DialogCode.Accepted:  # 检查对话框是否被接受
            self.save_config()  # 保存配置
            self.populate_versions()  # 更新版本列表
    
    def init_version_management_ui(self, panel):
        logging.debug("初始化版本管理界面")
        # 创建主布局
        layout = QVBoxLayout(panel)
        
        # 创建按钮工具栏布局
        button_layout = QHBoxLayout()
        
        # 创建并绑定按钮
        self.launch_button = QPushButton()
        self.launch_button.setIcon(self.get_themed_icon("launch.png"))
        self.launch_button.setIconSize(QSize(36, 36))
        self.launch_button.setFixedSize(48, 48)
        self.launch_button.setToolTip(_("启动 Blender"))
        self.launch_button.clicked.connect(self.launch_blender)
        button_layout.addWidget(self.launch_button)
        
        self.add_button = QPushButton()
        self.add_button.setIcon(self.get_themed_icon("add.png"))
        self.add_button.setIconSize(QSize(36, 36))
        self.add_button.setFixedSize(48, 48)
        self.add_button.setToolTip(_("添加 Blender 版本"))
        self.add_button.clicked.connect(self.add_blender_version)
        button_layout.addWidget(self.add_button)
        
        self.edit_button = QPushButton()
        self.edit_button.setIcon(self.get_themed_icon("edit.png"))
        self.edit_button.setIconSize(QSize(36, 36))
        self.edit_button.setFixedSize(48, 48)
        self.edit_button.setToolTip(_("编辑 Blender 版本"))
        self.edit_button.clicked.connect(self.edit_blender_version)
        button_layout.addWidget(self.edit_button)
        
        self.delete_button = QPushButton()
        self.delete_button.setIcon(self.get_themed_icon("delete.png"))
        self.delete_button.setIconSize(QSize(36, 36))
        self.delete_button.setFixedSize(48, 48)
        self.delete_button.setToolTip(_("删除 Blender 版本"))
        self.delete_button.clicked.connect(self.delete_blender_version)
        button_layout.addWidget(self.delete_button)
        
        self.uninstall_button = QPushButton()
        self.uninstall_button.setIcon(self.get_themed_icon("uninstall.png"))
        self.uninstall_button.setIconSize(QSize(36, 36))
        self.uninstall_button.setFixedSize(48, 48)
        self.uninstall_button.setToolTip(_("卸载 Blender 版本"))
        self.uninstall_button.clicked.connect(self.uninstall_blender_version)
        button_layout.addWidget(self.uninstall_button)
        
        self.download_button = QPushButton()
        self.download_button.setIcon(self.get_themed_icon("download.png"))
        self.download_button.setIconSize(QSize(36, 36))
        self.download_button.setFixedSize(48, 48)
        self.download_button.setToolTip(_("下载 Blender 版本"))
        self.download_button.clicked.connect(self.download_blender_version)
        button_layout.addWidget(self.download_button)
        
        self.backup_button = QPushButton()
        self.backup_button.setIcon(self.get_themed_icon("backup.png"))
        self.backup_button.setIconSize(QSize(36, 36))
        self.backup_button.setFixedSize(48, 48)
        self.backup_button.setToolTip(_("备份/还原 Blender 版本"))
        self.backup_button.clicked.connect(self.backup_restore_blender_version)
        button_layout.addWidget(self.backup_button)
        
        # 添加按钮布局到主布局
        layout.addLayout(button_layout)
        
        # 创建版本列表
        self.version_list = QTreeWidget()
        self.version_list.setHeaderLabels([_('Blender 版本'), _('路径')])
        self.version_list.setColumnWidth(0, 150)
        self.version_list.setColumnWidth(1, 400)
        self.version_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.version_list.customContextMenuRequested.connect(self.on_right_click)
        layout.addWidget(self.version_list)
    
    def on_right_click(self, position):
        # 检查是否��选中的项目
        selected_items = self.version_list.selectedItems()
        if not selected_items:
            return
            
        menu = QMenu(self)  # 添加父窗口
        
        # 图标到菜单项
        launch_action = menu.addAction(self.get_themed_icon("launch.png"), _("启动 Blender"))
        edit_action = menu.addAction(self.get_themed_icon("edit.png"), _("编辑 Blender 版本"))
        delete_action = menu.addAction(self.get_themed_icon("delete.png"), _("删除 Blender 版本"))
        uninstall_action = menu.addAction(self.get_themed_icon("uninstall.png"), _("卸载 Blender 版本"))
        backup_action = menu.addAction(self.get_themed_icon("backup.png"), _("备份/还原"))
        
        # 添加分隔线
        menu.addSeparator()
        
        open_location_action = menu.addAction(self.get_themed_icon("folder.png"), _("查看文件所在位置"))
        
        # 连接动作信号
        launch_action.triggered.connect(self.launch_blender)
        edit_action.triggered.connect(self.edit_blender_version)
        delete_action.triggered.connect(self.delete_blender_version)
        uninstall_action.triggered.connect(self.uninstall_blender_version)
        backup_action.triggered.connect(self.backup_restore_blender_version)
        open_location_action.triggered.connect(self.open_file_location)
        
        # 在鼠标位置显示菜单
        menu.exec(self.version_list.viewport().mapToGlobal(position))
    
    def scale_bitmap(self, image_path, target_width, target_height):
        # PyQt6中的图像缩放
        pixmap = QPixmap(image_path)
        return pixmap.scaled(target_width, target_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    
    def apply_theme(self, theme):
        logging.debug(f"应用主题: {theme}")
        if theme == 'Dark':
            # 手动设置深色主题
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: rgb(45, 45, 48);
                    color: rgb(255, 255, 255);
                }
                QPushButton {
                    background-color: rgb(60, 60, 63);
                    border: none;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: rgb(70, 70, 73);
                }
                QTreeWidget {
                    background-color: rgb(30, 30, 33);
                    color: rgb(255, 255, 255);
                    border: 1px solid rgb(60, 60, 63);
                }
                QTreeWidget::item:selected {
                    background-color: rgb(0, 120, 215);
                }
            """)
        else:
            # System 主题：清除所有样式表使用系统原生主题
            self.setStyleSheet("")
    
    def init_user_settings_ui(self, panel):
        logging.debug("初始化用户设置界面")
        # 用户设置管理界面
        layout = QVBoxLayout(panel)
        
        # 添加 Blender 版本选择
        version_label = QLabel(_("选择 Blender 版本:"))
        version_choices = list(self.config['VERSIONS'].keys())
        version_choice = QComboBox()
        version_choice.addItems(version_choices)
        layout.addWidget(version_label)
        layout.addWidget(version_choice)
        
        # 添加用户设置选项
        texture_dir_label = QLabel(_("纹理目录:"))
        texture_dir_text = QLineEdit()
        layout.addWidget(texture_dir_label)
        layout.addWidget(texture_dir_text)
        
        script_dir_label = QLabel(_("脚本目录:"))
        script_dir_text = QLineEdit()
        layout.addWidget(script_dir_label)
        layout.addWidget(script_dir_text)
        
        # 保存按钮
        save_button = QPushButton(_("保存设置"))
        save_button.clicked.connect(lambda: self.save_blender_preferences(
            version_choice.currentText(),
            texture_dir_text.text(),
            script_dir_text.text()
        ))
        layout.addWidget(save_button, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def save_blender_preferences(self, selected_version, texture_directory, script_directory):
        if not selected_version:
            QMessageBox.warning(self, _("警告"), _("请选择一个 Blender 版本。"))
            return
        
        # 获取选定版本的路径
        blender_path = self.config['VERSIONS'].get(selected_version)
        if not blender_path:
            QMessageBox.critical(self, _("错误"), _("找���到选定版本的路径。"))
            return
        
        # 生成 Python 脚本
        script_content = f"""
import bpy

# 访问偏好设置
preferences = bpy.context.preferences
file_paths = preferences.filepaths

# 修改文件路径设置
file_paths.texture_directory = r"{texture_directory}"
file_paths.script_directory = r"{script_directory}"

# 保存用户设置
bpy.ops.wm.save_userpref()
"""
        script_path = os.path.join(tempfile.gettempdir(), "set_blender_preferences.py")
        with open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write(script_content)
        
        # 创建输出对话框
        output_dialog = QDialog(self)
        output_dialog.setWindowTitle(_("Blender 偏好设置输出"))
        output_dialog.resize(600, 400)
        
        layout = QVBoxLayout(output_dialog)
        output_text = QTextEdit()
        output_text.setReadOnly(True)
        layout.addWidget(output_text)
        
        def read_output(process):
            for line in iter(process.stdout.readline, ''):
                output_text.append(line)
            process.stdout.close()
        
        # 通过命令行运行 Blender 脚本并实时获取输出
        process = subprocess.Popen(
            [blender_path, '-b', '--python', script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )
        logging.debug(f"正在运行 Blender 脚本: {blender_path} -b --python {script_path}")
        
        threading.Thread(target=read_output, args=(process,)).start()
        
        output_dialog.exec()
    
    def init_plugin_management_ui(self, panel):
        logging.debug("初始化插件管理界面")
        # 版本插件管理界面
        layout = QVBoxLayout(panel)
        
        # 添加 Blender 版本选择
        version_layout = QHBoxLayout()
        version_label = QLabel(_("选择 Blender 版本:"))
        version_choices = list(self.config['VERSIONS'].keys())
        version_choice = QComboBox()
        version_choice.addItems(version_choices)
        version_choice.currentTextChanged.connect(self.populate_plugins)
        version_layout.addWidget(version_label)
        version_layout.addWidget(version_choice)
        layout.addLayout(version_layout)
        
        # 添加插件模式选择
        mode_layout = QHBoxLayout()
        mode_label = QLabel(_("插件模式:"))
        mode_choice = QComboBox()
        mode_choice.addItems([_("用户"), _("系统")])
        mode_choice.currentTextChanged.connect(lambda: self.populate_plugins(version_choice.currentText(), mode_choice.currentText()))
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(mode_choice)
        layout.addLayout(mode_layout)
        
        # 插件表
        self.plugin_list = QTreeWidget()
        self.plugin_list.setHeaderLabels([_('插件名称'), _('状态')])
        self.plugin_list.setColumnWidth(0, 200)
        self.plugin_list.setColumnWidth(1, 100)
        layout.addWidget(self.plugin_list)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        install_button = QPushButton(_("安装插件"))
        install_button.clicked.connect(lambda: self.install_plugin(
            version_choice.currentText(),
            mode_choice.currentText()
        ))
        button_layout.addWidget(install_button)
        
        uninstall_button = QPushButton(_("卸载插件"))
        uninstall_button.clicked.connect(lambda: self.uninstall_plugin(
            version_choice.currentText(),
            mode_choice.currentText()
        ))
        button_layout.addWidget(uninstall_button)
        
        enable_button = QPushButton(_("启用插件"))
        enable_button.clicked.connect(lambda: self.enable_plugin(
            version_choice.currentText(),
            mode_choice.currentText()
        ))
        button_layout.addWidget(enable_button)
        
        disable_button = QPushButton(_("禁用插件"))
        disable_button.clicked.connect(lambda: self.disable_plugin(
            version_choice.currentText(),
            mode_choice.currentText()
        ))
        button_layout.addWidget(disable_button)
        
        refresh_button = QPushButton(_("刷新列表"))
        refresh_button.clicked.connect(lambda: self.populate_plugins(
            version_choice.currentText(),
            mode_choice.currentText()
        ))
        button_layout.addWidget(refresh_button)
        
        layout.addLayout(button_layout)
    
    def install_plugin(self, selected_version, mode="用户"):
        # 安装插件逻辑
        if not selected_version:
            QMessageBox.warning(self, _("警告"), _("请��择一个 Blender 版本。"))
            return
        
        # 获取选定版本的插件路径
        addon_path = self.get_addon_path(selected_version, mode)
        logging.debug(f"安装插件路径: {addon_path}")
        if not addon_path:
            QMessageBox.critical(self, _("错误"), _("找不到选定版本的插件路径。"))
            return
        
        file_dialog = QFileDialog()
        plugin_file, _ = file_dialog.getOpenFileName(
            self,
            _("选择插件文件"),
            "",
            _("插件文件 (*.zip *.py)")
        )
        
        if plugin_file:
            logging.debug(f"选择的插件文件: {plugin_file}")
            
            if plugin_file.endswith('.zip'):
                # 解压 ZIP 文件到插件目录
                with zipfile.ZipFile(plugin_file, 'r') as zip_ref:
                    zip_ref.extractall(addon_path)
                QMessageBox.information(self, _("信息"), _("插件安装成功。"))
            elif plugin_file.endswith('.py'):
                # 直接复制 .py 文件到插件目录
                shutil.copy(plugin_file, addon_path)
                QMessageBox.information(self, _("信息"), _("插件安装成功。"))
            
            self.populate_plugins(selected_version, mode)
    
    def uninstall_plugin(self, selected_version, mode="用���"):
        # 卸载插件逻辑
        if not selected_version:
            QMessageBox.warning(self, _("警告"), _("请选择一个 Blender 版本。"))
            return
        
        selected_items = self.plugin_list.selectedItems()
        if not selected_items:
            QMessageBox.critical(self, _("错误"), _("请选择一个插件。"))
            return
        
        plugin_name = selected_items[0].text(0)
        addon_path = self.get_addon_path(selected_version, mode)
        plugin_path = os.path.join(addon_path, plugin_name)
        logging.debug(f"卸载插件路径: {plugin_path}")
        
        if os.path.exists(plugin_path):
            shutil.rmtree(plugin_path) if os.path.isdir(plugin_path) else os.remove(plugin_path)
            QMessageBox.information(self, _("信息"), _("插件卸载成功。"))
            self.populate_plugins(selected_version, mode)
        else:
            QMessageBox.critical(self, _("错误"), _("找不到插件文件。"))
    
    def enable_plugin(self, selected_version, mode="用户"):
        selected_items = self.plugin_list.selectedItems()
        if not selected_items:
            QMessageBox.critical(self, _("错误"), _("请选择一个插件。"))
            return
        
        plugin_name = selected_items[0].text(0)
        blender_exe = self.config['VERSIONS'].get(selected_version)
        if not blender_exe or not os.path.exists(blender_exe):
            QMessageBox.critical(self, _("错误"), 
                               _("找不到 {0} 的可执行文件。").format(selected_version))
            return
        
        script_content = f"""
import bpy
bpy.ops.preferences.addon_enable(module="{plugin_name}")
bpy.ops.wm.save_userpref()
"""
        script_path = os.path.join(tempfile.gettempdir(), "enable_plugin.py")
        with open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write(script_content)
        
        try:
            self.run_blender_script(blender_exe, script_path)
            QMessageBox.information(self, _("信息"), _("插件已启用。"))
            self.populate_plugins(selected_version, mode)
        except Exception as e:
            QMessageBox.critical(self, _("错误"), _("启用插件失败: {0}").format(str(e)))
    
    def disable_plugin(self, selected_version, mode="用户"):
        selected_items = self.plugin_list.selectedItems()
        if not selected_items:
            QMessageBox.critical(self, _("错误"), _("请选择一个插件。"))
            return
        
        plugin_name = selected_items[0].text(0)
        blender_exe = self.config['VERSIONS'].get(selected_version)
        if not blender_exe or not os.path.exists(blender_exe):
            QMessageBox.critical(self, _("错误"), 
                               _("找不到 {0} 的可执行文件。").format(selected_version))
            return
        
        script_content = f"""
import bpy
bpy.ops.preferences.addon_disable(module="{plugin_name}")
bpy.ops.wm.save_userpref()
"""
        script_path = os.path.join(tempfile.gettempdir(), "disable_plugin.py")
        with open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write(script_content)
        
        try:
            self.run_blender_script(blender_exe, script_path)
            QMessageBox.information(self, _("信息"), _("插件已禁用。"))
            self.populate_plugins(selected_version, mode)
        except Exception as e:
            QMessageBox.critical(self, _("错误"), _("禁用插件失败: {0}").format(str(e)))

    def load_config(self):
        logging.debug("加载配置文件")
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            logging.warning("配置文件不存在，用默认设置")
        if 'VERSIONS' not in self.config:
            self.config['VERSIONS'] = {}
        if 'PREFERENCES' not in self.config:
            self.config['PREFERENCES'] = {
                'AutoFetch': 'False',
                'FolderPath': '',
                'SourceURL': SOURCE_URL,
                'ThreadCount': '4',
                'Language': DEFAULT_LANGUAGE
            }
        self.save_config()
        set_language(self.config.get('PREFERENCES', 'Language', fallback=DEFAULT_LANGUAGE))

    def save_config(self):
        logging.debug("保存配置文件")
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def launch_blender(self, event=None):
        logging.info("尝试启动 Blender")
        selected_items = self.version_list.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            selected_version = selected_item.text(0)
            logging.info(f"选择的版本: {selected_version}")
            blender_exe = self.config['VERSIONS'].get(selected_version)
            if blender_exe and os.path.exists(blender_exe):
                logging.info(f"启动 Blender: {blender_exe}")
                threading.Thread(target=self.run_blender_with_logging, args=(blender_exe,)).start()
            else:
                logging.error(f"找不到可执行文件: {blender_exe}")
                QMessageBox.critical(self, _("错误"), _("找不到 {0} 的可执行文件。").format(selected_version))
        else:
            logging.warning("未选择 Blender 版本")
            QMessageBox.warning(self, _("警告"), _("请选择一个 Blender 版本。"))

    def run_blender_with_logging(self, blender_exe):
        # 运 Blender 并记录日志
        log_file = os.path.join(os.path.dirname(blender_exe), "blender_log.txt")
        with open(log_file, "w") as log:
            process = subprocess.Popen([blender_exe], stdout=log, stderr=log)
            process.wait()
        # 用 QMetaObject.invokeMethod 在主线程中显示消息框
        QMetaObject.invokeMethod(self, "show_blender_started_message",
                               Qt.ConnectionType.QueuedConnection,
                               Q_ARG(str, log_file))

    @pyqtSlot(str)
    def show_blender_started_message(self, log_file):
        QMessageBox.information(self, _("信息"), 
                              _("Blender 已启动。日志记录在 {0}").format(log_file))

    def add_blender_version(self, event):
        logging.info("开始添加 Blender 版本")
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self,
            _("选择 Blender 可执行文件"),
            "",
            _("Executable files (*.exe)")
        )
        
        if file_path:
            logging.info(f"选择的文件路径: {file_path}")
            version_name, ok = QInputDialog.getText(
                self,
                _("输入名称"),
                _("为此 Blender 版本输入一个名称:")
            )
            if ok and version_name:
                logging.info(f"添加版本: {version_name} -> {file_path}")
                self.config['VERSIONS'][version_name] = file_path
                self.save_config()
                self.populate_versions()
            elif ok:
                logging.warning("版本名称为空")
                QMessageBox.warning(self, _("警告"), _("名称不能为空。"))
        else:
            logging.info("取消添加版本")

    def edit_blender_version(self, event):
        logging.info("开始编辑 Blender 版本")
        selected_items = self.version_list.selectedItems()
        if not selected_items:
            logging.warning("未选择要编辑的版本")
            QMessageBox.critical(self, _("错误"), _("选择一个 Blender 版本。"))
            return
        
        selected_version = selected_items[0].text(0)
        current_path = self.config['VERSIONS'].get(selected_version)
        logging.info(f"编辑版本: {selected_version}, 当前路径: {current_path}")
        
        file_dialog = QFileDialog()
        new_path, _ = file_dialog.getOpenFileName(
            self,
            _("选择新的 Blender 可执行文件"),
            "",
            _("Executable files (*.exe)")
        )
        
        if new_path:
            logging.info(f"更新版本路径: {selected_version} -> {new_path}")
            self.config['VERSIONS'][selected_version] = new_path
            self.save_config()
            self.populate_versions()
            QMessageBox.information(self, _("信息"), _("Blender 版本已更新。"))
        else:
            logging.info("取消编辑版本")

    def delete_blender_version(self, event):
        logging.info("开始删除 Blender 版本")
        selected_items = self.version_list.selectedItems()
        if not selected_items:
            logging.warning("未选择要删除的版本")
            QMessageBox.critical(self, _("错误"), _("请选择一个 Blender 版本。"))
            return
        
        selected_version = selected_items[0].text(0)
        logging.info(f"准备删除版本: {selected_version}")
        
        reply = QMessageBox.question(
            self,
            _("确认删除"),
            _("确定要删除 {0} 吗？").format(selected_version),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            logging.info(f"确认删除版本: {selected_version}")
            del self.config['VERSIONS'][selected_version]
            self.save_config()
            self.populate_versions()
            QMessageBox.information(self, _("信息"), _("Blender 版本已删除。"))
        else:
            logging.info("取消删除版本")

    def uninstall_blender_version(self, event):
        logging.info("开始卸载 Blender 版本")
        selected_items = self.version_list.selectedItems()
        if not selected_items:
            logging.warning("未选择要卸载的版本")
            QMessageBox.critical(self, _("错误"), _("请选择一个 Blender 版本。"))
            return
        
        selected_version = selected_items[0].text(0)
        logging.info(f"准备卸载版本: {selected_version}")
        
        reply = QMessageBox.question(
            self,
            _("确认卸载"),
            _("确定要卸载 {0} 吗？").format(selected_version),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            blender_path = self.config['VERSIONS'].get(selected_version)
            if blender_path and os.path.exists(blender_path):
                logging.info(f"开始卸载: {blender_path}")
                shutil.rmtree(os.path.dirname(blender_path))
                del self.config['VERSIONS'][selected_version]
                self.save_config()
                self.populate_versions()
                logging.info(f"卸载完成: {selected_version}")
                QMessageBox.information(self, _("信息"), _("Blender 版本已卸载。"))
            else:
                logging.error(f"找不到版本路径: {blender_path}")
                QMessageBox.critical(self, _("错误"), _("找不到 {0} 的路径。").format(selected_version))
        else:
            logging.info("取消卸载版本")

    def download_blender_version(self, event):
        logging.info("开始下载 Blender 版本")
        major_versions = self.get_major_versions()
        if not major_versions:
            logging.error("无法获��可用的 Blender 版本列表")
            QMessageBox.critical(self, _("错误"), _("无法获取可用的 Blender 版本列表。"))
            return
        
        logging.info(f"获取到的大版本列表: {major_versions}")
        version_dialog = QDialog(self)
        version_dialog.setWindowTitle(_("选择大版本"))
        layout = QVBoxLayout(version_dialog)
        
        version_list = QListWidget()
        version_list.addItems(major_versions)
        layout.addWidget(version_list)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(version_dialog.accept)
        button_box.rejected.connect(version_dialog.reject)
        layout.addWidget(button_box)
        
        if version_dialog.exec() == QDialog.DialogCode.Accepted and version_list.currentItem():
            major_version = version_list.currentItem().text()
            self.select_minor_version(major_version)

    def select_minor_version(self, major_version):
        minor_versions = self.get_minor_versions(major_version)
        if not minor_versions:
            QMessageBox.critical(self, _("错误"), 
                               _("无法获取 {0} 小版本列表。").format(major_version))
            return
        
        version_dialog = QDialog(self)
        version_dialog.setWindowTitle(_("选择小版本"))
        layout = QVBoxLayout(version_dialog)
        
        version_list = QListWidget()
        version_list.addItems(minor_versions)
        layout.addWidget(version_list)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(version_dialog.accept)
        button_box.rejected.connect(version_dialog.reject)
        layout.addWidget(button_box)
        
        if version_dialog.exec() == QDialog.DialogCode.Accepted and version_list.currentItem():
            minor_version = version_list.currentItem().text()
            self.download_selected_version(major_version, minor_version)

    def download_selected_version(self, major_version, minor_version):
        folder_path = self.config.get('PREFERENCES', 'FolderPath', fallback='')
        source_url = self.config.get('PREFERENCES', 'SourceURL', fallback=SOURCE_URL)
        
        if not os.path.exists(folder_path):
            QMessageBox.critical(self, _("错误"), _("请先设置有效的下载目录。"))
            return
        
        url = f"{source_url}/{major_version}/{minor_version}"
        save_path = os.path.join(folder_path, minor_version)
        
        try:
            # 创建下载对话框
            download_dialog = Aria2DownloadDialog(self, url, save_path)
            
            if download_dialog.exec() == QDialog.DialogCode.Accepted:
                # 下载完成，开始解压
                try:
                    self.extract_blender(save_path, folder_path, minor_version)
                    QMessageBox.information(
                        self,
                        _("成功"),
                        _("Blender {0} 下载并解压成功。").format(minor_version.split('-')[1])
                    )
                    self.populate_versions()
                except Exception as e:
                    logging.error(f"解压失败: {e}")
                    QMessageBox.critical(self, _("错误"), _("解压失败: {0}").format(str(e)))
            
        except Exception as e:
            logging.error(f"下载失败: {e}")
            QMessageBox.critical(self, _("错误"), str(e))

    def get_major_versions(self):
        # 获取大版本列表
        source_url = self.config.get('PREFERENCES', 'SourceURL', fallback=SOURCE_URL)
        try:
            response = requests.get(source_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            versions = [a.text.strip('/') for a in soup.find_all('a') if a.text.startswith('Blender')]
            print(_("获取到的大版本列表: {0}").format(versions))  # 调试信息
            return versions
        except requests.exceptions.RequestException as e:
            print(_("获取本列表失败：{0}").format(e))
            return []
    
    def get_minor_versions(self, major_version):
        # 获取小版本列表
        source_url = self.config.get('PREFERENCES', 'SourceURL', fallback=SOURCE_URL)
        try:
            response = requests.get(f"{source_url}/{major_version}/")
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            versions = [a.text.strip('/') for a in soup.find_all('a') if a.text.startswith(f"blender-{major_version.split('Blender')[-1]}")]
            print(_("获取到的小版本列表: {0}").format(versions))  # 调试信息
            return versions
        except requests.exceptions.RequestException as e:
            print(_("获取版本列表失败：{0}").format(e))
            return []

    def get_addon_path(self, selected_version, mode="用户"):
        # 获取插件路径
        blender_exe = self.config['VERSIONS'].get(selected_version)
        if not blender_exe:
            logging.error(f"找不到 {selected_version} 的可执行文件。")
            return None
        
        blender_dir = os.path.dirname(blender_exe)
        
        if mode == "系统":
            # 系��插件路径在 Blender 安装目录下
            if sys.platform == 'win32':
                # Windows: <blender安装目录>/4.0/scripts/addons
                addon_path = os.path.join(blender_dir, self.get_blender_version(blender_exe), "scripts", "addons")
            else:
                # Linux/Mac: <blender安装目录>/scripts/addons
                addon_path = os.path.join(blender_dir, "scripts", "addons")
        else:
            # 用插件路径
            if sys.platform == 'win32':
                # Windows: %APPDATA%/Blender Foundation/Blender/4.0/scripts/addons
                addon_path = os.path.join(
                    os.getenv('APPDATA'),
                    "Blender Foundation",
                    "Blender",
                    self.get_blender_version(blender_exe),
                    "scripts",
                    "addons"
                )
            elif sys.platform == 'darwin':
                # macOS: ~/Library/Application Support/Blender/4.0/scripts/addons
                addon_path = os.path.expanduser(
                    f"~/Library/Application Support/Blender/{self.get_blender_version(blender_exe)}/scripts/addons"
                )
            else:
                # Linux: ~/.config/blender/4.0/scripts/addons
                addon_path = os.path.expanduser(
                    f"~/.config/blender/{self.get_blender_version(blender_exe)}/scripts/addons"
                )
        
        logging.debug(f"插件路径: {addon_path}")
        os.makedirs(addon_path, exist_ok=True)
        return addon_path

    def get_blender_version(self, blender_exe):
        # 获取 Blender 版本号
        try:
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            result = subprocess.run(
                [blender_exe, '--version'],
                capture_output=True,
                text=True,
                startupinfo=startupinfo,
                encoding='utf-8',
                errors='replace'
            )
            # 输出式类似: "Blender 4.0.2"，我们只需要主版本号，如 "4.0"
            version = result.stdout.split()[1].rsplit('.', 1)[0]  # 获取主版本号 (4.0)
            return version
        except Exception as e:
            logging.error(f"获取 Blender 版本失败: {e}")
            return "unknown"

    def populate_plugins(self, selected_version, mode="用户"):
        # 填充插件列表
        self.plugin_list.clear()
        if not selected_version:
            return
        
        addon_path = self.get_addon_path(selected_version, mode)
        if not addon_path or not os.path.exists(addon_path):
            return
        
        try:
            # 获取已启用的插件列表
            enabled_addons = self.get_enabled_addons(selected_version)
            
            # 获取所有插件
            for item in os.listdir(addon_path):
                item_path = os.path.join(addon_path, item)
                
                # 检查是否为有效的插件
                is_valid_plugin = False
                plugin_name = None
                
                if item.endswith('.py'):
                    # Python 文件形式的插件
                    is_valid_plugin = True
                    plugin_name = item[:-3]
                elif os.path.isdir(item_path):
                    # 文件夹形式的插件，检查是否包含 __init__.py
                    if os.path.exists(os.path.join(item_path, '__init__.py')):
                        is_valid_plugin = True
                        plugin_name = item
                
                if is_valid_plugin:
                    logging.debug(f"找到插件: {plugin_name} ({item}")
                    tree_item = QTreeWidgetItem([item])
                    status = _("已启用") if plugin_name in enabled_addons else _("已禁用")
                    tree_item.setText(1, status)
                    self.plugin_list.addTopLevelItem(tree_item)
                
        except Exception as e:
            logging.error(f"填充插件列表时发生错误: {e}")
            QMessageBox.warning(self, _("警告"), _("获取插件列表失败。"))

    def get_enabled_addons(self, selected_version):
        # 获取已启用的插件列表
        blender_exe = self.config['VERSIONS'].get(selected_version)
        if not blender_exe or not os.path.exists(blender_exe):
            return set()
        
        script_content = """
import bpy
for addon in bpy.context.preferences.addons.keys():
    print(addon)
"""
        script_path = os.path.join(tempfile.gettempdir(), "list_enabled_addons.py")
        with open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write(script_content)
        
        try:
            stdout = self.run_blender_script(blender_exe, script_path)
            # 过滤掉空行
            return set(line.strip() for line in stdout.split('\n') if line.strip())
        except Exception as e:
            logging.error(f"获取已启用插件列表失败: {e}")
            return set()

    def run_blender_script(self, blender_exe, script_path, timeout=10):
        """运行 Blender 脚本并处理输出"""
        try:
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            logging.info(f"运行 Blender 脚本: {blender_exe} --background --python {script_path}")
            process = subprocess.Popen(
                [blender_exe, '--background', '--python', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                
                # 记录输出到日志和控制台
                if stdout:
                    for line in stdout.splitlines():
                        if line.strip():
                            logging.info(f"Blender 输出: {line.strip()}")
                
                if stderr:
                    for line in stderr.splitlines():
                        if line.strip():
                            logging.error(f"Blender 错误: {line.strip()}")
                
                if process.returncode != 0:
                    raise Exception(f"Blender 脚本执行失败，返回码: {process.returncode}")
                
                return stdout
                
            except subprocess.TimeoutExpired:
                process.kill()
                logging.error("Blender 脚本执行超时")
                raise
                
        except Exception as e:
            logging.error(f"运行 Blender 脚时发生错误: {e}")
            raise

    def backup_restore_blender_version(self, event):
        logging.info("开始备份/还原操作")
        selected_items = self.version_list.selectedItems()
        if not selected_items:
            logging.warning("未选择要备份/还原的版本")
            QMessageBox.critical(self, _("错误"), _("请选择一个 Blender 版本。"))
            return
        
        selected_version = selected_items[0].text(0)
        logging.info(f"选择的版本: {selected_version}")
        dialog = BackupRestoreDialog(self, _("备份/还原"), selected_version)
        dialog.exec()
    
    def populate_versions(self):
        logging.info("开始更新版本列表")
        self.version_list.clear()
        versions = list(self.config['VERSIONS'].items())
        logging.info(f"当前版本数量: {len(versions)}")
        for version, path in versions:
            logging.debug(f"添加版本: {version} -> {path}")
            item = QTreeWidgetItem([version, path])
            self.version_list.addTopLevelItem(item)
        logging.info("版本列表更新完成")

    def open_file_location(self, event=None):
        logging.info("尝试打开文件位置")
        selected_items = self.version_list.selectedItems()
        if not selected_items:
            logging.warning("未选择版本")
            return
            
        selected_version = selected_items[0].text(0)
        blender_path = self.config['VERSIONS'].get(selected_version)
        logging.info(f"选择的版本: {selected_version}, 路径: {blender_path}")
        
        if blender_path and os.path.exists(blender_path):
            folder_path = os.path.dirname(blender_path)
            logging.info(f"打开文件夹: {folder_path}")
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', folder_path])
            else:
                subprocess.run(['xdg-open', folder_path])
        else:
            logging.error(f"文件路径不存在: {blender_path}")

    def extract_blender(self, zip_path, folder_path, version_name):
        """解压 Blender 压缩包"""
        logging.info(f"开始解压 Blender: {zip_path}")
        logging.info(f"目标文件夹: {folder_path}")
        logging.info(f"版本名称: {version_name}")
        
        try:
            # 创建解压进度对话框
            progress = QProgressDialog(_("正在解压..."), _("取消"), 0, 100, self)
            progress.setWindowTitle(_("解压进度"))
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            
            # 设置解压目标路径
            extract_path = os.path.join(folder_path, _("Blender {0}").format(version_name.split('-')[1]))
            logging.info(f"解压目标路径: {extract_path}")
            
            # 确保目标路径不存在
            if os.path.exists(extract_path):
                logging.info(f"删除已存在的目标路径: {extract_path}")
                shutil.rmtree(extract_path)
            
            # 解压文件
            with zipfile.ZipFile(zip_path, 'r') as z:
                # 获取总文件数
                total_files = len(z.namelist())
                logging.info(f"压缩包中文件总数: {total_files}")
                progress.setMaximum(total_files)
                
                # 解压每个文件
                for i, member in enumerate(z.namelist()):
                    if progress.wasCanceled():
                        logging.warning("用户取消解压操作")
                        # 如果用户取消，清理已解压的文件
                        shutil.rmtree(extract_path, ignore_errors=True)
                        raise Exception(_("用户取消解压"))
                    
                    logging.debug(f"正在解压: {member} ({i+1}/{total_files})")
                    z.extract(member, extract_path)
                    progress.setValue(i + 1)
                    progress.setLabelText(_("正在解压: {0}").format(member))
            
            # 处理嵌套文件夹
            contents = os.listdir(extract_path)
            if len(contents) == 1 and os.path.isdir(os.path.join(extract_path, contents[0])):
                nested_folder = os.path.join(extract_path, contents[0])
                logging.info(f"处理嵌套文件夹: {nested_folder}")
                # 移动所有文件到上一级
                for item in os.listdir(nested_folder):
                    src = os.path.join(nested_folder, item)
                    dst = os.path.join(extract_path, item)
                    logging.debug(f"移动文件: {src} -> {dst}")
                    shutil.move(src, dst)
                # 删除空文件夹
                logging.debug(f"删除空文件夹: {nested_folder}")
                os.rmdir(nested_folder)
            
            # 查找 blender.exe
            logging.info("开始查找 blender.exe")
            blender_exe = None
            for root, dirs, files in os.walk(extract_path):
                for file in files:
                    if file.lower() == 'blender.exe':
                        blender_exe = os.path.join(root, file)
                        logging.info(f"找到 blender.exe: {blender_exe}")
                        break
                if blender_exe:
                    break
            
            if not blender_exe:
                logging.error("未找到 blender.exe")
                raise Exception(_("找不到 blender.exe"))
            
            # 添加到版本列表
            version_name = _("Blender {0}").format(version_name.split('-')[1])
            logging.info(f"添加版本到配置: {version_name} -> {blender_exe}")
            self.config['VERSIONS'][version_name] = blender_exe
            self.save_config()
            
            # 清理下载的压缩包
            logging.info(f"删除压缩包: {zip_path}")
            os.remove(zip_path)
            
            logging.info("解压完成")
            
        except Exception as e:
            logging.error(f"解压失败: {e}")
            # 确保清理解压目录
            if os.path.exists(extract_path):
                logging.info(f"清理解压目录: {extract_path}")
                shutil.rmtree(extract_path, ignore_errors=True)
            raise

    def perform_backup(self):
        """执行备份操作"""
        try:
            logging.info("开始执行备份操作")
            # 使用临时目录创建 ZIP 文件
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_backup_path = temp_file.name
            logging.info(f"创建临时备份文件: {temp_backup_path}")
            
            # 获取文件总数
            source_dir = os.path.dirname(self.version_path)
            total_files = sum(len(files) for _, _, files in os.walk(source_dir))
            logging.info(f"需要备份的文件总数: {total_files}")
            file_count = 0
            
            with zipfile.ZipFile(temp_backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
                for foldername, subfolders, filenames in os.walk(source_dir):
                    for filename in filenames:
                        if self.progress.wasCanceled():
                            logging.warning("用户取消备份操作")
                            return
                        
                        file_path = os.path.join(foldername, filename)
                        arcname = os.path.relpath(file_path, source_dir)
                        logging.debug(f"正在备份: {arcname} ({file_count+1}/{total_files})")
                        
                        backup_zip.write(file_path, arcname)
                        file_count += 1
                        
                        # 更新进度
                        progress_value = int((file_count / total_files) * 100)
                        QMetaObject.invokeMethod(
                            self.progress, "setValue",
                            Qt.ConnectionType.QueuedConnection,
                            Q_ARG(int, progress_value)
                        )
                        QMetaObject.invokeMethod(
                            self.progress, "setLabelText",
                            Qt.ConnectionType.QueuedConnection,
                            Q_ARG(str, _("已备份: {0}").format(filename))
                        )
            
            # 移动临时文件到最终位置
            final_backup_path = os.path.join(self.backup_folder, f"{self.backup_name}.zip")
            logging.info(f"移动备份文件到最终位置: {final_backup_path}")
            shutil.move(temp_backup_path, final_backup_path)
            
            logging.info("备份完成")
            
            # 在主线程中显示成功消息并更新列表
            QMetaObject.invokeMethod(
                self, "backup_completed",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, self.backup_name)
            )
            
        except Exception as e:
            logging.error(f"备份失败: {e}")
            QMetaObject.invokeMethod(
                self, "backup_failed",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, str(e))
            )

class BackupRestoreDialog(QDialog):
    def __init__(self, parent, title, version_name):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 400)
        
        self.version_name = version_name
        self.backup_folder = parent.config.get('PREFERENCES', 'BackupFolder', fallback='')
        self.version_path = parent.config['VERSIONS'].get(version_name, '')
        
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        # 备份版本选择列表
        self.restore_list = QTreeWidget()
        self.restore_list.setHeaderLabels([_('备份版本')])
        self.restore_list.setColumnWidth(0, 300)
        self.populate_backup_versions()
        layout.addWidget(self.restore_list)
        
        # 右侧控件
        right_layout = QVBoxLayout()
        
        # 备份版本名称���入
        backup_name_label = QLabel(_("备份版本名称:"))
        self.backup_name_text = QLineEdit()
        self.backup_name_text.setText(
            f"{self.version_name}_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        right_layout.addWidget(backup_name_label)
        right_layout.addWidget(self.backup_name_text)
        
        # 按钮
        backup_button = QPushButton(_("备��"))
        backup_button.clicked.connect(self.backup_version)
        right_layout.addWidget(backup_button)
        
        restore_button = QPushButton(_("还原"))
        restore_button.clicked.connect(self.restore_version)
        right_layout.addWidget(restore_button)
        
        delete_button = QPushButton(_("删除备份"))
        delete_button.clicked.connect(self.delete_backup)
        right_layout.addWidget(delete_button)
        
        import_button = QPushButton(_("导入备份"))
        import_button.clicked.connect(self.import_backup)
        right_layout.addWidget(import_button)
        
        export_button = QPushButton(_("导出备份"))
        export_button.clicked.connect(self.export_backup)
        right_layout.addWidget(export_button)
        
        layout.addLayout(right_layout)
    
    def populate_backup_versions(self):
        self.restore_list.clear()
        if not self.backup_folder:
            return
        
        for file in os.listdir(self.backup_folder):
            if file.startswith(self.version_name) and file.endswith('.zip'):
                QTreeWidgetItem(self.restore_list, [file])
    
    def backup_version(self):
        logging.info("开始备份版本")
        if not self.backup_folder:
            logging.error("未设置备份文件夹路径")
            QMessageBox.critical(self, _("错误"), _("请先设置备份文件夹路径。"))
            return
        
        if not os.path.exists(self.version_path):
            logging.error(f"版本路径无效: {self.version_path}")
            QMessageBox.critical(self, _("错误"), _("版本路径无效。"))
            return
        
        backup_name = self.backup_name_text.text()
        final_backup_path = os.path.join(self.backup_folder, f"{backup_name}.zip")
        logging.info(f"备份路径: {final_backup_path}")
        
        # 创建进度对话框（在主线程中）
        progress = QProgressDialog(_("正在备份..."), _("取消"), 0, 100, self)
        progress.setWindowTitle(_("备份进度"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        def perform_backup():
            try:
                # ��用临时目录创��� ZIP 文件
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_backup_path = temp_file.name
                
                # 获取文件总数
                total_files = sum(len(files) for _, _, files in os.walk(os.path.dirname(self.version_path)))
                file_count = 0
                
                with zipfile.ZipFile(temp_backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
                    for foldername, subfolders, filenames in os.walk(os.path.dirname(self.version_path)):
                        for filename in filenames:
                            if progress.wasCanceled():
                                return
                            file_path = os.path.join(foldername, filename)
                            arcname = os.path.relpath(file_path, os.path.dirname(self.version_path))
                            backup_zip.write(file_path, arcname)
                            file_count += 1
                            # 使用信号更新进度
                            progress_value = int((file_count / total_files) * 100)
                            QMetaObject.invokeMethod(progress, "setValue",
                                                   Qt.ConnectionType.QueuedConnection,
                                                   Q_ARG(int, progress_value))
                            QMetaObject.invokeMethod(progress, "setLabelText",
                                                   Qt.ConnectionType.QueuedConnection,
                                                   Q_ARG(str, _("已备份: {0}").format(filename)))
                
                # 移动压缩文件到备份文件夹
                shutil.move(temp_backup_path, final_backup_path)
                
                # 在主线程中显示成功消息并更新列表
                QMetaObject.invokeMethod(self, "backup_completed",
                                       Qt.ConnectionType.QueuedConnection,
                                       Q_ARG(str, backup_name))
                
            except Exception as e:
                logging.error(f"备份失败: {e}")
                QMetaObject.invokeMethod(self, "backup_failed",
                                       Qt.ConnectionType.QueuedConnection,
                                       Q_ARG(str, str(e)))
        
        # 在新线程中执行备份
        threading.Thread(target=perform_backup).start()
    
    @pyqtSlot(str)
    def backup_completed(self, backup_name):
        QMessageBox.information(self, _("信息"), _("备份 {0} 成功。").format(backup_name))
        self.populate_backup_versions()
    
    @pyqtSlot(str)
    def backup_failed(self, error_message):
        QMessageBox.critical(self, _("错误"), _("备份失败: {0}").format(error_message))
    
    def restore_version(self):
        logging.info("开始还原版本")
        if not self.backup_folder:
            logging.error("未设置备份文件夹路径")
            QMessageBox.critical(self, _("错误"), _("请先设置备份文件夹路径。"))
            return
        
        selected_items = self.restore_list.selectedItems()
        if not selected_items:
            logging.warning("未选择要还原的备份版本")
            QMessageBox.critical(self, _("错误"), _("请选择一个备份版本。"))
            return
        
        selected_backup = selected_items[0].text(0)
        backup_path = os.path.join(self.backup_folder, selected_backup)
        logging.info(f"还原备份文件: {backup_path}")
        if not os.path.exists(backup_path):
            QMessageBox.critical(self, _("错误"), _("找不到备份文件 {0}。").format(backup_path))
            return
        
        def perform_restore():
            # 清目标目录
            for root, dirs, files in os.walk(os.path.dirname(self.version_path)):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    shutil.rmtree(os.path.join(root, dir))
            
            with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                # 创建进度对话框
                total_files = len(backup_zip.namelist())
                progress = QProgressDialog(_("正在还原..."), _("取消"), 0, total_files, self)
                progress.setWindowTitle(_("还原进度"))
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                
                for i, file in enumerate(backup_zip.namelist()):
                    if progress.wasCanceled():
                        return
                    backup_zip.extract(file, os.path.dirname(self.version_path))
                    progress.setValue(i + 1)
                    progress.setLabelText(_("已还原: {0}").format(file))
            
            QMessageBox.information(self, _("信息"), _("还原 {0} 成功。").format(selected_backup))
        
        # 在新线程中执行还原
        threading.Thread(target=perform_restore).start()
    
    def delete_backup(self):
        selected_items = self.restore_list.selectedItems()
        if not selected_items:
            QMessageBox.critical(self, _("错误"), _("请选择一个备份版本。"))
            return
        
        selected_backup = selected_items[0].text(0)
        backup_path = os.path.join(self.backup_folder, selected_backup)
        if os.path.exists(backup_path):
            os.remove(backup_path)
            QMessageBox.information(self, _("信息"), _("删除备份 {0} 成功。").format(selected_backup))
            self.populate_backup_versions()
        else:
            QMessageBox.critical(self, _("错误"), _("找不到备份文件 {0}。").format(backup_path))
    
    def import_backup(self):
        file_dialog = QFileDialog()
        backup_path, _ = file_dialog.getOpenFileName(
            self,
            _("选择备份文件"),
            "",
            _("ZIP files (*.zip)")
        )
        
        if backup_path:
            shutil.copy(backup_path, self.backup_folder)
            QMessageBox.information(self, _("信息"), 
                                  _("导入备份 {0} 成功。").format(os.path.basename(backup_path)))
            self.populate_backup_versions()
    
    def export_backup(self):
        selected_items = self.restore_list.selectedItems()
        if not selected_items:
            QMessageBox.critical(self, _("错误"), _("请选择一个备份版本。"))
            return
        
        selected_backup = selected_items[0].text(0)
        backup_path = os.path.join(self.backup_folder, selected_backup)
        
        file_dialog = QFileDialog()
        export_path, _ = file_dialog.getSaveFileName(
            self,
            _("保存备份文件"),
            selected_backup,
            _("ZIP files (*.zip)")
        )
        
        if export_path:
            shutil.copy(backup_path, export_path)
            QMessageBox.information(self, _("信息"), 
                                  _("导出备份 {0} 成功。").format(selected_backup))
    
    def populate_backup_versions(self):
        self.restore_list.clear()
        if not self.backup_folder:
            return
        
        for file in os.listdir(self.backup_folder):
            if file.startswith(self.version_name) and file.endswith('.zip'):
                QTreeWidgetItem(self.restore_list, [file])

class PreferencesDialog(QDialog):
    def __init__(self, parent, title, config):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(500, 400)
        
        self.config = config
        self.init_ui()
    
    def init_ui(self):
        notebook = QTabWidget(self)
        
        # 常规选项卡
        general_panel = QWidget(notebook)
        notebook.addTab(general_panel, _("常规"))
        
        general_layout = QVBoxLayout(general_panel)
        
        # 自动获取选项
        auto_fetch_var = QCheckBox(_("自动获取文件夹 Blender 版本列表"))
        auto_fetch_var.setChecked(self.config.getboolean('PREFERENCES', 'AutoFetch', fallback=False))
        general_layout.addWidget(auto_fetch_var)
        
        # 文件夹路径设置
        folder_group = QGroupBox(_("文件夹路径设置"))
        folder_layout = QVBoxLayout()
        
        folder_path_layout = QHBoxLayout()
        folder_path = QLineEdit()
        folder_path.setText(self.config.get('PREFERENCES', 'FolderPath', fallback=''))
        browse_button = QPushButton(_("浏览"))
        browse_button.clicked.connect(lambda: self.browse_folder(folder_path))
        folder_path_layout.addWidget(folder_path)
        folder_path_layout.addWidget(browse_button)
        folder_layout.addLayout(folder_path_layout)
        
        backup_folder_layout = QHBoxLayout()
        backup_folder = QLineEdit()
        backup_folder.setText(self.config.get('PREFERENCES', 'BackupFolder', fallback=''))
        backup_browse_button = QPushButton(_("浏览"))
        backup_browse_button.clicked.connect(lambda: self.browse_folder(backup_folder))
        backup_folder_layout.addWidget(backup_folder)
        backup_folder_layout.addWidget(backup_browse_button)
        folder_layout.addLayout(backup_folder_layout)
        
        folder_group.setLayout(folder_layout)
        general_layout.addWidget(folder_group)
        
        # 下载设置
        download_group = QGroupBox(_("下载设置"))
        download_layout = QVBoxLayout()
        
        source_url_layout = QHBoxLayout()
        source_url_label = QLabel(_("下载源:"))
        source_url = QLineEdit()
        source_url.setText(self.config.get('PREFERENCES', 'SourceURL', fallback=SOURCE_URL))
        source_url_layout.addWidget(source_url_label)
        source_url_layout.addWidget(source_url)
        download_layout.addLayout(source_url_layout)
        
        thread_count_layout = QHBoxLayout()
        thread_count_label = QLabel(_("下载线程数:"))
        thread_count = QSpinBox()
        thread_count.setRange(1, 32)
        thread_count.setValue(self.config.getint('PREFERENCES', 'ThreadCount', fallback=4))
        thread_count_layout.addWidget(thread_count_label)
        thread_count_layout.addWidget(thread_count)
        download_layout.addLayout(thread_count_layout)
        
        download_group.setLayout(download_layout)
        general_layout.addWidget(download_group)
        
        # 主题选择
        theme_layout = QHBoxLayout()
        theme_label = QLabel(_("主题选择:"))
        theme_choice = QComboBox()
        theme_choice.addItems([_("System"), _("Dark")])
        theme_choice.setCurrentText(self.config.get('PREFERENCES', 'Theme', fallback='System'))
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(theme_choice)
        general_layout.addLayout(theme_layout)
        
        # 语言选择
        language_layout = QHBoxLayout()
        language_label = QLabel(_("语言:"))
        language_choice = QComboBox()
        language_choice.addItems(['zh_CN', 'en_US'])
        language_choice.setCurrentText(self.config.get('PREFERENCES', 'Language', fallback=DEFAULT_LANGUAGE))
        language_layout.addWidget(language_label)
        language_layout.addWidget(language_choice)
        general_layout.addLayout(language_layout)
        
        # 确认按钮
        button_layout = QHBoxLayout()
        save_button = QPushButton(_("保存"))
        save_button.clicked.connect(lambda: self.save_preferences(
            auto_fetch_var.isChecked(),
            folder_path.text(),
            backup_folder.text(),
            source_url.text(),
            thread_count.value(),
            theme_choice.currentText(),
            language_choice.currentText()
        ))
        button_layout.addWidget(save_button)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(notebook)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def browse_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(
            self,
            _("选择文件夹"),
            line_edit.text()
        )
        if folder:
            line_edit.setText(folder)
    
    def save_preferences(self, auto_fetch, folder_path, backup_folder, source_url, 
                        thread_count, theme, language):
        # 保存所有设置
        self.config['PREFERENCES'].update({
            'AutoFetch': str(auto_fetch),
            'FolderPath': folder_path,
            'BackupFolder': backup_folder,
            'SourceURL': source_url,
            'ThreadCount': str(thread_count),
            'Theme': theme,
            'Language': language
        })
        
        # 立即应用主题
        self.parent().apply_theme(theme)
        
        # 如果语言改变了，提示需要重启
        if language != self.config.get('PREFERENCES', 'Language', fallback=DEFAULT_LANGUAGE):
            QMessageBox.information(
                self,
                _("提示"),
                _("语言设置将在重启程序后生效。")
            )
        
        self.accept()

class Aria2DownloadDialog(QDialog):
    def __init__(self, parent, url, save_path):
        super().__init__(parent)
        self.setWindowTitle(_("下载进度"))
        self.resize(500, 400)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        
        self.url = url
        self.save_path = save_path
        self.is_running = True
        self.download = None
        self.update_thread = None
        
        # 初始化 aria2
        try:
            self.aria2 = aria2p.API(
                aria2p.Client(
                    host="http://localhost",
                    port=6800,
                    secret="",
                    timeout=30  # 增加超时时间到30秒
                )
            )
            # 设置全局选项
            self.aria2.set_global_options({
                'connect-timeout': '60',  # 连接超时时间
                'timeout': '60',  # 超时时间
                'stream-piece-selector': 'geom',  # 使用几何选择器
                'disk-cache': '64M',  # 磁盘缓存大小
                'file-allocation': 'none',  # 禁用文件预分配
                'max-concurrent-downloads': '1',  # 最大同时下载数
                'max-connection-per-server': '16',  # 每个服务器最大连接数
                'min-split-size': '1M',  # 最小分片大小
                'split': '16',  # 分片数
                'max-tries': '0',  # 无限重试
                'retry-wait': '3',  # 重试等待时间
                'max-file-not-found': '10'  # 文件未找到最大次数
            })
        except Exception as e:
            logging.error(f"初始化 aria2 失败: {e}")
            QMessageBox.critical(self, _("错误"), _("初始化下载服务失败"))
            self.reject()
            return
        
        self.init_ui()
        self.start_download()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 总体进度
        total_group = QGroupBox(_("总体进度"))
        total_layout = QVBoxLayout()
        
        self.total_progress = QProgressBar()
        self.total_progress.setRange(0, 100)
        total_layout.addWidget(self.total_progress)
        
        self.total_info = QLabel()
        total_layout.addWidget(self.total_info)
        
        self.speed_label = QLabel()
        total_layout.addWidget(self.speed_label)
        
        total_group.setLayout(total_layout)
        layout.addWidget(total_group)
        
        # 下载日志
        log_group = QGroupBox(_("下载日志"))
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # 取消按钮
        self.cancel_button = QPushButton(_("取消"))
        self.cancel_button.clicked.connect(self.cancel_download)
        layout.addWidget(self.cancel_button)
    
    def start_download(self):
        try:
            # 添加下载任务，设置请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': self.url
            }
            
            # 添加下载任务
            self.download = self.aria2.add_uris(
                [self.url],
                options={
                    'dir': os.path.dirname(self.save_path),
                    'out': os.path.basename(self.save_path),
                    'split': '16',  # 分片数
                    'max-connection-per-server': '16',  # 最大连接数
                    'min-split-size': '1M',  # 最小分片大小
                    'header': [f"{k}: {v}" for k, v in headers.items()],
                    'log': '-',
                    'log-level': 'notice',
                    'summary-interval': '0.1',
                    'console-log-level': 'notice',
                    'bt-max-peers': '0',
                    'bt-tracker': [],
                    'seed-time': '0',
                    'check-integrity': 'false',
                    'realtime-chunk-checksum': 'false',
                    'connect-timeout': '10',  # 连接超时
                    'timeout': '10',  # 超时
                    'max-tries': '10',  # 最大重试次数
                    'retry-wait': '3',  # 重试等待时间
                    'max-file-not-found': '5',  # 文件未找到最大次数
                    'max-resume-failure-tries': '5',  # 断点续传失败最大重试次数
                    'auto-file-renaming': 'false',  # 禁用自动重命名
                    'allow-overwrite': 'true',  # 允许覆盖
                    'file-allocation': 'none',  # 禁用文件预分配
                    'async-dns': 'false'  # 禁用异步DNS
                }
            )
            
            # 启动进度更新线程
            self.update_thread = threading.Thread(target=self.update_progress)
            self.update_thread.daemon = True
            self.update_thread.start()
            
            self.append_log(f"开始下载: {self.url}")
            self.append_log(f"保存到: {self.save_path}")
            
        except Exception as e:
            logging.error(f"启动下载失败: {e}")
            self.append_log(f"启动下载失败: {e}")
            QMessageBox.critical(self, _("错误"), str(e))
            self.reject()
    
    def append_log(self, message):
        """添加日志到日志框"""
        self.log_text.append(f"{datetime.datetime.now().strftime('%H:%M:%S')} - {message}")
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    @pyqtSlot(object)
    def update_ui(self, download):
        try:
            # 更新总进度
            progress = download.progress
            self.total_progress.setValue(int(progress))
            
            # 更新总体信息
            total_length = self.format_size(download.total_length)
            completed_length = self.format_size(download.completed_length)
            self.total_info.setText(
                _("已下载: {0} / {1} ({2}%)").format(
                    completed_length,
                    total_length,
                    int(progress)
                )
            )
            
            # 更新速度信息
            speed = self.format_size(download.download_speed)
            eta = self.format_time((download.total_length - download.completed_length) / download.download_speed if download.download_speed > 0 else 0)
            self.speed_label.setText(_("下载速度: {0}/s (剩余时间: {1})").format(speed, eta))
            
            # 更新日志
            if hasattr(download, 'info') and download.info:
                self.append_log(download.info)
        
        except Exception as e:
            logging.error(f"更新UI失败: {e}")
    
    @staticmethod
    def format_time(seconds):
        """格式化时间"""
        if seconds < 60:
            return _("{0}秒").format(int(seconds))
        elif seconds < 3600:
            return _("{0}分{1}秒").format(int(seconds / 60), int(seconds % 60))
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return _("{0}时{1}分").format(hours, minutes)
    
    def update_progress(self):
        """更新下载进度的线程函数"""
        last_update = 0
        retry_count = 0
        max_retries = 5
        
        while self.is_running:
            try:
                if not self.download:
                    time.sleep(0.05)
                    continue
                
                current_time = time.time()
                if current_time - last_update < 0.5:  # 降低更新频率到0.5秒
                    time.sleep(0.1)
                    continue
                
                self.download.update()
                last_update = current_time
                retry_count = 0  # 重置重试计数
                
                # 在主线程中更新UI
                QMetaObject.invokeMethod(
                    self,
                    "update_ui",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(object, self.download)
                )
                
                # 修改完成判断条件
                if self.download.is_complete or (
                    self.download.total_length > 0 and 
                    self.download.completed_length >= self.download.total_length
                ):
                    self.is_running = False
                    self.append_log("下载完成")
                    QMetaObject.invokeMethod(self, "accept", Qt.ConnectionType.QueuedConnection)
                    break
                elif self.download.has_failed or self.download.status == 'error':
                    self.is_running = False
                    error_msg = self.download.error_message or "下载失败"
                    self.append_log(f"下载失败: {error_msg}")
                    QMetaObject.invokeMethod(
                        self,
                        "show_error",
                        Qt.ConnectionType.QueuedConnection,
                        Q_ARG(str, error_msg))
                    break
                
            except Exception as e:
                logging.error(f"更新进度失败: {e}")
                self.append_log(f"更新进度失败: {e}")
                retry_count += 1
                
                if retry_count >= max_retries:
                    self.append_log("达到最大重试次数，停止下载")
                    self.is_running = False
                    QMetaObject.invokeMethod(
                        self,
                        "show_error",
                        Qt.ConnectionType.QueuedConnection,
                        Q_ARG(str, "连接超时，请检查网络连接"))
                    break
                
                time.sleep(1)  # 错误后等待1秒再重试
    
    def cancel_download(self):
        """取消下载"""
        try:
            self.append_log("正在取消下载...")
            self.is_running = False
            
            if self.download:
                try:
                    # 先暂停下载
                    self.download.pause()
                    time.sleep(0.1)  # 等待暂停完成
                    # 然后移除下载
                    self.download.remove(force=True)
                except Exception as e:
                    logging.error(f"取消下载任务失败: {e}")
            
            # 等待更新线程结束
            if self.update_thread and self.update_thread.is_alive():
                self.update_thread.join(timeout=2.0)
            
            # 清理下载文件
            try:
                if os.path.exists(self.save_path):
                    os.remove(self.save_path)
            except Exception as e:
                logging.error(f"清理下载文件失败: {e}")
            
            self.append_log("下载已取消")
            
        except Exception as e:
            logging.error(f"取消下载过程中发生错误: {e}")
        finally:
            self.reject()
    
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        try:
            self.is_running = False
            self.cancel_download()
            
            # 等待更新线程结束
            if self.update_thread and self.update_thread.is_alive():
                self.update_thread.join(timeout=2.0)
            
            # 如果线程仍在运行，强制结束
            if self.update_thread and self.update_thread.is_alive():
                logging.warning("强制结束更新线程")
                # Python 不支持直接终止线程，但我们已经设置了 is_running 标志
        except Exception as e:
            logging.error(f"关闭窗口时发生错误: {e}")
        finally:
            event.accept()
    
    @pyqtSlot(str)
    def show_error(self, error_message):
        """显示错误消息"""
        QMessageBox.critical(self, _("错误"), error_message)
        self.reject()
    
    @staticmethod
    def format_size(size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

def download_file_part(url, start, end, thread_id, progress_callback):
    headers = {'Range': f'bytes={start}-{end}'}
    try:
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()  # 检查响应态
        
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                downloaded += len(chunk)
                # 计算总大小
                total = end - start + 1
                progress_callback(thread_id, downloaded, total, len(chunk))
                yield chunk
    except Exception as e:
        logging.error(f"线程 {thread_id} 下载失败: {e}")
        raise

def check_encoding():
    """检查系统编码设置"""
    logging.info(f"系统默认编码: {sys.getdefaultencoding()}")
    logging.info(f"文件系统编码: {sys.getfilesystemencoding()}")
    
    # 安全地获取标准输出编码
    try:
        stdout_encoding = getattr(sys.stdout, 'encoding', None)
        if stdout_encoding is None:
            stdout_encoding = locale.getpreferredencoding()
        logging.info(f"标准输出编码: {stdout_encoding}")
    except Exception as e:
        logging.warning(f"无法获取标准输出编码: {e}")
    
    # 安全地获取标准错误编码
    try:
        stderr_encoding = getattr(sys.stderr, 'encoding', None)
        if stderr_encoding is None:
            stderr_encoding = locale.getpreferredencoding()
        logging.info(f"标准错误编码: {stderr_encoding}")
    except Exception as e:
        logging.warning(f"无法获取标准错误编码: {e}")
    
    # 获取当前语言环境
    try:
        current_locale = locale.getlocale()
        logging.info(f"当前语言环境: {current_locale}")
    except Exception as e:
        logging.warning(f"无法获取当前语言环境: {e}")
    
    # 获取首选编码
    try:
        preferred_encoding = locale.getpreferredencoding()
        logging.info(f"首选编码: {preferred_encoding}")
    except Exception as e:
        logging.warning(f"无法获取首选编码: {e}")

# 在文件开头添加全局变量
CLEANUP_LOCK = threading.Lock()
CLEANUP_DONE = False

# 修改 cleanup 函数
def cleanup():
    global CLEANUP_DONE
    with CLEANUP_LOCK:
        if CLEANUP_DONE:
            return
        CLEANUP_DONE = True
        
    logging.info("开始清理程序...")
    
    # 确保停止所有 aria2c 进程
    try:
        stop_aria2c()
    except Exception as e:
        logging.error(f"停止 aria2c 失败: {e}")
    
    # 终止所有可能残留的 Blender 进程
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'blender' in proc.name().lower():
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        logging.error(f"清理 Blender 进程失败: {e}")
    
    # 合并日志
    try:
        merge_logs()
    except Exception as e:
        logging.error(f"合并日志失败: {e}")
    
    logging.info("程序清理完成")

# 修改主程序入口
if __name__ == "__main__":
    try:
        # 首先创建 QApplication 实例
        app = QApplication([])
        app.setApplicationName("BlenderVersionManager")
        
        # 检查是否已经有实例在运行
        socket = QLocalSocket()
        socket.connectToServer("BlenderVersionManagerLock")
        
        if socket.waitForConnected(500):
            QMessageBox.warning(None, "警告", "程序已经在运行！")
            socket.disconnectFromServer()
            sys.exit(1)
        
        # 创建服务器以阻止其他实例启动
        server = QLocalServer()
        server.removeServer("BlenderVersionManagerLock")
        server.listen("BlenderVersionManagerLock")
        
        # 初始化日志系统
        setup_logging()
        
        # 启动 aria2c 服务
        if not start_aria2c():
            logging.error("启动 aria2c 服务失败")
            QMessageBox.critical(None, _("错误"), 
                               _("启动 aria2c 服务失败，下载功能可能无法使用。"))
        
        # 创建并显示主窗口
        frame = BlenderVersionManager()
        frame.show()
        
        # 注册清理函数
        atexit.register(cleanup)
        
        # 注册信号处理
        def signal_handler(signum, frame):
            logging.info(f"收到信号 {signum}，开始清理...")
            cleanup()
            sys.exit(0)
        
        # 注册信号处理器
        if sys.platform != 'win32':
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        
        # 运行程序
        exit_code = app.exec()
        
        # 主动调用清理
        cleanup()
        
        sys.exit(exit_code)
        
    except Exception as e:
        logging.error(f"程序运行出错: {e}")
        cleanup()
        sys.exit(1)