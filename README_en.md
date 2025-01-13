#Blender Version Management Tool

<div align="center">

![Logo](icons/Blender-VMT%20%5B256x256%5D.ico)

[![License](https://img.shields.io/badge/license-GPL3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyQt](https://img.shields.io/badge/PyQt-6.0+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Platform](https://img.shields.io/badge/platform-Windows%20|%20Linux%20|%20macOS-lightgrey.svg)](https://github.com/your-username/blender-version-manager)

[Simplified Chinese] (README. md) | [English] (README-en. md)

A powerful Blender version management tool that supports downloading, installing, switching, and managing multiple versions.

</div>

##  📑  catalogue

-[Feature] (# - Feature)
-[Installation Guide] (# - Installation Guide)
-[System Requirements] (# System Requirements)
-[Installation Steps] (# Installation Steps)
-[Install from Source Code] (# Install from Source Code)
-[Quick Start] (# - Quick Start)
-[User Guide] (# - User Guide)
-[Interface Overview] (# Interface Overview)
-[Basic Operations] (# Basic Operations)
-[Advanced Features] (# Advanced Features)
-[Configuration Description] (# - Configuration Description)
-[Multilingual Support] (# - Multilingual Support)
-[Theme Setting] (# - Theme Setting)
-[Frequently Asked Questions] (# - Frequently Asked Questions)
-[Developer's Guide] (# - Developer's Guide)
-[Project Structure] (# Project Structure)
-[Development Environment Settings] (# Development Environment Settings)
-[Construction Instructions] (# Construction Instructions)
-[Testing Guide] (# Testing Guide)
-[Contribution Guide] (# Contribution Guide)
-[Update Log] (# - Update Log)
-[Technical Architecture] (# - Technical Architecture)
-[License] (# - License)
-[Acknowledgements] (# - Acknowledgements)

##  ✨  characteristic

###Core functions
-  🚀  Automatically detect and manage multiple Blender versions
-  📥  Support online download of various versions of Blender
-  🔄  Quickly switch between different versions
-  💾  Automatically backup and restore user configurations
-  🌐  Multi language interface support
-  🎨  Dark/Light Theme Switching
-  📊  Version usage statistics
-  🔍  Intelligent version search
-  🛠️  Configuration file management

###Advanced features
-  🔒  Secure configuration file storage
-  🌍  Global download source support
-  📦  Portable version support
-  🔄  Incremental update support
-  🎮  Plugin management function
-  📋  Detailed operation log
-  ⚡  Multi threaded download acceleration
-  🔧  Customize installation path
-  📱  Responsive interface design

##  🚀  Installation Guide

###System requirements

#### Windows
-Windows 10/11 64 bit
- Python 3.8+
- 4GB+ RAM
-1GB+available disk space

#### Linux
- Ubuntu 20.04+/Fedora 34+
- Python 3.8+
- 4GB+ RAM
-1GB+available disk space

#### macOS
- macOS 10.15+
- Python 3.8+
- 4GB+ RAM
-1GB+available disk space

###Installation steps

1. Download the latest released version
```bash
git clone  https://github.com/your-username/blender-version-manager.git
cd blender-version-manager
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Run the program
```bash
python blender_version_manager.py
```

###Install from source code

1. Clone repository
```bash
git clone  https://github.com/your-username/blender-version-manager.git
```

2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. Installation and development dependencies
```bash
pip install -r requirements-dev.txt
```

4. Build the program
```bash
python setup.py build
```

##  🎯  Quick Start

1. Start the program for the first time
2. Set Blender installation directory
3. Click "Refresh" to get available versions
4. Select the required version for download/installation
5. Use version switching function

##  📖  Usage Guide

###Interface Overview

####Main Window
-Toolbar: Quick Access to Common Features
-Version List: Display all available versions
-Status bar: Display the current operational status
-Settings button: Access program configuration

####Set dialog box
-General settings
-Download Settings
-Backup Settings
-Theme setting
-Language settings

###Basic operations

####Version management
1. Obtain the version list
2. Download the new version
3. Switch versions
4. Delete version

####Configuration Management
1. Backup configuration
2. Restore configuration
3. Reset settings

###Advanced features

####Customize download source
```ini
[PREFERENCES]
SourceURL =  https://download.blender.org/release/
```

####Multi threaded download
```ini
[PREFERENCES]
ThreadCount = 4
```

####Automatic update check
```ini
[PREFERENCES]
AutoFetch = True
```

##  ⚙️  Configuration Description

###Configuration file location
- Windows: `% USERPROFILE%/blender_version_manager_config.ini`
- Linux/macOS: `~/ blender_version_manager_config.ini`

###Configuration Item Description

####General settings
```ini
[PREFERENCES]
Autofetch=True # Automatically retrieve version list
FolderPath=D:/Blender # Blender installation path
BackupFolder=D:/Backup # Backup folder path
```

####Download Settings
```ini
[PREFERENCES]
SourceURL =  https://download.blender.org/release/
ThreadCount=4 # Number of download threads
```

####Interface settings
```ini
[PREFERENCES]
Theme=System # Theme (System/Park)
Language=zh_CN # Interface Language
```

##  🌍  Multi language support

###Supported Languages
-Simplified Chinese (zh_CN)
-English (en-US)
-German (de_de)
-Japanese (ja_JP)
-Russian (ru_rU)

###Add new language
1. Create a new language folder in the 'locality' directory
2. Copy 'messages. bot' to a new folder
3. Rename to ` messagespro '`
4. Translate all strings
5. Compile `. mo ` files

###Language file structure
```
locale/
├── zh_CN/
│   ├── LC_MESSAGES/
│   │   ├── messages.po
│   │   └── messages.mo
├── en_US/
│   ├── LC_MESSAGES/
│   │   ├── messages.po
│   │   └── messages.mo
└── ...
```

##  🎨  Theme setting

###Supported themes
-System (Follow System)
-Dark (Dark Theme)

###Custom Theme
```python
#Example of Theme Configuration
THEMES = {
'Dark':  {
'background': '# 2b2b2b',
'foreground': '# ffffff',
'accent': '# 007acc'
}
}
```

##  ❓  common problem

### 1.  What should I do if the download fails?
-Check network connection
-Try switching download sources
-Increase the number of retries

### 2.  Version switching failed?
-Ensure the complete download of the target version
-Check file permissions
-Close all Blender processes

### 3.  Is the configuration file damaged?
-Use backup recovery
-Reset to default settings
-Manually edit and repair

##  👨‍💻  Developer's Guide

###Project Structure
```
Blender-VMT-Remastered/
∝ - blender-version_manager. py # Main Program
∝ - lang/# Language Files
∝ - icons/# icon resources
```

###Development environment settings

####Necessary tools
- Python 3.8+
- Git
- VSCode/PyCharm
- Qt Designer

####Development dependency
```bash
pip install -r requirements-dev.txt
```

###Construction instructions

#### Windows
```bash
pyinstaller --onefile --windowed --icon=icons/Blender-VMT.ico blender_version_manager.py
```

#### Linux
```bash
pyinstaller --onefile --windowed blender_version_manager.py
```

#### macOS
```bash
pyinstaller --onefile --windowed --icon=icons/Blender-VMT.icns blender_version_manager.py
```

###Testing Guide

####Unit testing
```bash
python -m pytest tests/
```

####Coverage testing
```bash
coverage run -m pytest
coverage report
```

####Performance testing
```bash
python -m cProfile -o output.prof blender_version_manager.py
```

###Contribution Guide

####Submit specifications
```
feat:  new function
fix:  Fix the problem
docs:  Document Update
style:  Code format
refactor:  code refactoring
test:  Testing related
chore:  Build related
```

####Branch management
-Main: main branch
-Develop: development branch
-Feature/*: Function branch
-Bugfix/*: Fix branch

####Code Style
-Follow PEP 8
-Use type annotation
-Write a document string

##  📝  Update log

### v1.0.0 (2024-03-xx)
-Initial version release
-Basic version management function
-Multi language support
-Theme switching

###V1.1.0 (planned)
-Plugin management
-Automatic update
-Performance optimization

##  🏗️  Technical Architecture

###Core module

####GUI module
-PyQt6 interface framework
-QSS Style Sheet
-Event driven architecture

####Download module
-Multi threaded download
-Resume from breakpoint
-Verification mechanism

####Configuration module
-INI configuration file
-Encrypted storage
-Version control

####Internationalization module
-Babel framework
-Dynamic loading
-Real time switching

###Data flow

```mermaid
graph TD
A [User Interface] -->B [Controller]
B -->C [Download Management]
B -->D [Configuration Management]
C -->E [File System]
D --> E
```

###Performance optimization

####Memory management
-Delayed loading
-Resource pooling
-Garbage collection

####Concurrent processing
-Asynchronous operation
-Thread Pool
-Task queue

##  📄  licence

This project adopts GPL3 license. Please refer to the [LICENSE] document for details.

```
Blender Version Manager - a tool for managing Blender versions
Copyright (C) 2024 dhjs0000

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY;  without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see < https://www.gnu.org/licenses/ >.
```

##  🙏  Thank you

###Open source project
- [PyQt]( https://riverbankcomputing.com/software/pyqt/ )
- [Babel]( http://babel.pocoo.org/ )
- [requests]( https://requests.readthedocs.io/ )

###Contributor
- dhjs0000

###Special thanks
-Blender Foundation
-Open source community
-All users

##  📞  contact information

-Problem feedback: [Issues]( https://github.com/dhjs0000/Blender-VMT-Remastered/issues )
-Email contact: 3110197220@qq.com
-Community discussion: [Discussions]( https://github.com/dhjs0000/Blender-VMT-Remastered/discussions )

---

<div align="center">

**[ ⬆  Return to top] (# blender version management tool blender version management tool tool)**

If this project is helpful to you, please consider giving it a star rating ⭐ ️, thank you!

</div> 