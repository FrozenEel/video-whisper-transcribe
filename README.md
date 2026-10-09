# video-whisper-transcribe

把视频或音频转成带时间戳的文字稿，用 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 在本地识别，不上传任何内容。输入可以是网址（YouTube、B 站、播客等，凡是 yt-dlp 支持的网站），也可以是本地的 mp4、mp3、m4a、wav 等文件。适合没有字幕的长视频（例如几小时的播客）。

## 安装

```bash
pip install -U yt-dlp faster-whisper numpy
```

另外需要 ffmpeg：macOS 用 `brew install ffmpeg`，Windows 用 `winget install ffmpeg`。

## 用法

```bash
# CPU（慢，但任何电脑都能跑）
python transcribe.py "https://www.youtube.com/watch?v=VIDEO_ID" --model small --device cpu

# 有 NVIDIA 显卡（快、更准）
python transcribe.py "https://www.youtube.com/watch?v=VIDEO_ID" --model large-v3 --device cuda

# 本地文件；换语言用 --lang（如 en、ja）
python transcribe.py "D:/videos/talk.mp4" --lang en

# 先把音频加速再识别，更快，准确率略降（1.0 到 2.0）
python transcribe.py URL --speed 1.5
```

输出在 `out/` 目录（位置见下面的"输出位置"）：

- `transcript.txt`：每行 `[HH:MM:SS] 文字`
- `transcript.srt`：字幕文件

## 输出位置

默认输出到**运行命令时所在文件夹**下的 `out` 子文件夹（`当前目录/out/`），和脚本放在哪里无关。例如在 `C:\Users\你的用户名\Downloads\video-whisper-transcribe` 里运行，结果就在该文件夹下的 `out\`。

`out/` 里有：

- `transcript.txt`、`transcript.srt`：识别结果
- 下载的音频 `audio.m4a`（本地文件不会复制）
- 转换出的 `.pcm` 中间文件（很大，4 小时多的音频可能有几百 MB，识别完可以删除）

用 `--out` 改位置，目录不存在会自动创建：

```bash
python transcribe.py "URL" --out D:\transcripts\podcast1
```

注意：

- 同一个输出目录里再跑新内容，`transcript.txt` 和 `transcript.srt` 会被覆盖。
- 网址的音频固定存成 `out/audio.m4a`，如果已存在就直接复用、不会重新下载。所以**换新视频时请换一个 `--out`，或先删掉旧文件**，否则识别的还是上一个视频。

## 怎么提速

默认是 1.0 倍速（不加速）、`large-v3` 模型、自动选择设备。想更快，按效果从大到小：

1. **用显卡**：`--device cuda`（NVIDIA 显卡）。显卡比 CPU 快一个数量级，通常比其他办法都管用。
2. **换小一点的模型**：`--model medium` 大约快一倍，`--model small` 更快；模型越小，错字越多，专有名词尤其明显。
3. **减小束搜索宽度**：`--beam-size 1`，明显更快，同音词和专有名词更容易写错。
4. **降低计算精度**：显卡上用 `--compute-type float16`，CPU 上用 `--compute-type int8`。
5. **加速音频**：`--speed 1.5`，耗时大约降到三分之二，准确率略降；`--speed 2.0` 大约降到一半，错字会明显增多。范围限制在 1.0 到 2.0。

推荐组合（几乎不损失准确率）：

```bash
python transcribe.py URL --model large-v3 --device cuda --speed 1.25
```

实际耗时取决于显卡和音频长度。

## 说明

- 用 ffmpeg 把音频转成 16kHz 单声道 PCM，再按 30 分钟一段识别，省内存。
- 加速识别时，时间戳会换算回原视频时间。
- Windows 上会自动加入 pip 安装的 CUDA 运行库路径（没装也没关系）。
- 语音识别难免有错字，专有名词尤其容易错，需要人工校对。
- 请只用于你有权处理的内容，并遵守 YouTube 的服务条款和相关版权规定。

## 完整命令模板

```bash
python transcribe.py "<网址或本地文件路径>" --out out --model large-v3 --device cuda --lang zh --speed 1.0 --beam-size 5 --compute-type auto
```

| 参数 | 含义 | 可选值 | 默认 |
|---|---|---|---|
| `<网址或本地文件路径>`（必填） | 要识别的内容 | yt-dlp 支持的网址，或本地 mp4/mp3/m4a/wav 等文件 | 无 |
| `--out` | 输出目录（也存放下载的音频和中间文件） | 任意目录名 | `out` |
| `--model` | 识别模型 | `large-v3`（最准，需显卡）/ `medium` / `small`（CPU 可用）等 faster-whisper 支持的模型 | `large-v3` |
| `--device` | 运行设备 | `auto` / `cuda`（NVIDIA 显卡）/ `cpu` | `auto` |
| `--lang` | 音频语言代码 | `zh` / `en` / `ja` 等 | `zh` |
| `--speed` | 识别前把音频加速的倍数 | 1.0 到 2.0 | `1.0` |
| `--beam-size` | 束搜索宽度，越大越准越慢 | 1 或更大的整数（常用 1 到 5） | `5` |
| `--compute-type` | 计算精度 | `auto` / `float16` / `int8_float16` / `int8` / `float32` | `auto` |

常用写法：

```bash
# 显卡，最准（推荐）
python transcribe.py "URL" --model large-v3 --device cuda --lang zh --speed 1.25

