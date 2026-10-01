# -*- coding: utf-8 -*-
"""
main.py —— 程序入口
====================
双击本文件（或命令行运行 python main.py）即可启动程序。
"""

import os
import sys
import tkinter as tk

# 把项目根目录加入搜索路径，保证 modules / ui / config 都能被找到
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ui.app import ScreenReaderApp


def main():
    root = tk.Tk()
    # 稍微美化一下默认字体
    try:
        from tkinter import ttk
        style = ttk.Style()
        style.theme_use("vista")  # Windows 上更好看
    except Exception:
        pass

    app = ScreenReaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
