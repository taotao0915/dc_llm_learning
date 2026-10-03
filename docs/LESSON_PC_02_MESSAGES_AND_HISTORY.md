# 电脑端第 2 课：看懂请求，让模型连续对话

这一课只掌握四个字段和一件事：`model`、`messages`、`role`、`content`，以及怎样把上一轮对话带进下一轮请求。
第一课的单轮实验脚本继续保留，本课使用新的 `scripts/chat-with-history.py`。

2026-10-03 更新：本课改用已下载的 `qwen3:1.7b`，并用 `think=False` 关闭思考生成。
旧 DeepSeek 试验的成功与失败记录保持原样，参见 [模型更换验证与练习](LESSON_PC_02_QWEN_VALIDATION.md)。

## 1. 先提出一个问题

第一轮告诉模型：“我叫小林。”第二轮再问：“我叫什么名字？”

如果第二轮只发送“我叫什么名字？”，请求中没有名字信息，模型就缺少回答依据。
如果程序把第一轮的问答一起发送，模型可以从这些上下文中读到“小林”。

本课演示的对话记忆来自程序保存并重新发送的文本；没有重新训练模型，也没有修改模型权重。
本地服务可能复用计算缓存，但程序仍应明确发送它希望模型参考的消息列表。

## 2. 在 PyCharm 直接运行

1. 确保 Ollama 已启动。
2. 在工程中打开 `scripts/chat-with-history.py`，右键 Run。
3. 在下方 Run 控制台输入：`我叫小林。请只回复：你好，小林。`
4. 等待完整回答结束，程序会再次显示 `你：`。
5. 输入：`我叫什么名字？请只回答名字。`
6. 再输入 `/history`，观察保存的消息。
7. 输入 `/clear`，然后输入 `/history`，应该看到空列表 `[]`。
8. 输入 `/exit` 退出。

这是练习过程，不承诺模型每次措辞相同。小模型也可能回答错误，记录真实结果即可。

注意运行顶部选择的是本课文件，不是第一课脚本。所有问题都在 Run 控制台输入，而不是 Python 源代码编辑区。
本课无需填写运行参数、无需安装额外 Python 包。

## 3. 先认识 Python 的两种容器

花括号 `{}` 创建字典，可以保存“字段名 → 值”的对应关系：

```python
message = {"role": "user", "content": "我叫小林。"}
```

这里 `role` 对应 `user`，`content` 对应一段文字。

方括号 `[]` 创建列表，可以按顺序保存多条消息：

```python
messages = [
    {"role": "user", "content": "我叫小林。"},
    {"role": "assistant", "content": "你好，小林。"},
]
```

字典描述“一条消息长什么样”，列表描述“有多少条消息，顺序是什么”。

## 4. 四个字段各负责什么

| 字段 | 通俗解释 | 本课示例 |
|---|---|---|
| `model` | 请哪个模型来回答 | `qwen3:1.7b` |
| `messages` | 本次交给模型的对话记录 | 一个按顺序排列的列表 |
| `role` | 这一句话是谁说的 | `user` 或 `assistant` |
| `content` | 这一句话说了什么 | `我叫小林。` |

`user` 表示用户消息，`assistant` 表示模型正式回答。
接口还存在其他角色，例如用于应用指令的 `system`；这节课先掌握前两种。

把一句话的 `role` 改成 `assistant`，并不会触发一次模型生成，它只是把这句话标记为历史中的助手发言。
模型新回答需要通过发送请求获得。

## 5. 两轮请求具体长什么样

第一轮发送的核心内容（下面是 Python 字典）：

```python
payload = {
    "model": "qwen3:1.7b",
    "messages": [
        {"role": "user", "content": "我叫小林。"}
    ],
    "stream": True,
    "think": False,
}
```

假设第一轮回答是“你好，小林。”，第二轮需要发送：

```python
payload = {
    "model": "qwen3:1.7b",
    "messages": [
        {"role": "user", "content": "我叫小林。"},
        {"role": "assistant", "content": "你好，小林。"},
        {"role": "user", "content": "我叫什么名字？"},
    ],
    "stream": True,
    "think": False,
}
```

第二轮有 3 条消息：上一轮用户消息、上一轮助手消息、本轮用户问题。
因此程序会显示“本次发送 3 条消息，包含 1 轮历史”。
`stream: True` 表示逐步接收生成内容，不是把历史保存到服务端的开关。
`think: False` 表示本课请求 Qwen3 不生成独立的思考内容；仍然需要计算，并非不做推理。
它与 `model`、`messages` 同层，不应放在 `options` 里面。Python 写 `False`，序列化为 JSON 后写作 `false`。

