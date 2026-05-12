"""tts.py 纯逻辑单元测试（不调网络）。

跑：
    cd ~/.claude/skills/kaiyu-elevenlabs-tts
    python -m unittest tests.test_logic -v
或：
    python tests/test_logic.py
"""

import sys
import unittest
from pathlib import Path

# 把 scripts/ 加进 import path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from tts import (
    detect_language,
    split_text,
    _split_by_sentence,
    count_billable_chars,
    cache_key,
    estimate_cost,
)


class TestDetectLanguage(unittest.TestCase):
    def test_pure_chinese(self):
        lang, ratio, mixed = detect_language("你好世界这是一段中文")
        self.assertEqual(lang, "zh")
        self.assertAlmostEqual(ratio, 1.0)
        self.assertFalse(mixed)

    def test_pure_english(self):
        lang, ratio, mixed = detect_language("Hello world this is English")
        self.assertEqual(lang, "en")
        self.assertEqual(ratio, 0.0)
        self.assertFalse(mixed)

    def test_chinese_dominant(self):
        # 中文为主，少量英文术语 → zh
        lang, ratio, _ = detect_language("我们用 Python 来检测语种是否合理")
        self.assertEqual(lang, "zh")
        self.assertGreater(ratio, 0.5)

    def test_empty(self):
        lang, ratio, mixed = detect_language("")
        self.assertEqual(lang, "en")
        self.assertEqual(ratio, 0.0)
        self.assertFalse(mixed)

    def test_punctuation_only(self):
        # 只有数字标点 → 视为英文（不会 div by zero）
        lang, ratio, mixed = detect_language("...123!!!")
        self.assertEqual(lang, "en")
        self.assertEqual(ratio, 0.0)
        self.assertFalse(mixed)

    def test_mixed_flag(self):
        # 中英比例都不极端 → mixed=True
        text = "Hello 世界 this is mixed 中文 and English text 一二三四"
        _, _, mixed = detect_language(text)
        self.assertTrue(mixed)

    def test_threshold_just_below(self):
        # 1 个汉字夹在 10 个英文字母里：1/(1+10)=9.09% < 15% → en
        lang, _, _ = detect_language("aaaaaaaaaa中")
        self.assertEqual(lang, "en")

    def test_threshold_just_above(self):
        # 2 个汉字夹在 10 个英文字母里：2/12=16.7% > 15% → zh
        lang, _, _ = detect_language("aaaaaaaaaa中文")
        self.assertEqual(lang, "zh")


class TestSplitText(unittest.TestCase):
    def test_short_no_split(self):
        chunks = split_text("短文本", 100)
        self.assertEqual(chunks, ["短文本"])

    def test_split_by_paragraph(self):
        text = "第一段。\n第二段。\n第三段。"
        chunks = split_text(text, 6)
        for c in chunks:
            self.assertLessEqual(len(c), 6)
        # 拼回去能还原所有内容字符（忽略段间空白）
        rejoined = "".join(c.replace("\n", "") for c in chunks)
        original = text.replace("\n", "")
        self.assertEqual(rejoined, original)

    def test_long_single_sentence_hard_split(self):
        text = "abcdefghij" * 5  # 50 字符无标点
        chunks = split_text(text, 12)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLessEqual(len(c), 12)
        self.assertEqual("".join(chunks), text)

    def test_split_by_sentence_punctuation(self):
        chunks = _split_by_sentence("第一句。第二句。第三句。", 4)
        for c in chunks:
            self.assertLessEqual(len(c), 4)


class TestBillableChars(unittest.TestCase):
    def test_minimax_pure_chinese(self):
        # 6 个汉字 × 2 = 12
        self.assertEqual(count_billable_chars("你好世界你好", "minimax"), 12)

    def test_minimax_with_chinese_punctuation(self):
        # CJK 范围只覆盖 \u4e00-\u9fff，中文逗号 \uff0c 不在内 → 按 1 字符算
        # 4 汉字 × 2 + 1 逗号 = 9
        self.assertEqual(count_billable_chars("你好，世界", "minimax"), 9)

    def test_minimax_mixed(self):
        # 4 汉字 + "abc" 3 字符 + 1 空格 = 4*2 + 3 + 1 = 12
        self.assertEqual(count_billable_chars("你好世界 abc", "minimax"), 12)

    def test_elevenlabs_equals_len(self):
        self.assertEqual(count_billable_chars("hello world", "elevenlabs"), 11)

    def test_elevenlabs_chinese_no_doubling(self):
        # ElevenLabs 不做 ×2 处理
        self.assertEqual(count_billable_chars("你好", "elevenlabs"), 2)


class TestCacheKey(unittest.TestCase):
    def test_deterministic(self):
        k1 = cache_key("minimax", "v1", "m1", "你好",
                       {"emotion": "happy"}, {"sample_rate": 32000})
        k2 = cache_key("minimax", "v1", "m1", "你好",
                       {"emotion": "happy"}, {"sample_rate": 32000})
        self.assertEqual(k1, k2)

    def test_text_change_invalidates(self):
        k1 = cache_key("minimax", "v1", "m1", "你好", {}, {})
        k2 = cache_key("minimax", "v1", "m1", "再见", {}, {})
        self.assertNotEqual(k1, k2)

    def test_voice_setting_change_invalidates(self):
        k1 = cache_key("minimax", "v1", "m1", "你好", {"emotion": "happy"}, {})
        k2 = cache_key("minimax", "v1", "m1", "你好", {"emotion": "sad"}, {})
        self.assertNotEqual(k1, k2)

    def test_provider_change_invalidates(self):
        k1 = cache_key("minimax", "v1", "m1", "你好", {}, {})
        k2 = cache_key("elevenlabs", "v1", "m1", "你好", {}, {})
        self.assertNotEqual(k1, k2)

    def test_voice_id_change_invalidates(self):
        k1 = cache_key("minimax", "v1", "m1", "你好", {}, {})
        k2 = cache_key("minimax", "v2", "m1", "你好", {}, {})
        self.assertNotEqual(k1, k2)

    def test_dict_order_invariant(self):
        # 字段顺序不影响 key（json.dumps sort_keys=True 保证）
        k1 = cache_key("minimax", "v1", "m1", "你好",
                       {"emotion": "happy", "speed": 1.1}, {})
        k2 = cache_key("minimax", "v1", "m1", "你好",
                       {"speed": 1.1, "emotion": "happy"}, {})
        self.assertEqual(k1, k2)


class TestEstimateCost(unittest.TestCase):
    def test_minimax_format(self):
        s = estimate_cost("minimax", 1000)
        self.assertIn("¥", s)
        self.assertIn("Token Plan", s)

    def test_elevenlabs_format(self):
        s = estimate_cost("elevenlabs", 1000)
        self.assertIn("$", s)
        self.assertIn("¥", s)

    def test_unknown_provider(self):
        self.assertEqual(estimate_cost("foo", 100), "未知")


if __name__ == "__main__":
    unittest.main()
