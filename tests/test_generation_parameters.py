"""第四课离线检查：不连接 Ollama，不产生真实推理请求。"""
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generation-parameters-lab.py"
SPEC = importlib.util.spec_from_file_location("parameter_lab_tests", SCRIPT)
lab = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lab)


class ParameterTests(unittest.TestCase):
    def test_budget_pair_changes_only_num_predict(self):
        left, right = lab.generation_cases("1")
        self.assertEqual(left["prompt"], right["prompt"])
        self.assertEqual([k for k in left["options"] if left["options"][k] != right["options"][k]], ["num_predict"])
        self.assertEqual((left["options"]["num_predict"], right["options"]["num_predict"]), (8, 128))

    def test_each_temperature_pair_changes_only_temperature(self):
        cases = lab.generation_cases("3")
        self.assertEqual(len(cases), 6)
        for left, right in zip(cases[::2], cases[1::2]):
            self.assertEqual(left["prompt"], right["prompt"])
            self.assertEqual(left["pair_seed"], right["pair_seed"])
            self.assertEqual([k for k in left["options"] if left["options"][k] != right["options"][k]], ["temperature"])

    def test_options_restore_even_on_error(self):
        original = lab.chat.OPTIONS
        with self.assertRaises(RuntimeError):
            with lab.temporary_options({"num_predict": 8}):
                self.assertEqual(lab.chat.OPTIONS, {"num_predict": 8})
                raise RuntimeError("test")
        self.assertIs(lab.chat.OPTIONS, original)

    def test_context_demo_is_offline_and_preserves_whole_pairs(self):
        with patch.object(lab.chat, "ask_model") as request, redirect_stdout(io.StringIO()):
            result = lab.context_demo()
        request.assert_not_called()
        small, large = result["cases"]
        self.assertEqual((small["removed_old_turns"], large["removed_old_turns"]), (2, 0))
        self.assertEqual((small["message_count"], large["message_count"]), (5, 9))
        self.assertEqual(len(result["history"]), 8)

    def test_generation_uses_only_one_user_message(self):
        with patch.object(lab.chat, "ask_model", return_value=({}, {"answer": "test"})) as request, redirect_stdout(io.StringIO()):
            lab.run_generation_case(lab.generation_cases("1")[0])
        self.assertEqual(len(request.call_args.args[0]), 1)
        self.assertEqual(request.call_args.args[0][0]["role"], "user")

    def test_offline_menu_creates_readable_report_without_metadata_request(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(lab, "OUTPUT_DIR", Path(directory)), patch.object(lab, "service_metadata") as metadata, redirect_stdout(io.StringIO()):
                self.assertEqual(lab.main(["--experiment", "2"]), 0)
            metadata.assert_not_called()
            reports = list(Path(directory).glob("*.json"))
            self.assertEqual(len(reports), 1)
            report = json.loads(reports[0].read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "finished")
            self.assertEqual(report["entries"][0]["kind"], "application_budget_demo")
            with self.assertRaises(FileExistsError):
                lab.save_report(reports[0], report, new=True)


if __name__ == "__main__":
    unittest.main()
