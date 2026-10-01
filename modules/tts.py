# -*- coding: utf-8 -*-
"""
tts.py —— 语音合成（把文字读出来）
====================================
用系统自带的语音引擎 pyttsx3 来朗读。

"有感情"的实现思路（对新手友好、可扩展）：
    - 每个"语音包"有不同的语速(rate)和音量(volume)，从而听起来情绪不同。
    - 尽量挑选系统里不同音色的语音（男声/女声），让角色区分更明显。
    - 想升级成真人有感情的语音（如微软 edge-tts / Azure），
      见 README「如何扩展语音」一节，只需替换本文件的 speak()。

注意（重要，解决"只有第一次能发声"的问题）：
    Windows 上的 pyttsx3 引擎在多次跨线程调用后常常"哑掉"，
    第二次调用 runAndWait() 就没声音了。
    解决办法：每次朗读都新建一个引擎实例，读完就丢掉。
    这样虽然稍微多一点开销，但稳定可靠。
"""

import threading
import pyttsx3


class Speaker:
    """语音朗读器。

    用法：
        sp = Speaker()
        sp.speak("你好呀", pack={...语音包配置...})
    """

    def __init__(self):
        # 用一个锁，保证同一时间只有一段话在朗读，不会互相打断
        self._lock = threading.Lock()
        # 记录当前正在朗读的引擎，方便"停止"
        self._current_engine = None
        # 正在朗读时的事件；未朗读时处于"已设置"状态，
        # 朗读开始后清除，读完再设置回来，方便 wait() 等待
        self._done_event = threading.Event()
        self._done_event.set()
        # 缓存系统语音列表（临时引擎查询，查完即销毁）
        self._system_voices = self._query_system_voices()

    def _query_system_voices(self):
        """临时创建一个引擎，查询系统里有哪些语音，然后销毁它。"""
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            engine.stop()
            return voices or []
        except Exception:
            return []

    def list_system_voices(self):
        """返回系统里所有可用语音的名字列表（给界面下拉框用）。"""
        return [v.name for v in self._system_voices]

    def _pick_system_voice_id(self, keywords):
        """
        根据关键词，从系统语音里挑一个匹配的语音的 id。

        参数:
            keywords: 关键词列表，例如 ["Huihui", "女"]

        返回:
            匹配到的语音 id；没匹配到返回 None（表示用系统默认）。
        """
        if not keywords:
            return None
        for voice in self._system_voices:
            text = (voice.name or "") + " " + " ".join(voice.languages or [])
            for kw in keywords:
                if kw.lower() in text.lower():
                    return voice.id
        return None

    def speak(self, text, pack):
        """
        朗读一段文字（不阻塞，后台线程里念）。

        参数:
            text: 要朗读的字符串
            pack: 语音包配置字典，例如 config.VOICE_PACKS["小女孩"]
                  （包含 rate / volume / voice_keywords）
        """
        if not text or not text.strip():
            return

        # 标记"正在朗读"，供 wait() 使用
        self._done_event.clear()

        # 单独开一个线程朗读，避免界面卡住
        thread = threading.Thread(
            target=self._speak_worker, args=(text, pack), daemon=True
        )
        thread.start()

    def _speak_worker(self, text, pack):
        """真正干活的函数，在后台线程里运行。每次都用全新引擎。"""
        with self._lock:
            try:
                # 关键修复：每次朗读都新建引擎，避免 Windows 上第二次失效
                engine = pyttsx3.init()
                self._current_engine = engine

                # 1. 设置语速
                engine.setProperty("rate", pack.get("rate", 200))

                # 2. 设置音量（0.0 ~ 1.0）
                engine.setProperty("volume", pack.get("volume", 1.0))

                # 3. 挑选系统语音（按关键词），挑不到就用默认
                voice_id = self._pick_system_voice_id(pack.get("voice_keywords", []))
                if voice_id is not None:
                    engine.setProperty("voice", voice_id)

                # 4. 朗读
                engine.say(text)
                engine.runAndWait()

                # 5. 读完销毁引擎，释放资源
                engine.stop()
            except Exception:
                # 任何异常都不要让后台线程崩溃
                pass
            finally:
                self._current_engine = None
                self._done_event.set()

    def wait(self, timeout=None):
        """等待当前这段朗读结束（主要给测试 / 需要同步的场合用）。"""
        self._done_event.wait(timeout)

    def is_speaking(self):
        """当前是否正在朗读。"""
        return not self._done_event.is_set()

    def stop(self):
        """立即停止当前朗读。"""
        engine = self._current_engine
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                pass
        # 无论是否真的停下，都标记为"朗读结束"，避免 wait() 卡死
        self._done_event.set()
