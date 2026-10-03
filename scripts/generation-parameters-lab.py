"""第 4 课：直接在 PyCharm 运行，选择一组参数实验。

1 输出预算：2 次真实请求；2 上下文：只运行本地裁剪逻辑；3 温度：6 次请求。
复用第二课的发送函数，只临时改变本进程的配置，不编辑第二课脚本。
"""
import argparse
import importlib.util
import json
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("parameter_chat", ROOT / "scripts" / "chat-with-history.py")
chat = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(chat)
BASE_OPTIONS = {**chat.OPTIONS, "num_ctx": 4096, "num_predict": 128,
                "temperature": 0.6, "seed": 42}
OUTPUT_DIR = ROOT / "output" / "generation-parameters"


@contextmanager
def temporary_options(options):
    """修改的是本进程内导入的变量，退出后恢复，磁盘源文件完全不变。"""
    original = chat.OPTIONS
    chat.OPTIONS = options.copy()
    try:
        yield
    finally:
        chat.OPTIONS = original


def generation_cases(experiment):
    if experiment == "1":
        prompt = "请用三句话解释什么是端侧大模型：第一句说明运行在哪里；第二句说明一个优点；第三句说明一个限制。"
        return [{"label": f"输出上限 {limit}", "changed_parameter": "num_predict",
                 "prompt": prompt, "options": {**BASE_OPTIONS, "num_predict": limit}}
                for limit in (8, 128)]
    if experiment == "3":
        prompt = "为一家适合学习编程的咖啡馆取一个中文名字，只输出一个名字，不超过六个汉字。"
        # 每个 seed 构成一对：同一对内只改变 temperature，跨对才改变 seed。
        return [{"label": f"seed={seed}, temperature={temperature}",
                 "changed_parameter": "temperature", "pair_seed": seed,
                 "prompt": prompt, "options": {**BASE_OPTIONS, "seed": seed, "temperature": temperature}}
                for seed in (42, 43, 44) for temperature in (0.2, 1.0)]
    raise ValueError("真实生成实验只支持 1 或 3")


def run_generation_case(case):
    print(f"\n--- {case['label']} ---", flush=True)
    # 每次仅有当前问题；上一个实验的答案不会进入本次请求。
    with temporary_options(case["options"]):
        payload, result = chat.ask_model([{"role": "user", "content": case["prompt"]}])
    print(f"设置的输出上限：{case['options']['num_predict']}；"
          f"实际生成：{result.get('generated_tokens_including_thinking', '未知')} token；"
          f"结束原因：{result.get('done_reason', '未知')}")
    if case["options"]["num_predict"] == 8 and result.get("done_reason") == "length":
        print("本组故意把输出限制为 8 token；请观察下一组 128 的结果，不必修改原聊天脚本。")
    return {"kind": "model_generation", "case": case, "request": payload, "result": result}


def context_demo():
    """只测试应用层长度预算，不发送历史、不加载模型、不测模型记忆能力。"""
    history = []
    for number in range(1, 5):
        history += [{"role": "user", "content": f"第{number}轮用户消息：" + "背景资料。" * 40},
                    {"role": "assistant", "content": f"收到第{number}轮资料。"}]
    question = "请根据前面的资料回答。"
    cases = []
    for size in (2048, 4096):
        options = {**BASE_OPTIONS, "num_ctx": size}
        with temporary_options(options):
            messages, removed = chat.prepare_messages(history, question)
        result = {"num_ctx": size, "num_predict": options["num_predict"],
                  "application_budget": size - options["num_predict"] - 128,
                  "removed_old_turns": removed, "message_count": len(messages),
                  "remaining_messages": messages,
                  "estimated_bytes_plus_overhead": sum(len(m["content"].encode("utf-8")) + 32 for m in messages)}
        cases.append(result)
        print(f"num_ctx={size}：裁剪 {removed} 轮，保留 {len(messages)} 条消息。")
    print("注意：这里按 UTF-8 字节加开销进行保守估算，不是真实 tokenizer 的 token 数；没有调用模型。")
    return {"kind": "application_budget_demo", "history": history, "question": question, "cases": cases}


def service_metadata():
    metadata = {}
    for key, endpoint in (("ollama_version", "/api/version"), ("installed_models", "/api/tags")):
        with chat.CLIENT.open(Request(chat.BASE_URL + endpoint), timeout=30) as response:
            metadata[key] = json.load(response)
    return metadata


def save_report(path, report, *, new=False):
    with path.open("x" if new else "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", choices=("1", "2", "3", "all"))
    args = parser.parse_args(argv)
    print("第 4 课：生成参数实验（不会修改连续聊天脚本）")
    print("1 输出预算：2 次请求 | 2 上下文裁剪：无需模型 | 3 温度：6 次请求")
    choice = args.experiment or input("选择 1/2/3，直接回车先做 1：").strip() or "1"
    if choice not in ("1", "2", "3", "all"):
        print("请选择 1、2 或 3。")
        return 2
    now = datetime.now(timezone(timedelta(hours=8)))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"experiment-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    report = {"started_at": now.isoformat(), "experiment": choice, "status": "running",
              "model": chat.MODEL, "think": chat.THINK, "base_options": BASE_OPTIONS,
              "entries": [], "note": "每组为独立请求；温度实验每个 seed 内仅改变温度；上下文实验仅测试应用层裁剪。"}
    save_report(path, report, new=True)
    print(f"本次报告：{path}", flush=True)
    try:
        if choice != "2":
            report.update(service_metadata())
        for selected in (("1", "2", "3") if choice == "all" else (choice,)):
            if selected == "2":
                report["entries"].append(context_demo())
                save_report(path, report)
                continue
            for case in generation_cases(selected):
                report["entries"].append(run_generation_case(case))
                save_report(path, report)
        report["status"] = "finished"
        return 0
    except KeyboardInterrupt:
        report["status"] = "interrupted"
        print("已中断；已完成的实验保留在报告中，未完成请求不算成功。")
        return 130
    except Exception as error:
        report["status"] = "error"
        report["error"] = f"{type(error).__name__}: {error}"
        print(f"实验未完成：{report['error']}。真实生成需要本机 Ollama 启动且模型已安装。")
        return 1
    finally:
        report["ended_at"] = datetime.now(timezone(timedelta(hours=8))).isoformat()
        save_report(path, report)
        print(f"报告已保存：{path}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
