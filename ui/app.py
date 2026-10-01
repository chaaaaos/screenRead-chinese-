# -*- coding: utf-8 -*-
"""
app.py —— 图形界面
==================
把所有功能串起来的窗口程序。界面元素：
    - 选择语音包（默认跟随系统）
    - 选择识别语言
    - 框选"身份区域"和"文字区域"
    - 开始 / 停止 自动朗读
    - 显示识别结果
"""

import json
import os
import threading
import tkinter as tk
from tkinter import ttk

import config
from modules.capture import grab, select_region
from modules.ocr import TextReader
from modules.tts import Speaker
from modules.voice_chooser import choose_voice_pack


class ScreenReaderApp:
    """主窗口应用。"""

    def __init__(self, root):
        self.root = root
        self.root.title("屏幕文字朗读器 ScreenReader")
        self.root.geometry("640x660")

        # ---- 运行状态 ----
        self.running = False             # 是否正在自动朗读
        self.text_box = config.DEFAULT_TEXT_BOX
        self.speaker_box = config.DEFAULT_SPEAKER_BOX
        self.last_text = ""              # 上次朗读的文字（用于去重）
        self.reader = None               # OCR 识别器（用时才创建，很慢）
        self.speaker = None              # 语音引擎

        # ---- 界面变量 ----
        self.voice_var = tk.StringVar(value=config.DEFAULT_VOICE_PACK)
        self.lang_var = tk.StringVar(value="ch_sim+en")
        self.status_var = tk.StringVar(value="就绪")
        # 用于在界面上显示两个区域坐标的文字
        self.speaker_box_var = tk.StringVar(value=str(self.speaker_box))
        self.text_box_var = tk.StringVar(value=str(self.text_box))

        # 读取上次保存的设置（会更新上面的坐标变量）
        self._load_settings()

        # 创建界面
        self._build_ui()

        # 退出时保存设置
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ==================================================================
    # 界面搭建
    # ==================================================================
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # ---------- 区域1：语音包 ----------
        frame_voice = ttk.LabelFrame(self.root, text="1. 语音包设置")
        frame_voice.pack(fill="x", **pad)

        ttk.Label(frame_voice, text="选择语音包：").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        voice_names = list(config.VOICE_PACKS.keys())
        self.voice_combo = ttk.Combobox(
            frame_voice, textvariable=self.voice_var,
            values=voice_names, state="readonly", width=20,
        )
        self.voice_combo.grid(row=0, column=1, sticky="w", padx=6, pady=6)

        btn_test = ttk.Button(frame_voice, text="试听", command=self._test_voice)
        btn_test.grid(row=0, column=2, padx=6, pady=6)

        lbl_hint = ttk.Label(
            frame_voice,
            text="提示：语音包只是调整语速/音量；\n若系统有多个音色会自动挑选相近的。",
            foreground="gray",
        )
        lbl_hint.grid(row=1, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 6))

        # ---------- 区域2：识别语言 ----------
        frame_lang = ttk.LabelFrame(self.root, text="2. 识别语言")
        frame_lang.pack(fill="x", **pad)

        ttk.Label(frame_lang, text="选择语言：").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        lang_choices = ["ch_sim+en", "ch_sim", "en", "ja", "ko"]
        self.lang_combo = ttk.Combobox(
            frame_lang, textvariable=self.lang_var,
            values=lang_choices, state="readonly", width=20,
        )
        self.lang_combo.grid(row=0, column=1, sticky="w", padx=6, pady=6)

        # ---------- 区域3：框选区域 ----------
        frame_area = ttk.LabelFrame(self.root, text="3. 框选屏幕区域")
        frame_area.pack(fill="x", **pad)

        ttk.Label(frame_area, text="身份判断区域：").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.lbl_speaker_box = ttk.Label(frame_area, textvariable=self.speaker_box_var, foreground="blue")
        self.lbl_speaker_box.grid(row=0, column=1, sticky="w", padx=6, pady=6)
        ttk.Button(frame_area, text="框选身份区域", command=self._select_speaker_box)\
            .grid(row=0, column=2, padx=6, pady=6)

        ttk.Label(frame_area, text="朗读文字区域：").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        self.lbl_text_box = ttk.Label(frame_area, textvariable=self.text_box_var, foreground="blue")
        self.lbl_text_box.grid(row=1, column=1, sticky="w", padx=6, pady=6)
        ttk.Button(frame_area, text="框选文字区域", command=self._select_text_box)\
            .grid(row=1, column=2, padx=6, pady=6)

        # ---------- 区域4：控制 ----------
        frame_ctrl = ttk.LabelFrame(self.root, text="4. 运行控制")
        frame_ctrl.pack(fill="x", **pad)

        self.btn_start = ttk.Button(frame_ctrl, text="▶ 开始朗读", command=self._start)
        self.btn_start.grid(row=0, column=0, padx=6, pady=6)
        self.btn_stop = ttk.Button(frame_ctrl, text="■ 停止", command=self._stop, state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=6, pady=6)
        ttk.Button(frame_ctrl, text="🔊 立即朗读一次", command=self._read_once)\
            .grid(row=0, column=2, padx=6, pady=6)

        ttk.Label(frame_ctrl, text="状态：").grid(row=1, column=0, sticky="w", padx=6)
        ttk.Label(frame_ctrl, textvariable=self.status_var, foreground="green")\
            .grid(row=1, column=1, columnspan=2, sticky="w", padx=6)

        # ---------- 区域5：识别结果 ----------
        frame_result = ttk.LabelFrame(self.root, text="5. 识别结果")
        frame_result.pack(fill="both", expand=True, **pad)

        self.txt_result = tk.Text(frame_result, height=8, wrap="word")
        self.txt_result.pack(fill="both", expand=True, padx=6, pady=6)

    # ==================================================================
    # 按钮回调
    # ==================================================================
    def _test_voice(self):
        """试听当前选中的语音包。"""
        name = self.voice_var.get()
        pack = config.VOICE_PACKS[name]
        self._ensure_speaker()
        self.speaker.speak(f"你好，我是{name}。这是一段试听语音。", pack)

    def _select_speaker_box(self):
        """框选身份判断区域。"""
        # 让主窗口暂时最小化到后面，方便看到整个屏幕
        self.root.withdraw()
        self.root.update()
        # 关键：把现有主窗口传进去，框选窗口用 Toplevel 实现
        box = select_region(self.root)
        # 无论用户是否成功框选，都要把主窗口显示回来
        self.root.deiconify()
        self.root.lift()

        if box:
            self.speaker_box = box
            self.speaker_box_var.set(str(box))
            self._save_settings()

    def _select_text_box(self):
        """框选朗读文字区域。"""
        self.root.withdraw()
        self.root.update()
        box = select_region(self.root)
        self.root.deiconify()
        self.root.lift()

        if box:
            self.text_box = box
            self.text_box_var.set(str(box))
            self._save_settings()

    def _start(self):
        """开始自动循环朗读。"""
        if self.running:
            return
        self.running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.status_var.set("开始识别，正在准备 OCR 模型（首次较慢）…")
        # 后台线程里跑循环，避免卡界面
        threading.Thread(target=self._auto_loop, daemon=True).start()

    def _stop(self):
        """停止自动朗读。"""
        self.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.status_var.set("已停止")

    def _read_once(self):
        """立即识别并朗读一次。"""
        threading.Thread(target=self._do_read, daemon=True).start()

    def _on_close(self):
        """关闭窗口：停止朗读、保存设置、关闭所有语音引擎。"""
        self.running = False
        self._save_settings()
        if self.speaker is not None:
            self.speaker.stop()
        self.root.destroy()

    # ==================================================================
    # 核心逻辑
    # ==================================================================
    def _ensure_reader(self):
        """按需创建 OCR 识别器（创建过程很慢，只做一次）。"""
        if self.reader is None:
            langs = self.lang_var.get().split("+")
            self.reader = TextReader(langs, use_gpu=config.OCR_USE_GPU)

    def _ensure_speaker(self):
        """按需创建语音引擎。"""
        if self.speaker is None:
            self.speaker = Speaker()

    def _set_status(self, text):
        """线程安全地更新状态栏（从后台线程调用也安全）。"""
        self.root.after(0, self.status_var.set, text)

    def _auto_loop(self):
        """自动循环：每隔一段时间识别并朗读一次。"""
        import time
        while self.running:
            try:
                self._do_read()
            except Exception as e:
                self._set_status(f"出错：{e}")
            # 分小段 sleep，方便及时响应"停止"
            elapsed = 0.0
            while self.running and elapsed < config.AUTO_READ_INTERVAL:
                time.sleep(0.2)
                elapsed += 0.2
        self._set_status("已停止")

    def _do_read(self):
        """识别文字区域的文字 + 身份区域的文字，选择语音包并朗读。"""
        self._set_status("正在识别…")

        # 1. 准备 OCR 和语音引擎
        self._ensure_reader()
        self._ensure_speaker()

        # 2. 截图两个区域
        text_image = grab(self.text_box)
        speaker_image = grab(self.speaker_box)

        # 3. 识别文字
        text = self.reader.read_text(text_image)
        speaker_text = self.reader.read_text(speaker_image)

        # 4. 判断该用哪个语音包
        pack_name, pack = choose_voice_pack(speaker_text)

        # 5. 更新界面显示
        self.root.after(0, self._show_result, text, speaker_text, pack_name)

        # 6. 去重：和上次一样就不重复读
        if config.SKIP_REPEATED_TEXT and text == self.last_text:
            self._set_status("文字未变化，跳过")
            return
        self.last_text = text

        # 7. 朗读
        if text:
            self._set_status(f"正在朗读（语音包：{pack_name}）")
            self.speaker.speak(text, pack)
        else:
            self._set_status("未识别到文字")

    def _show_result(self, text, speaker_text, pack_name):
        """把识别结果写进界面文本框。"""
        self.txt_result.delete("1.0", "end")
        self.txt_result.insert("end", f"【身份区域文字】\n{speaker_text}\n\n")
        self.txt_result.insert("end", f"【判断语音包】{pack_name}\n\n")
        self.txt_result.insert("end", f"【朗读文字】\n{text}\n")

    # ==================================================================
    # 设置保存 / 读取
    # ==================================================================
    def _settings_path(self):
        # 配置文件放在本代码所在目录（ui 的上一级）
        base = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(base, "..", config.SETTINGS_FILE))

    def _save_settings(self):
        data = {
            "text_box": list(self.text_box),
            "speaker_box": list(self.speaker_box),
            "voice_pack": self.voice_var.get(),
            "language": self.lang_var.get(),
        }
        try:
            with open(self._settings_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 保存失败不影响使用

    def _load_settings(self):
        path = self._settings_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("text_box"):
                self.text_box = tuple(data["text_box"])
                self.text_box_var.set(str(self.text_box))
            if data.get("speaker_box"):
                self.speaker_box = tuple(data["speaker_box"])
                self.speaker_box_var.set(str(self.speaker_box))
            if data.get("voice_pack"):
                self.voice_var.set(data["voice_pack"])
            if data.get("language"):
                self.lang_var.set(data["language"])
        except Exception:
            pass
