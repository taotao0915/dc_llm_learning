"""课堂用小型评测：实际调用本机模型，不是离线单元测试。

PyCharm 直接运行：6 个名字 × 2 次独立对话，每次 2 轮，共 24 次请求。
复用 chat-with-history.py 的真实调用逻辑；不自动下载模型，不修改模型配置。
每个案例后保存原始请求、正式回答与判分；中断时仍保留已完成案例。
"""
import importlib.util
import json
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("lesson_chat", ROOT / "scripts" / "chat-with-history.py")
chat = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(chat)
NAMES = [("en", "Alice"), ("en", "Bob"), ("en", "Emma"),
         ("zh", "小林"), ("zh", "李雷"), ("zh", "张敏")]
REPEATS = 2


def now():
    return datetime.now(timezone(timedelta(hours=8)))


def get_json(path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(chat.BASE_URL + path, data=data,
                      headers={"Content-Type": "application/json"})
    with chat.CLIENT.open(request, timeout=30) as response:
        return json.load(response)


def matches_name(answer, name):
    # 只容许首尾空白、句末句号与引号。不把“答案里出现过名字”算成严格通过。
    return answer.strip().strip('。.!！\"\'“”‘’').strip() == name


def summarize(cases):
    turns = [turn for case in cases for turn in case["turns"]]
    seconds = [turn["result"]["client_total_seconds"] for turn in turns]
    return {
        "completed_cases": len(cases), "planned_cases": len(NAMES) * REPEATS,
        "recall_passed": sum(case["recall_passed"] for case in cases),
        "full_case_passed": sum(case["full_case_passed"] for case in cases),
        "actual_requests": len(turns),
        "thinking_seen_turns": sum(t["result"]["thinking_output_present"] for t in turns),
        "turn_seconds_min": min(seconds) if seconds else None,
        "turn_seconds_median": round(statistics.median(seconds), 3) if seconds else None,
        "turn_seconds_max": max(seconds) if seconds else None,
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    started = now()
    output = ROOT / "output" / "name-recall"
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"evaluation-{started.strftime('%Y%m%d-%H%M%S-%f')}.json"
    report = {
        "started_at": started.isoformat(), "status": "running",
        "executed_by": "script operator; assistant for initial classroom validation",
        "ollama_version": get_json("/api/version"),
        "installed_models": get_json("/api/tags"),
        "model_details": get_json("/api/show", {"model": chat.MODEL}).get("details"),
        "configuration": {"model": chat.MODEL, "think": chat.THINK, "options": chat.OPTIONS.copy()},
        "method": "6 names x 2 fresh conversations, fixed seed; first assistant reply is real; no model/cache reset between cases",
        "grading": "case-sensitive exact name after trimming whitespace, terminal full stops/exclamation marks and quotes; acknowledgement must be OK",
        "cases": [],
    }

    def persist():
        report["summary"] = summarize(report["cases"])
        with path.open("w", encoding="utf-8") as file:
            json.dump(report, file, ensure_ascii=False, indent=2)

    # 首次独占创建，后续只更新本次评测自己的报告。
    with path.open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    print(f"模型：{chat.MODEL}；think={chat.THINK}；记录：{path}", flush=True)
    try:
        for repeat in range(1, REPEATS + 1):
            for language, name in NAMES:
                print(f"\n=== 第 {repeat} 次 / {name} ===", flush=True)
                prompts = ([f"My name is {name}. Reply with only OK.",
                            "What is my name? Reply with only the name."] if language == "en"
                           else [f"我叫{name}。请只回复 OK。", "我叫什么名字？请只回答名字。"])
                case = {"repeat": repeat, "language": language, "expected_name": name, "turns": [],
                        "recall_passed": False, "full_case_passed": False}
                history = []
                try:
                    for question in prompts:
                        messages, removed = chat.prepare_messages(history, question)
                        payload, result = chat.ask_model(messages)
                        case["turns"].append({"request": payload, "result": result, "removed_old_turns": removed})
                        if not result["complete"]:
                            break
                        history = messages + [{"role": "assistant", "content": result["answer"]}]
                    if len(case["turns"]) == 2:
                        first, second = case["turns"]
                        case["recall_passed"] = second["result"]["complete"] and matches_name(second["result"]["answer"], name)
                        case["full_case_passed"] = case["recall_passed"] and matches_name(first["result"]["answer"], "OK")
                except Exception as error:
                    case["error"] = f"{type(error).__name__}: {error}"
                report["cases"].append(case)
                persist()
                print(f"名字回答通过：{case['recall_passed']}；整组通过：{case['full_case_passed']}", flush=True)
        report["status"] = "finished"
    except BaseException as error:
        report["status"] = "interrupted"
        report["interruption"] = type(error).__name__
        raise
    finally:
        report["ended_at"] = now().isoformat()
        persist()
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2), flush=True)
        print(f"原始记录：{path}", flush=True)


if __name__ == "__main__":
    main()
