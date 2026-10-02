# 第二课补充：英文名字也回答错误的排查

记录日期：2026-10-02。用户反馈英文名字样例不能正确回答，本次仅诊断，没有永久修改练习代码或替换模型。

## 用户记录中的事实

最近一次失败见 [21:20 的实验记录](../output/chat-with-history/turn-20261002-212003-309169.json)。
请求包含完整的三条消息：

```text
user: My name is Alice. Reply with only OK.
assistant: OK
user: What is my name? Reply with only the name.
```

模型实际回答：`I'm an AI, so I don't have a name.`

- `removed_old_turns=0`：没有发生历史裁剪。
- 输出上限 1024，实际生成 273 token，`done_reason=stop`：没有耗尽输出预算。
- `complete=true`：当前代码只据此判定正常结束且有正式文本，不判定答案事实正确。
- 模型为 `deepseek-r1:1.5b`，上下文 4096，CPU 4 线程，temperature=0.6，seed=42。
- [20:40 的另一次记录](../output/chat-with-history/turn-20261002-204045-233409.json)也出现了相同错误。

将其与此前回答 Alice 的 [18:12 记录](../output/chat-with-history/turn-20261002-181208-712995.json)比较，保存的 request 内容完全一致，服务报告的输入 token 数都为 29。
不同运行的输出却不同。固定 seed 不构成跨所有推理运行状态的绝对复现保证；本次没有进一步隔离造成差异的具体底层因素。

## 两项临时诊断请求

直接调用本机接口，仍使用相同模型，均设置 `stream=false` 以收集完整返回。
只对临时请求修改字段，磁盘上的脚本 OPTIONS 保持原样。

| 对照 | 设置与问题 | 实际结果 |
|---|---|---|
| A | 完整三条历史保持原样，temperature 改为 0 | `I'm Alice.`；正常停止；199 token；53.782 秒 |
| B | temperature=0.6，改为单条用户消息：The user previously said: My name is Alice. What is the user name? Reply with only the name. | `The username corresponding to the name "Alice" is "alice".`；正常停止；470 token；76.849 秒 |

A 这一次包含了正确名字，但没有严格只输出名字；不能据此断言温度调为 0 就能稳定解决。
B 把事实放到当前消息中，但回复把名字解释成用户名，仍然没有遵循只回答名字的要求；其问题措辞本身也可能诱发这种解释，因此不是严格的历史机制单变量对照。

## 能确认和不能确认的内容

已确认应用层正确准备并发送了历史；用户没有因为漏传参数、未保存历史或预算不足造成这次错误。
当前模型与推理设置组合不能稳定完成这个名字问答样例。
尚不能仅凭这些日志，把底层原因完全归为参数量、量化精度、聊天模板、缓存实现或某一个采样参数。

DeepSeek 官方说明该 1.5B 蒸馏模型基于 Qwen2.5-Math-1.5B；对 R1 系列推荐 temperature=0.5～0.7（推荐 0.6），并建议重复评测。
因此本次 temperature=0 是诊断条件，不是官方通用推荐，也未永久改入代码。

## 对课程的修正

此前助手的英文样例属于一次成功的实测，不代表能稳定复现。实际教学不应让用户靠反复重跑来等待一次成功。
可保留当前脚本学习消息结构；后续更合理的工作是选另一款通用指令模型作对照，重复验证中文、英文和不同名字，再确定课程默认模型。
最初计划的 Qwen3-1.7B 可以作为候选，本次尚未下载或测试它，不能宣称已经解决。

参考：[DeepSeek 模型卡](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B)、[官方使用建议](https://github.com/deepseek-ai/DeepSeek-R1#usage-recommendations)。
