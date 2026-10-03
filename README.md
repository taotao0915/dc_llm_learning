# 端侧大模型学习资料

本目录是用户指定的学习资料统一存放位置：

`F:\Software\JetBrains\PyCharm\PycharmProjects\20260624\dc_llm_learning`

2026 年 10 月 2 日整理迁入。后续讲义、代码练习和实验报告继续放在这里。

## 从这里开始

1. [基础概念与完整学习路线](docs/FOUNDATIONS_AND_ROADMAP.md)：回顾端侧推理、参数量、量化、Token、KV Cache 等概念。
2. [电脑配置与选型判断](docs/HARDWARE_ASSESSMENT.md)：此前实测硬件及适用模型规模。
3. [电脑端第 1 课：本地推理](docs/LESSON_PC_01_LOCAL_INFERENCE.md)：真实实验、逐步命令、参数解释与练习。
4. [Python 练习代码](scripts/local-model-lab.py)：调用本机 Ollama，显示流式回答和耗时。
5. [第一次实验记录](output/local-model-lab/first-run.json) / [第二次实验记录](output/local-model-lab/second-run.json)：2026 年 10 月 1 日的原始测量结果。
6. [电脑端第 2 课：请求字段与多轮历史](docs/LESSON_PC_02_MESSAGES_AND_HISTORY.md)：理解 `model/messages/role/content`。
7. [连续对话练习](scripts/chat-with-history.py)：PyCharm 直接运行，一次启动可以连续提问。
8. [第二课真实验证记录](docs/LESSON_PC_02_EXPERIMENTS.md)：两组短对话的实际结果，包含成功与错误样例。
9. [英文名字失败的诊断](docs/LESSON_PC_02_NAME_RECALL_DIAGNOSIS.md)：为什么历史已经传入，仍可能答错。
10. [Qwen3 验证与重新练习](docs/LESSON_PC_02_QWEN_VALIDATION.md)：2026-10-03 的模型更换结果、关键代码与逐步操作。

## 运行练习

当前正在学第二课，请优先运行 `scripts/chat-with-history.py`（Qwen3，关闭思考生成）。
下面的单轮脚本仍保留 DeepSeek，便于回看第一课；两个文件的默认模型现在不同。

推荐直接在 PyCharm 中运行：

1. 打开 `scripts/local-model-lab.py`，右键选择 Run，或使用该文件的绿色运行按钮。
2. 在下方 Run（运行）控制台输入问题并回车。直接回车会使用“1加1等于几？请简短回答。”。
3. 等待模型思考后显示回答，末尾会显示速度、耗时和报告路径。

不需要额外填写运行参数。若之前在运行配置中填写过 `--prompt` 或 `--max-tokens 256`，
请清空该配置的 Parameters，让脚本使用新的交互输入及默认 1024 token 上限。
一次运行只处理一个问题；再次点击运行可以问新问题，目前不保存多轮对话历史。
报告会自动按时间保存到 `output/local-model-lab/`，保留旧实验记录。
1024 是上限，不是每次必须生成的数量，也不保证任意问题都会在上限内完成。

也可以继续使用命令行：

```powershell
Set-Location 'F:\Software\JetBrains\PyCharm\PycharmProjects\20260624\dc_llm_learning'
python scripts/local-model-lab.py --prompt '1加1等于几？' --max-tokens 512 --report output/local-model-lab/my-run.json
```

运行前启动 Ollama，确认 `ollama list` 能看到 `deepseek-r1:1.5b`。
脚本只使用 Python 标准库，无需额外安装包。相对报告路径按本目录解析。
在 PyCharm 中打开此目录，解释器可使用此前检测到的
`F:\Software\Python\Python312\python.exe`；工作目录设为本目录。

本次迁移的是学习资料和练习代码。Python、Ollama 的现有安装和 Ollama 管理的模型缓存仍由原来的软件管理，未迁移或修改它们的配置。

## 当前进度

- 已讲解基础概念、模型内存估算和学习路线。
- 已读取电脑配置，完成初始模型选型判断。
- 已由助手执行两次本地 CPU 推理实验，并保存结果。
- 已讲解输出预算、思考内容、首个片段、正式答案、速度和质量检查。
- 用户已理解“推理需要计算时间”；本课进一步区分前置思考生成与正式答案生成。
- 用户已自己运行脚本，并反馈 256 token 预算耗尽、没有正式答案的日志。
- 已讲解默认参数与命令行参数的区别；2026-10-02 改为 PyCharm 控制台输入、默认 1024 token、自动保存新报告。
- 用户已实践第二课，反馈中文和英文名字都出现错误；诊断确认相关请求携带了历史，并非漏发消息或输出预算耗尽。
- 原先英文名字的一次成功不代表可靠复现，后续真实失败与诊断记录均已保留。
- 第二课现有 6 项离线检查，验证历史携带、裁剪、清空、流式拼接、失败轮次隔离和模型/思考字段；这些检查不代替真实模型效果评测。
- 2026-10-03 助手下载并重复测试 Qwen3-1.7B 非思考模式；详见新验证讲义。用户对新配置的亲自练习尚待反馈，尚未进入下一课。

## 第二课怎么运行

启动 Ollama，确认 `ollama list` 中有 `qwen3:1.7b`。本机已由助手下载，通常不需要再次下载。
停止旧的运行进程再重新 Run；顶部应显示 `本地模型 qwen3:1.7b` 和 `思考生成：关闭`。

在 PyCharm 中打开 `scripts/chat-with-history.py` 并右键 Run，依次输入：

```text
我叫小林。请只回复：你好，小林。
我叫什么名字？请只回答名字。
/history
/clear
/history
/exit
```

每次提问后等待回答完成，再输入下一条。正式回答与实际发送的消息会逐轮保存在 `output/chat-with-history/`。
这一课的 `/clear` 清空本轮会话内存，磁盘上的实验记录仍保留；重新运行不会自动恢复旧历史。

如需重复助手的小型真实评测，可以运行 `scripts/evaluate-name-recall.py`。
它会真实调用模型 24 次（6 个名字，每个重复 2 次，每次 2 轮），保存报告到 `output/name-recall/`；
这是可选的复现实验，初学时先完成上面的手动对话即可。

离线检查（无需启动 Ollama）：

```powershell
python -B -m unittest discover -s tests -v
```

## 目录约定

```text
dc_llm_learning/
├── README.md
├── AGENTS.md
├── docs/                   # 概念讲义、配置记录、课程笔记
├── scripts/                # 可运行练习
├── tests/                  # 练习程序的离线检查
└── output/                 # 第一课及连续对话的实验记录
```

更新代码、模型或参数后产生的新结果另存文件，保留第一次和第二次实验记录作为历史基准。