# 显卡，追求速度
python transcribe.py "URL" --model large-v3 --device cuda --compute-type float16 --beam-size 1 --speed 1.5

# 只有 CPU
python transcribe.py "URL" --model small --device cpu --compute-type int8 --lang zh

# 本地英文视频，输出到 my_out
python transcribe.py "D:/videos/talk.mp4" --out my_out --lang en
```

说明：`--lang zh` 时会自动加上"使用简体中文"的提示词，其他语言不加。

## 所有可选项与对应指令

### 速度 `--speed`

范围：1.0 到 2.0 的任意小数（超出范围会直接报错退出）。

| 指令 | 含义 | 建议 |
|---|---|---|
| `--speed 1.0` | 不加速（默认） | 最准 |
| `--speed 1.25` | 加速 1.25 倍 | 几乎不影响准确率，推荐 |
| `--speed 1.5` | 加速 1.5 倍 | 准确率略降 |
| `--speed 2.0` | 加速到上限 | 错字明显增多，只在赶时间时用 |

加速后的时间戳会自动换算回原视频时间。

### 模型 `--model`

| 指令 | 特点 | 适合 |
|---|---|---|
| `--model large-v3` | 最准，最慢，默认 | 有 NVIDIA 显卡 |
| `--model large-v3-turbo` | 接近 large-v3 的准确率，更快 | 显卡，想省时间（需要较新版本的 faster-whisper） |
| `--model large-v2` | 上一代大模型 | 备选 |
| `--model medium` | 速度和准确率折中 | 显卡较弱或想更快 |
| `--model small` | 较快，错字较多 | 只有 CPU |
| `--model base` | 很快，准确率一般 | 快速试跑 |
| `--model tiny` | 最快，准确率最低 | 只测试流程 |

名字带 `.en` 的（如 `small.en`、`medium.en`）是纯英文模型，只用于英文音频。带 `distil-` 的（如 `distil-large-v3`）主要针对英文，不建议用于中文。具体支持哪些名字取决于你安装的 faster-whisper 版本。

### 设备 `--device`

| 指令 | 含义 |
|---|---|
| `--device auto` | 自动选择（默认） |
| `--device cuda` | NVIDIA 显卡，需要 CUDA 运行库，速度最快 |
| `--device cpu` | 只用 CPU，任何电脑都能跑，较慢 |

苹果芯片（M 系列）的 GPU 不被 faster-whisper 支持，请用 `--device cpu`。

### 语言 `--lang`

默认 `zh`。必须明确指定语言代码，脚本不支持自动检测。

| 指令 | 语言 | 指令 | 语言 |
|---|---|---|---|
| `--lang zh` | 中文（普通话，默认） | `--lang ko` | 韩语 |
| `--lang en` | 英语 | `--lang fr` | 法语 |
| `--lang ja` | 日语 | `--lang de` | 德语 |
| `--lang es` | 西班牙语 | `--lang ru` | 俄语 |
| `--lang pt` | 葡萄牙语 | `--lang ar` | 阿拉伯语 |
| `--lang it` | 意大利语 | `--lang yue` | 粤语 |

Whisper 一共支持约 100 种语言，其他语言用它的标准语言代码即可。只有 `--lang zh` 会附带"使用简体中文"的提示词。

### 束搜索宽度 `--beam-size`

Whisper 识别每一句话时，会同时保留几条"候选写法"，最后选得分最高的一条。`--beam-size` 就是同时保留几条。

| 指令 | 效果 |
|---|---|
| `--beam-size 5` | 默认。候选多，最准，最慢 |
| `--beam-size 3` | 折中 |
| `--beam-size 1` | 只走一条路，明显更快；遇到同音词、专有名词时更容易写错 |

### 计算精度 `--compute-type`

模型运算时数字的精度。精度越低，占用显存/内存越少，速度越快，准确率可能略降。

| 指令 | 含义 | 适合 |
|---|---|---|
| `--compute-type auto` | 由程序按设备自动选择（默认） | 不确定时 |
| `--compute-type float16` | 半精度 | NVIDIA 显卡，速度和准确率的最佳平衡 |
| `--compute-type int8_float16` | 8 位量化 + 半精度 | 显卡显存不够时 |
| `--compute-type int8` | 8 位量化 | CPU，更快更省内存 |
| `--compute-type float32` | 全精度 | 最稳，最慢，一般不需要 |

`float16` 只能在显卡上用；在 `--device cpu` 下选它会报错，请改用 `int8` 或 `auto`。

### 其他

| 指令 | 含义 |
|---|---|
| `--out 目录名` | 输出目录，默认 `out` |
| `-h` | 显示帮助 |
