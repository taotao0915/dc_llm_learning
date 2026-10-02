"""第一课：用 Python 标准库调用本机 Ollama，观察流式输出和耗时。

运行：python scripts/local-model-lab.py
此脚本只连接 127.0.0.1，不下载模型，不调用云端服务。
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


BASE_URL = "http://127.0.0.1:11434"
# 本地请求直接连接，不经过系统 HTTP 代理。
CLIENT = build_opener(ProxyHandler({}))


def request(path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    return CLIENT.open(
        Request(BASE_URL + path, data=data, headers={"Content-Type": "application/json"}),
        timeout=180,
    )


def get_json(path, body=None):
    with request(path, body) as response:
        return json.load(response)


def seconds(nanoseconds):
    return round(nanoseconds / 1_000_000_000, 3)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="deepseek-r1:1.5b")
    parser.add_argument("--prompt", default="请用一句简短的中文解释什么是端侧大模型。")
    parser.add_argument("--threads", type=int, choices=range(1, 9), default=4)
    parser.add_argument("--max-tokens", type=int, default=256, metavar="N", help="输出上限，范围 1～1024，默认 256")
    parser.add_argument("--report", type=Path, help="可选：将实验结果保存为 JSON 文件")
    args = parser.parse_args()
    if not 1 <= args.max_tokens <= 1024:
        parser.error("--max-tokens 必须在 1～1024 之间。")
    # 相对报告路径始终以学习目录为起点，避免 PyCharm 的工作目录改变保存位置。
    if args.report and not args.report.is_absolute():
        args.report = Path(__file__).resolve().parents[1] / args.report

    # 先确认模型已经下载，避免初次实验意外拉取一个大模型。
    installed = get_json("/api/tags")["models"]
    if args.model not in [item["name"] for item in installed]:
        parser.error(f"本机尚未安装 {args.model}，请先用 ollama list 查看已有模型。")
    loaded_before = get_json("/api/ps")["models"]
    details = get_json("/api/show", {"model": args.model})
    options = {
        "num_ctx": 2048,       # 输入、历史和输出共享的上下文预算
        "num_thread": args.threads,
        "num_gpu": 0,          # 固定 CPU，便于建立性能基准
        "num_predict": args.max_tokens,
        "temperature": 0.6,
        "seed": 42,
    }
    body = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "stream": True,        # 一边生成，一边接收，不等整段答案完成
        "keep_alive": "5m",  # 方便下一次实验复用已加载的模型
        "options": options,
    }
    print(f"模型：{args.model}\n问题：{args.prompt}", flush=True)
    print("正在请求本机模型……", flush=True)
    started = time.perf_counter()
    first_generated = None
    first_answer = None
    thinking_seen = False
    answer = []
    final = None
    with request("/api/chat", body) as response:
        # Ollama 的流式响应每行是一个 JSON 对象，不是一个完整的大 JSON。
        for line in response:
            if not line.strip():
                continue
            chunk = json.loads(line)
            if chunk.get("error"):
                raise RuntimeError(chunk["error"])
            message = chunk.get("message", {})
            thinking = message.get("thinking", "")
            content = message.get("content", "")
            elapsed = time.perf_counter() - started
            if (thinking or content) and first_generated is None:
                first_generated = round(elapsed, 3)
            if thinking and not thinking_seen:
                print("模型正在生成思考内容，等待正式答案……", flush=True)
                thinking_seen = True
            if content:
                if first_answer is None:
                    first_answer = round(elapsed, 3)
                    print("\n模型回答：", flush=True)
                print(content, end="", flush=True)
                answer.append(content)
            if chunk.get("done"):
                final = chunk
                break
    wall_seconds = round(time.perf_counter() - started, 3)
    if final is None:
        raise RuntimeError("响应在结束标记到达前中断，本次不能算成功完成。")
    eval_ns = final.get("eval_duration", 0)
    token_count = final.get("eval_count", 0)
    rate = round(token_count * 1_000_000_000 / eval_ns, 2) if eval_ns else None
    report = {
        "measured_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "ollama_version": get_json("/api/version").get("version"),
        "model": args.model,
        "model_details": details.get("details"),
        "options": options,
        "prompt": args.prompt,
        "answer": "".join(answer),
        "model_loaded_before_request": any(m["name"] == args.model for m in loaded_before),
        "first_generated_chunk_seconds": first_generated,
        "first_answer_chunk_seconds": first_answer,
        "client_total_seconds": wall_seconds,
        "server_load_seconds": seconds(final.get("load_duration", 0)),
        "prompt_tokens": final.get("prompt_eval_count"),
        "server_prefill_seconds": seconds(final.get("prompt_eval_duration", 0)),
        "generated_tokens_including_thinking": token_count,
        "server_decode_seconds": seconds(eval_ns),
        "decode_tokens_per_second": rate,
        "done_reason": final.get("done_reason"),
        "thinking_output_present": thinking_seen,
        "loaded_models_after_request": get_json("/api/ps")["models"],
    }
    first_answer_text = "未收到" if first_answer is None else f"{first_answer} 秒"
    print(f"\n\n首个生成片段：{first_generated} 秒；正式答案首片：{first_answer_text}")
    print(f"生成：{token_count} token；生成速度：{rate} token/s；总耗时：{wall_seconds} 秒")
    print(f"结束原因：{report['done_reason']}")
    if not answer:
        print("没有收到正式答案：思考可能已用完输出预算，可尝试 --max-tokens 512。")
    elif report["done_reason"] == "length":
        print("已达到输出上限，答案可能尚未写完。")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"报告：{args.report.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        print(f"本地服务返回错误 {error.code}：{error.read().decode('utf-8', errors='replace')}", file=sys.stderr)
        sys.exit(1)
    except (URLError, OSError, RuntimeError, ValueError) as error:
        print(f"实验未完成：{error}。请确认 Ollama 已启动，且 ollama list 可用。", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n已中断本次实验。", file=sys.stderr)
        sys.exit(130)
