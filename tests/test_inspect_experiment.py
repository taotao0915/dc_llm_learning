"""第 5 课离线检查：只测试内存中的数据，不连接服务、不创建文件。"""
import copy
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "inspect-experiment.py"
SPEC = importlib.util.spec_from_file_location("inspect_experiment_tests", SCRIPT)
viewer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(viewer)


class InspectTests(unittest.TestCase):
    def test_stop_is_not_a_quality_grade(self):
        label = viewer.completion_label({"done_reason": "stop", "complete": True, "answer": "1+1=3"})
        self.assertIn("不代表内容正确", label)
        self.assertIn("没有正式正文", viewer.completion_label({"done_reason": "stop", "answer": " "}))

    def test_length_and_unknown_reason_are_distinguished(self):
        self.assertIn("长度限制", viewer.completion_label({"done_reason": "length", "answer": "没写完"}))
        self.assertIn("未确认", viewer.completion_label({"answer": "有文本"}))

    def test_missing_metrics_are_not_zero(self):
        self.assertEqual(viewer.number(None), "未记录")
        self.assertEqual(viewer.number(False), "未记录")
        self.assertEqual(viewer.number(0), "0.000")
        self.assertEqual(viewer.number(float("nan")), "无效数值")
        self.assertEqual(viewer.number(-1), "无效数值")

    def test_offline_demo_is_excluded_and_input_is_not_mutated(self):
        report = {"entries": [{"kind": "application_budget_demo"},
                              {"kind": "model_generation", "result": {"answer": "示例"}}]}
        before = copy.deepcopy(report)
        result = viewer.render_report(report)
        self.assertIn("有 1 次已记录", result)
        self.assertEqual(before, report)

    def test_default_two_all_option_and_actual_speed_fields(self):
        entry = {"kind": "model_generation", "result": {"client_total_seconds": 10.273,
                 "decode_tokens_per_second": 6.29, "first_answer_chunk_seconds": 9.022}}
        report = {"entries": [copy.deepcopy(entry) for _ in range(3)]}
        text = viewer.render_report(report)
        self.assertIn("展示 2 次", text)
        self.assertIn("首个正式答案片段：9.022 秒", text)
        self.assertIn("客户端总耗时：10.273 秒", text)
        self.assertIn("服务端生成阶段速度：6.29 token/s", text)
        self.assertIn("展示 3 次", viewer.render_report(report, show_all=True))

    def test_invalid_report_is_not_silently_accepted(self):
        for invalid in ({}, {"entries": "bad"}, {"entries": [None]},
                        {"entries": [{"kind": "model_generation"}]}):
            with self.assertRaises(ValueError):
                viewer.render_report(invalid)
        self.assertIn("没有真实生成记录", viewer.render_report({"entries": []}))


if __name__ == "__main__":
    unittest.main()