## 6. 先看懂程序的核心循环

下面只展示关键逻辑，完整脚本还处理了流式响应、错误、预算和记录保存：

```python
history = []

while True:
    question = input("你：")
    messages = history + [{"role": "user", "content": question}]
    payload, result = ask_model(messages)
    if result["complete"]:
        history = messages + [{"role": "assistant", "content": result["answer"]}]
```

按顺序解释：

1. `history = []`：准备一份空对话记录，必须放在循环外，否则每次提问前都被清空。
2. `while True`：回答完后继续等待下一个问题。
3. `input()`：从 PyCharm 控制台取得你输入的文字。
4. `history + [...]`：把旧消息与这次的问题拼成新列表。
5. `ask_model(messages)`：把列表送给本机模型，接收回答。
6. 将回答标记为 `assistant`，与前面的消息一起保存，供下一轮使用。

“保存历史”先发生在当前 Python 进程的变量中，不等于长期记忆或自动恢复会话。
完整程序对预算超限、清空和退出有处理，学习时先关注 main() 中标记 ①②③ 的代码。

## 7. 从 Python 字典到模型，中间还有什么

Python 不能把内存中的字典对象原封不动送给另一个程序，需要先序列化：

```python
data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
```

- `json.dumps`：把字典转换为 JSON 文本。
- `ensure_ascii=False`：保留中文字符，方便观察。
- `.encode("utf-8")`：把文本转换成 HTTP 请求可以发送的字节。

随后发送到 `http://127.0.0.1:11434/api/chat`。
其中 `127.0.0.1` 是本机，`11434` 是端口，`/api/chat` 是聊天接口路径。
脚本通过 HTTP POST 发送这些数据。

流式响应不是一个完整的大 JSON，而是逐行返回的 JSON 对象。
程序对每行执行 `json.loads(line)`，取出 `message.content`，边接收边显示并拼接。
模型返回的 `message.thinking` 用于显示等待状态，其正文不存入下一轮的聊天历史。
当前默认关闭思考生成；相关解析代码仍保留，以兼容之后的思考模式实验。

## 8. 两种不同的记录

| 记录 | 在哪里 | 用途 | 重启后如何处理 |
|---|---|---|---|
| `history` 列表 | Python 进程内存 | 下一轮重新发送给模型 | 重新运行后从空列表开始 |
| 每轮 JSON 文件 | `output/chat-with-history/` | 查看实际请求、回答和耗时 | 保留，但本课不会自动加载 |

`/history` 查看的是内存列表；`/clear` 清空的是内存列表，不删除已保存的实验文件。
JSON 中 `request.messages` 能准确展示本次模型收到哪些消息；`result.answer` 是正式回答。
不完整但正常返回的生成也会保存实验记录，`result.complete` 为 false，并且不会加入下一轮历史。
网络断流会提示错误，不把缺少结束标记的响应当成完整回答。

## 9. 为什么没有无限保存所有消息

模型的上下文空间有限，历史越长，输入处理通常也越费时间和内存。
本课把上下文从第一课的 2048 调到 4096，为短多轮对话留出空间；输出上限仍为 1024。
因此本课的速度不能直接当成第一课相同配置下的对照数据。

代码用 UTF-8 字节数加上消息开销做保守预算估计，为输出预留空间，超出时按“用户 + 助手”完整轮次移除最早的历史，并在控制台提示。
这不是模型原生 tokenizer 的精确 token 计数，可能提前丢掉本可容纳的历史；后面的性能课再深入精确计数。

被裁剪掉的信息，后续请求中就没有了。先用短句练习，观察 messages 的变化。
`complete=True` 只表示正常结束且有正式文本，不表示回答事实正确。

## 10. 自己验证是否理解

1. 第二轮为什么发送 3 条消息，而不是只发送最新问题？
2. 如果把 `history = []` 放到 while 循环里面，会发生什么？
3. `/clear` 之后 `/history` 输出 `[]`，为什么磁盘上仍有 JSON 文件？

下一课可以继续学习如何把请求、流式输出和对话历史拆成更容易维护的函数，并进一步理解生成参数。

参考：[Ollama Chat API](https://docs.ollama.com/api/chat)。
