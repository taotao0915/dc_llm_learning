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

## 运行练习

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
- 用户自己重复运行练习的结果尚未反馈，不能记为已完成。
- 下一课：理解 Python 请求中的 `model`、`messages`、`role`、`content`，逐步加入多轮历史。

## 目录约定

```text
dc_llm_learning/
├── README.md
├── AGENTS.md
├── docs/                   # 概念讲义、配置记录、课程笔记
├── scripts/                # 可运行练习
└── output/local-model-lab/  # 原始实验记录及后续报告
```

更新代码、模型或参数后产生的新结果另存文件，保留第一次和第二次实验记录作为历史基准。
