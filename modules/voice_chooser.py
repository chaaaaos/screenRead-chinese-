# -*- coding: utf-8 -*-
"""
voice_chooser.py —— 根据文字判断该用哪个语音包
================================================
这是需求2的核心：读取"身份框"里的文字，判断说话人是谁，
然后返回对应的语音包名字，交给 tts 去用不同音色朗读。

判断规则写在 config.SPEAKER_RULES 里，新手直接改那里即可。
"""

import config


def choose_voice_pack(speaker_text):
    """
    根据说话人区域识别到的文字，决定使用哪个语音包。

    参数:
        speaker_text: 从"身份框"里识别出来的文字字符串

    返回:
        (语音包名字, 语音包配置字典)
        例如 ("小女孩", {...})
    """
    if not speaker_text:
        # 没有文字，直接用默认语音包
        name = config.FALLBACK_VOICE_PACK
        return name, config.VOICE_PACKS[name]

    # 逐条检查规则（顺序很重要，越靠前优先）
    for keywords, pack_name in config.SPEAKER_RULES:
        for kw in keywords:
            if kw in speaker_text:
                return pack_name, config.VOICE_PACKS[pack_name]

    # 所有规则都没命中，用兜底语音包
    name = config.FALLBACK_VOICE_PACK
    return name, config.VOICE_PACKS[name]
