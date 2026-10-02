"""离线验证消息历史、截断与断流；不会连接模型或产生报告文件。"""
import importlib.util
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "chat-with-history.py"
SPEC = importlib.util.spec_from_file_location("lesson_chat", SCRIPT)
chat = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(chat)


def fake_stream(events):
    return io.BytesIO(b"\n".join(json.dumps(e, ensure_ascii=False).encode("utf-8") for e in events))


class HistoryTests(unittest.TestCase):
    def test_budget_removes_whole_old_turns_without_mutating_history(self):
        history = [{"role": "user", "content": "早" * 700},
                   {"role": "assistant", "content": "旧" * 700},
                   {"role": "user", "content": "我叫小林"},
                   {"role": "assistant", "content": "你好，小林"}]
        messages, removed = chat.prepare_messages(history, "我叫什么？")
        self.assertEqual(removed, 1)
        self.assertEqual([m["role"] for m in messages], ["user", "assistant", "user"])
        self.assertEqual(messages[0]["content"], "我叫小林")
        self.assertEqual(len(history), 4)
        with self.assertRaises(ValueError):
            chat.prepare_messages([], "长" * 2000)

    def test_stream_assembles_unicode_and_keeps_thinking_out_of_answer(self):
        events = [{"message": {"thinking": "test reasoning"}, "done": False},
                  {"message": {"content": "小"}, "done": False},
                  {"message": {"content": "林"}, "done": True, "done_reason": "stop",
                   "eval_count": 10, "eval_duration": 2_000_000_000}]
        with patch.object(chat.CLIENT, "open", return_value=fake_stream(events)) as opened, redirect_stdout(io.StringIO()):
            payload, result = chat.ask_model([{"role": "user", "content": "我叫什么？"}])
        self.assertTrue(result["complete"])
        self.assertEqual(result["answer"], "小林")
        self.assertEqual(result["decode_tokens_per_second"], 5.0)
        self.assertEqual(json.loads(opened.call_args.args[0].data), payload)

    def test_disconnect_and_length_limit_are_not_completed_answers(self):
        partial = [{"message": {"content": "没写完"}, "done": False}]
        with patch.object(chat.CLIENT, "open", return_value=fake_stream(partial)), redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError):
                chat.ask_model([{"role": "user", "content": "测试"}])
        limited = partial + [{"done": True, "done_reason": "length"}]
        with patch.object(chat.CLIENT, "open", return_value=fake_stream(limited)), redirect_stdout(io.StringIO()):
            _, result = chat.ask_model([{"role": "user", "content": "测试"}])
        self.assertFalse(result["complete"])

    def test_next_turn_carries_history_and_clear_removes_it(self):
        sent = []

        def answer(messages):
            sent.append(messages)
            return {}, {"complete": True, "answer": "你好，小林。"}

        with patch("builtins.input", side_effect=["我叫小林", "我叫什么", "/clear", "重新开始", "/exit"]), \
                patch.object(chat, "ask_model", side_effect=answer), \
                patch.object(chat, "save_record") as saved, redirect_stdout(io.StringIO()):
            chat.main()
        self.assertEqual([len(m) for m in sent], [1, 3, 1])
        self.assertEqual(sent[1][0]["content"], "我叫小林")
        self.assertEqual(sent[1][1]["role"], "assistant")
        self.assertEqual(saved.call_count, 3)

    def test_failed_turn_is_excluded_from_next_request(self):
        sent = []

        def answer(messages):
            sent.append(messages)
            return {}, {"complete": len(sent) > 1, "answer": "未完成"}

        with patch("builtins.input", side_effect=["第一次", "第二次", "/exit"]), \
                patch.object(chat, "ask_model", side_effect=answer), \
                patch.object(chat, "save_record"), redirect_stdout(io.StringIO()):
            chat.main()
        self.assertEqual(sent[1], [{"role": "user", "content": "第二次"}])


if __name__ == "__main__":
    unittest.main()
