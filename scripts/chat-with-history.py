"""第 2 课：PyCharm 直接运行，输入问题后回车，可以连续对话。

先读 main() 中标记 ①②③ 的位置。/history 查看历史，/clear 清空，/exit 退出。
只使用 Python 标准库和本机已安装模型，每次运行从空历史开始。
"""

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


MODEL = "qwen3:1.7b"
# Qwen3 支持关闭思考生成。本课先练短对话，不把等待思考作为学习重点。
THINK = False
BASE_URL = "http://127.0.0.1:11434"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output" / "chat-with-history"
OPTIONS = {"num_ctx": 4096, "num_predict": 1024, "num_thread": 4,
           "num_gpu": 0, "temperature": 0.6, "seed": 42}
CLIENT = build_opener(ProxyHandler({}))


def prepare_messages(history, question):
    """历史过长时按完整问答轮次裁剪；字节估计只是本课的保守近似。"""
    messages = history + [{"role": "user", "content": question}]
    budget = OPTIONS["num_ctx"] - OPTIONS["num_predict"] - 128
    removed = 0
    while sum(len(m["content"].encode("utf-8")) + 32 for m in messages) > budget:
        if len(messages) == 1:
            raise ValueError("这个问题超过本课的输入预算，请先拆成简短问题。")
        messages = messages[2:]  # 一起移除最早的 user 和 assistant 消息
        removed += 1
    return messages, removed


def ask_model(messages):
    """发送完整消息列表，拼接流式回答；这部分沿用上一课的调用方式。"""
    payload = {"model": MODEL, "messages": messages, "stream": True, "think": THINK,
               "keep_alive": "5m", "options": OPTIONS.copy()}
    request = Request(BASE_URL + "/api/chat",
                      data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
    start = time.perf_counter()
    first_generated = None
    first_answer = None
    thinking_seen = False
    last_progress = 0.0
    answer_parts = []
    final = None
    print("正在请求本机模型……", flush=True)
    with CLIENT.open(request, timeout=180) as response:
        for line in response:
            if not line.strip():
                continue
            chunk = json.loads(line)
            if chunk.get("error"):
                raise RuntimeError(chunk["error"])
            message = chunk.get("message", {})
            thinking = message.get("thinking", "")
            content = message.get("content", "")
            elapsed = time.perf_counter() - start
            if (thinking or content) and first_generated is None:
                first_generated = round(elapsed, 3)
            if thinking and not thinking_seen:
                print("模型正在生成思考内容，等待正式回答……", flush=True)
                thinking_seen = True
                last_progress = elapsed
            elif thinking and first_answer is None and elapsed - last_progress >= 10:
                print(f"仍在思考，已等待 {elapsed:.0f} 秒……", flush=True)
                last_progress = elapsed
            if content:
                if first_answer is None:
                    first_answer = round(elapsed, 3)
                    print("\n模型：", end="", flush=True)
                print(content, end="", flush=True)
                answer_parts.append(content)
            if chunk.get("done"):
                final = chunk
                break
    if final is None:
        raise RuntimeError("流式响应中断，本轮不加入历史。")
    answer = "".join(answer_parts)
    generated = final.get("eval_count", 0)
    duration = final.get("eval_duration", 0)
    rate = round(generated * 1e9 / duration, 2) if duration else None
    elapsed = round(time.perf_counter() - start, 3)
    # 正常停止且有正式回答，才作为后续对话的历史；这不代表内容一定正确。
    complete = final.get("done_reason") == "stop" and bool(answer.strip())
    result = {
        "answer": answer, "complete": complete,
        "done_reason": final.get("done_reason"), "client_total_seconds": elapsed,
        "first_generated_chunk_seconds": first_generated,
        "first_answer_chunk_seconds": first_answer,
        "generated_tokens_including_thinking": generated,
        "decode_tokens_per_second": rate, "thinking_output_present": thinking_seen,
        "prompt_tokens": final.get("prompt_eval_count"),
    }
    print(f"\n\n本轮 {elapsed} 秒；{rate} token/s；结束原因：{result['done_reason']}")
    if not complete:
        print("本轮没有完整正式答案，不加入后续历史。请缩短问题后重试。")
    return payload, result


def save_record(payload, result, removed):
    """记录这次实际发送的 messages，便于学习；重启时不会自动恢复它。"""
    now = datetime.now(timezone(timedelta(hours=8)))
    record = {"measured_at": now.isoformat(), "request": payload,
              "result": result, "removed_old_turns": removed}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"turn-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    with path.open("x", encoding="utf-8") as file:
        json.dump(record, file, ensure_ascii=False, indent=2)
    print(f"本轮记录：{path}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"第 2 课：连续对话 | 本地模型 {MODEL}")
    print(f"思考生成：{'开启' if THINK else '关闭'}（请求字段 think）")
    print("输入问题后回车；/history 查看历史；/clear 清空历史；/exit 退出。")
    print("每轮问题、发送的历史和正式回答会记录到学习目录 output/chat-with-history。")
    history = []  # ① 当前进程保存对话；重新运行时从空列表开始
    while True:
        try:
            question = input("\n你：").strip()
        except EOFError:
            print("\n输入结束，退出。")
            break
        if not question:
            continue
        if question.lower() == "/exit":
            print("已退出。")
            break
        if question.lower() == "/clear":
            history.clear()
            print("对话历史已清空，下一轮不会携带旧消息。磁盘上的实验记录仍保留。")
            continue
        if question.lower() == "/history":
            print(json.dumps(history, ensure_ascii=False, indent=2))
            continue
        try:
            # ② 准备本次消息：此前完整问答 + 当前问题
            messages, removed = prepare_messages(history, question)
            if removed:
                print(f"为控制上下文，本次省略最早 {removed} 轮问答。")
            print(f"本次发送 {len(messages)} 条消息，包含 {len(messages) // 2} 轮历史。")
            payload, result = ask_model(messages)
            if result["complete"]:
                # ③ 正式回答标记为 assistant，一起留给下一轮
                history = messages + [{"role": "assistant", "content": result["answer"]}]
            try:
                save_record(payload, result, removed)
            except OSError as error:
                print(f"回答已接收，但记录保存失败：{error}")
        except HTTPError as error:
            print(f"本地服务错误 {error.code}：{error.read().decode('utf-8', errors='replace')}")
        except (URLError, OSError) as error:
            print(f"连接或读取本机模型失败：{error}。请确认 Ollama 已启动。")
        except (ValueError, RuntimeError) as error:
            print(f"本轮未完成：{error}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已中断并退出；未完成的回答不会进入下一轮历史。")
