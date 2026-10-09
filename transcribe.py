#!/usr/bin/env python3
"""把视频/音频转成带时间戳的文字（本地 Whisper 离线识别）。
输入可以是网址（YouTube、B 站、播客等 yt-dlp 支持的网站），也可以是本地的 mp4/mp3/m4a/wav 等文件。

安装（一次）：
    pip install -U yt-dlp faster-whisper
    # 还需要 ffmpeg：macOS 用 `brew install ffmpeg`，Windows 用 `winget install ffmpeg`

用法：
    python transcribe.py "https://www.youtube.com/watch?v=VIDEO_ID" --model small --device cpu
    python transcribe.py "D:/videos/talk.mp4" --lang en      # 本地文件，英文
    python transcribe.py URL --speed 1.5     # 先把音频加速再识别，更快，准确率略降

输出（在 out/ 目录）：
    transcript.txt   带 [HH:MM:SS] 时间戳的全文
    transcript.srt   字幕文件
注意：--speed 建议不超过 2.0，更高会明显影响识别准确率。
"""
import argparse
import pathlib
import subprocess
import sys

SR = 16000
CHUNK_SECONDS = 30 * 60  # 每段 30 分钟，省内存


def fmt(t: float, srt: bool = False) -> str:
    h, rem = divmod(int(t), 3600)
    m, s = divmod(rem, 60)
    if srt:
        ms = int((t - int(t)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    return f"{h:02d}:{m:02d}:{s:02d}"


def run(cmd):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def add_cuda_dll_dirs():
    """Windows 上让程序找到 pip 装的 cuBLAS / cuDNN 运行库（没装也没关系）。"""
    if sys.platform != "win32":
        return
    import importlib.util
    import os
    for pkg in ("nvidia.cublas", "nvidia.cudnn", "nvidia.cuda_runtime"):
        try:
            spec = importlib.util.find_spec(pkg)
        except Exception:
            spec = None
        if not spec or not spec.submodule_search_locations:
            continue
        for loc in spec.submodule_search_locations:
            d = pathlib.Path(loc) / "bin"
            if d.is_dir():
                os.add_dll_directory(str(d))
                os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="视频网址，或本地音视频文件路径")
    ap.add_argument("--out", default="out")
    ap.add_argument("--model", default="large-v3",
                    help="large-v3（需要显卡，最准）/ medium / small（CPU 可用）")
    ap.add_argument("--device", default="auto", help="auto / cuda / cpu")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--speed", type=float, default=1.0,
                    help="识别前用 ffmpeg 加速音频的倍数，建议 1.0 到 2.0")
    ap.add_argument("--beam-size", type=int, default=5,
                    help="束搜索宽度：越大越准越慢，1 最快（默认 5）")
    ap.add_argument("--compute-type", default="auto",
                    choices=["auto", "float16", "int8_float16", "int8", "float32"],
                    help="计算精度：显卡推荐 float16，CPU 可用 int8（默认 auto）")
    args = ap.parse_args()

    if args.speed < 1.0 or args.speed > 2.0:
        sys.exit("--speed 请设在 1.0 到 2.0 之间")
    if args.beam_size < 1:
        sys.exit("--beam-size 必须是 1 或更大的整数")

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    local = pathlib.Path(args.source)
    if local.is_file():
        audio = local
        tag = local.stem
    else:
        audio = out / "audio.m4a"
        tag = "audio"
        if not audio.exists():
            run([sys.executable, "-m", "yt_dlp", "-f", "bestaudio", "-x",
                 "--audio-format", "m4a", "-o", str(out / "audio.%(ext)s"), args.source])

    # 用 ffmpeg 转成 16kHz 单声道原始 PCM（可选加速），不经过 av 库
    pcm = out / f"{tag}_x{args.speed}.pcm"
    if not pcm.exists():
        cmd = ["ffmpeg", "-y", "-i", str(audio), "-vn", "-ac", "1", "-ar", str(SR)]
        if args.speed != 1.0:
            cmd += ["-filter:a", f"atempo={args.speed}"]
        cmd += ["-f", "s16le", str(pcm)]
        run(cmd)

    add_cuda_dll_dirs()
    import numpy as np
    from faster_whisper import WhisperModel

    data = np.memmap(pcm, dtype=np.int16, mode="r")
    total = len(data)
    print(f"音频时长约 {total / SR / 60 * args.speed:.0f} 分钟（原速），开始识别……", flush=True)

    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    prompt = "以下是普通话的句子，使用简体中文。" if args.lang == "zh" else None

    txt = (out / "transcript.txt").open("w", encoding="utf-8")
    srt = (out / "transcript.srt").open("w", encoding="utf-8")
    n = 0
    step = CHUNK_SECONDS * SR
    for off in range(0, total, step):
        chunk = np.asarray(data[off:off + step], dtype=np.float32) / 32768.0
        base = off / SR
        segments, _ = model.transcribe(
            chunk, language=args.lang, vad_filter=True, initial_prompt=prompt,
            beam_size=args.beam_size)
        for seg in segments:
            # 加速过的音频，时间戳要换算回原视频时间
            start = (base + seg.start) * args.speed
            end = (base + seg.end) * args.speed
            text = seg.text.strip()
            n += 1
            txt.write(f"[{fmt(start)}] {text}\n")
            srt.write(f"{n}\n{fmt(start, True)} --> {fmt(end, True)}\n{text}\n\n")
            if n % 50 == 0:
                print(f"已识别到 {fmt(start)}", flush=True)
                txt.flush()
                srt.flush()
    txt.close()
    srt.close()
    print(f"完成：{out / 'transcript.txt'}")


if __name__ == "__main__":
    main()
