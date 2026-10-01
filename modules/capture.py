# -*- coding: utf-8 -*-
"""
capture.py —— 屏幕截图 + 框选区域
==================================
两个功能：
    1. grab(box)      : 截取屏幕上指定矩形区域的画面，返回 Pillow 图片。
    2. select_region(): 弹出一个半透明全屏窗口，让用户用鼠标拖拽画出矩形，
                        返回 (left, top, width, height)；按 Esc 取消返回 None。

矩形 box 的格式统一为 (left, top, width, height)：
    left   : 矩形左上角的 X 坐标（距离屏幕左边的像素数）
    top    : 矩形左上角的 Y 坐标（距离屏幕上边的像素数）
    width  : 矩形宽度
    height : 矩形高度
"""

import mss
import numpy as np
import tkinter as tk
from PIL import Image


def grab(box):
    """
    截取屏幕上 box 区域的画面。

    参数:
        box: (left, top, width, height)

    返回:
        PIL.Image 对象（RGB 模式），可直接交给 OCR 识别。
    """
    left, top, width, height = box

    # mss 使用 {left, top, width, height} 字典来描述区域
    monitor = {"left": left, "top": top, "width": width, "height": height}

    with mss.mss() as sct:
        # sct.grab 返回的是 BGRA 格式的原始图像
        raw = sct.grab(monitor)

    # 转成 numpy 数组，再去掉 alpha 通道（BGRA -> BGR）
    arr = np.array(raw)
    img_bgr = arr[:, :, :3]

    # OpenCV 用 BGR，PIL 用 RGB，这里翻转通道顺序后交给 PIL
    img_rgb = img_bgr[:, :, ::-1]
    return Image.fromarray(img_rgb)


def grab_full_screen():
    """截取整个主屏幕，返回 PIL 图片（框选界面用）。"""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # monitors[0] 是全部屏幕，[1] 是主屏
        raw = sct.grab(monitor)
    arr = np.array(raw)[:, :, :3]
    img_rgb = arr[:, :, ::-1]
    return Image.fromarray(img_rgb)


def select_region(parent):
    """
    弹出一个全屏半透明窗口，让用户用鼠标拖拽选择一个矩形区域。

    重要：这里用 parent 上新建的 Toplevel 窗口，而不是另开一个 tk.Tk()。
    因为同一个程序里如果有两个 Tk() 主窗口，会导致窗口无法正常关闭、
    主界面收不回来等问题。

    参数:
        parent: 现有的主窗口（tk.Tk 或 tk.Toplevel）。

    返回:
        (left, top, width, height)；用户按 Esc 取消则返回 None。
    """
    result = {"box": None}

    # 用 Toplevel 而不是 Tk()，跟随主窗口的生命周期
    top = tk.Toplevel(parent)
    top.title("框选区域")
    top.attributes("-topmost", True)             # 永远显示在最上层
    top.overrideredirect(True)                   # 去掉标题栏，铺满整屏
    top.geometry(
        f"{parent.winfo_screenwidth()}x{parent.winfo_screenheight()}+0+0"
    )
    top.attributes("-alpha", 0.3)                # 半透明，能透出下面的屏幕
    top.configure(bg="black")

    # 画布铺满整个屏幕，用来画用户的选框
    canvas = tk.Canvas(top, cursor="cross", bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    # 提示文字
    canvas.create_text(
        parent.winfo_screenwidth() // 2, 40,
        text="按住鼠标左键拖拽框选区域，松开完成；按 Esc 取消",
        fill="white", font=("Microsoft YaHei", 20, "bold"),
    )

    # 记录鼠标按下时的起点
    start = {"x": 0, "y": 0}
    rect = {"id": None}

    def on_press(event):
        start["x"], start["y"] = event.x, event.y
        # 如果之前画过框，先删掉
        if rect["id"] is not None:
            canvas.delete(rect["id"])
        rect["id"] = canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline="red", width=3,
        )

    def on_drag(event):
        if rect["id"] is not None:
            canvas.coords(rect["id"], start["x"], start["y"], event.x, event.y)

    def on_release(event):
        # 计算矩形的左上角和宽高（兼容用户从右下往左上拖的情况）
        x1, y1 = start["x"], start["y"]
        x2, y2 = event.x, event.y
        left, top_y = min(x1, x2), min(y1, y2)
        width, height = abs(x2 - x1), abs(y2 - y1)
        if width > 3 and height > 3:  # 太小的忽略
            result["box"] = (left, top_y, width, height)
        top.destroy()

    def on_cancel(event=None):
        result["box"] = None
        top.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    top.bind("<Escape>", on_cancel)

    # 让框选窗口获得焦点，这样键盘 Esc 才能被它捕获
    top.focus_force()

    # 等待用户操作完成（窗口销毁后 wait_window 才返回）
    parent.wait_window(top)
    return result["box"]
