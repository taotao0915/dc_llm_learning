"""第 5 课：只读查看第四课 JSON 报告，不连接模型，不产生新推理记录。

PyCharm 直接运行：默认展示课堂固定报告中的前两次生成。
可选 --report 指定第四课报告，--all 展示全部生成；相对路径从学习目录计算。
"""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "output" / "generation-parameters" / "experiment-20261003-175558-459618.json"


def generation_entries(report):
    if not isinstance(report, dict) or not isinstance(report.get("entries"), list):
        raise ValueError("此脚本只支持第四课带 entries 列表的报告，不支持单轮 turn-*.json。")
    entries = []
    for entry in report["entries"]:
        if not isinstance(entry, dict):
            raise ValueError("报告条目不是对象，无法可靠读取。")
        if entry.get("kind") != "model_generation":
            continue
        if not isinstance(entry.get("result"), dict):
            raise ValueError("生成条目缺少 result 对象，不能当成有效生成结果。")
        entries.append(entry)
    return entries


def number(value, unit="", digits=3):
    # 不能把缺失值、布尔值或异常数值冒充测得的 0。
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "未记录"
    if not math.isfinite(value) or value < 0:
        return "无效数值"
    return f"{value:.{digits}f}{unit}"


def completion_label(result):
    answer = result.get("answer")
    has_answer = isinstance(answer, str) and bool(answer.strip())
    reason = result.get("done_reason")
    if reason == "length":
        return "达到长度限制；检查正文是否被截断"
    if reason == "stop" and has_answer:
        return "正常结束且有正文；不代表内容正确"
    if reason == "stop":
        return "正常停止，但没有正式正文"
    return "未确认正常结束；检查原始记录"


def render_report(report, *, show_all=False):
    entries = generation_entries(report)
    selected = entries if show_all else entries[:2]
    lines = ["第 5 课：查看已有实验，不重新生成",
             f"原实验时间：{report.get('started_at', '未记录')}",
             f"原实验状态：{report.get('status', '未记录')}（不等于所有回答正确）",
             f"模型：{report.get('model', '未记录')}；think={report.get('think', '未记录')}",
             f"报告中有 {len(entries)} 次已记录的真实生成，本次展示 {len(selected)} 次。",
             "应用层上下文裁剪演示不计入真实生成。"]
    if not entries:
        lines.append("没有真实生成记录；可能只运行了离线裁剪，也可能在请求前失败，请核对原实验状态。")
    for index, entry in enumerate(selected, start=1):
        result = entry["result"]
        case = entry.get("case") if isinstance(entry.get("case"), dict) else {}
        lines.extend(["", f"--- {index}. {case.get('label', '未命名实验')} ---",
                      f"结束原因：{result.get('done_reason', '未记录')}；{completion_label(result)}",
                      f"原 complete 标记：{result.get('complete', '未记录')}",
                      f"实际生成数：{number(result.get('generated_tokens_including_thinking'), ' token', 0)}",
                      f"首个生成片段：{number(result.get('first_generated_chunk_seconds'), ' 秒')}",
                      f"首个正式答案片段：{number(result.get('first_answer_chunk_seconds'), ' 秒')}",
                      f"客户端总耗时：{number(result.get('client_total_seconds'), ' 秒')}",
                      f"服务端生成阶段速度：{number(result.get('decode_tokens_per_second'), ' token/s', 2)}",
                      "内容质量：待人工检查；没有从 complete 或 stop 自动判定正确。",
                      "原始正式回答：",
                      result.get("answer") if isinstance(result.get("answer"), str) else "未记录"])
    lines += ["", "这只是读取旧报告；没有测量当前电脑速度，也没有修改原始结果。",
              "检查顺序：结束情况 → 任务要求和事实 → 首片等待、生成速度、总耗时。"]
    return "\n".join(lines)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    path = args.report if args.report.is_absolute() else ROOT / args.report
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            report = json.load(file)
        print(f"读取文件：{path}")
        print(render_report(report, show_all=args.all))
        return 0
    except (OSError, ValueError) as error:
        print(f"无法读取实验：{error}。请核对第四课报告路径。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
