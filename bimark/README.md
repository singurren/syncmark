# 基于大语言模型的鲁棒隐写与水印框架

## 项目简介
本项目是一个针对大型语言模型 (LLM) 的文本水印研究原型系统。旨在通过在模型生成过程中嵌入不可见的隐式水印，解决 AI 生成内容的版权追踪与溯源问题。该系统实现了一种基于 Logits 偏置的算法，能够在保证文本流畅度（低困惑度）的同时，嵌入高容量的比特信息，并具备一定的抗攻击能力。

## 核心功能

*   **隐式水印嵌入 (Invisible Embedding)**: 通过自定义 `LogitsProcessor` 介入 Transformer 的推理过程，利用基于上下文的伪随机函数 (PRF) 对词表进行划分和概率加权，实现无感的比特信息嵌入。
*   **多比特信息负载 (Multi-bit Payload)**: 不同于简单的二元检测水印，本框架支持嵌入具体的数字签名或 ID 信息（如 8-bit, 16-bit, 32-bit 负载）。
*   **纠错编码增强 (ECC Integration)**: 集成了 Hamming Code (7,4) 和 Reed-Solomon 纠错码机制，显著提升了水印在文本被部分修改或截断情况下的提取准确率。
*   **鲁棒性评估**: 内置完整的实验评估管线，支持测试不同文本长度、不同水印强度以及受到不同程度攻击（如随机替换、删除）下的检测率 (Hit Rate) 和误码率 (BER)。

## 技术栈

*   **核心框架**: Python, PyTorch, Hugging Face Transformers
*   **算法实现**: 密码学伪随机数生成, Logits 分布操作, 纠错编码算法
*   **数据分析**: Pandas, Matplotlib/Seaborn (用于实验结果的可视化分析)

## 项目结构

*   `WatermarkBimark.py`: 核心水印类实现，继承自 Transformers 的 `LogitsProcessor`，负责生成时的概率调整。
*   `generate_text_dump.py`: 批量生成带水印文本的脚本，支持配置不同的消息长度和编码策略。
*   `detect_watermark_dump.py`: 水印提取与验证脚本，计算比特错误率 (BER) 和提取准确度。

## 快速开始

### 1. 环境配置
本仓库统一使用根目录的 [uv](https://docs.astral.sh/uv/) 项目进行包管理。不要在 `bimark/` 子目录维护独立环境；所有 BiMark 命令都从仓库根目录执行。

```bash
cd /srv/scratch/z5542506/syncmark
uv sync
```

### 2. 生成带水印文本
使用指定的配置（如 16-bit 消息，使用 Hamming 纠错）生成文本：
```bash
uv run python bimark/generate_text_dump.py \
  --model_name gpt2 \
  --message 0000000000000000 \
  --ecc_method hamming74 \
  --num_test 10 \
  --batch_size 2
```

### 3. 检测与评估
生成脚本会打印 `AUTOMATION_OUTPUT_DIR:<目录名>`。对该目录运行水印提取和正确率检测：
```bash
uv run python bimark/detect_generation_text_dump.py \
  --data_dir <AUTOMATION_OUTPUT_DIR> \
  --detect
```

### 4. 结果分析
运行分析脚本以评估水印系统在不同条件下的表现：
```bash
uv run python bimark/katana/analyze_full_experiment.py
```

### 5. Katana CUDA 环境

当前根环境中的 PyTorch wheel 是 CUDA 13.0 build。提交 GPU PBS 作业时加载匹配的 CUDA module，并把 `uv` cache 指向可写目录：

```bash
module load cuda/13.0.0
export UV_CACHE_DIR="/tmp/${USER}/uv-cache"
uv run python -c 'import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())'
```

## 实验结果示例
在研究过程中，我们对比了引入 ECC 前后的性能差异。实验数据显示，在面临 20% 程度的文本扰动攻击下，引入 Reed-Solomon 编码的方案能够将信息提取成功率提升约 15-20%，同时对文本困惑度 (PPL) 的影响控制在可接受范围内。
