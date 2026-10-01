# -*- coding: utf-8 -*-
"""
ocr.py —— 文字识别
==================
把一张图片里的文字识别出来。

底层用 EasyOCR。它第一次运行时会自动联网下载识别模型，之后就不用再下了。

注意：easyocr 在真正的识别动作发生时才导入（延迟导入），
因为导入它会加载庞大的深度学习框架，很慢。
这样即使还没安装它，图形界面也能正常打开。
"""


class TextReader:
    """文字识别器。

    用法：
        reader = TextReader(["ch_sim", "en"])
        text = reader.read_text(pil_image)
    """

    def __init__(self, languages, use_gpu=False):
        """
        参数:
            languages: 语言列表，例如 ["ch_sim", "en"]
            use_gpu:   是否用显卡加速（没有 NVIDIA 显卡就填 False）
        """
        self.languages = languages
        self.use_gpu = use_gpu
        self.reader = None   # 真正用的时候再创建

    def _ensure_reader(self):
        """第一次使用时才创建 EasyOCR 识别器（这一步慢，只做一次）。"""
        if self.reader is not None:
            return
        try:
            import easyocr
        except ImportError:
            raise RuntimeError(
                "没有找到 easyocr 库。请先运行：pip install easyocr\n"
                "（如果安装失败，可先执行 pip install torch torchvision）"
            )
        self.reader = easyocr.Reader(self.languages, gpu=self.use_gpu)

    def read_text(self, pil_image):
        """
        识别一张图片里的所有文字。

        参数:
            pil_image: PIL 图片对象

        返回:
            识别出的字符串（多行文字用换行拼在一起）。
        """
        import numpy as np

        self._ensure_reader()

        # EasyOCR 需要 numpy 数组格式的输入
        image_array = np.array(pil_image)

        # detail=0 表示只返回文字内容，不要坐标等详细信息
        results = self.reader.readtext(image_array, detail=0)

        # results 是一个字符串列表，把它们拼起来
        return "\n".join(results).strip()
