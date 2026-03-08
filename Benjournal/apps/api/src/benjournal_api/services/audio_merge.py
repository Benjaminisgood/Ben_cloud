from __future__ import annotations

import shutil
import subprocess
import tempfile
import wave
from pathlib import Path


class AudioMergeError(RuntimeError):
    pass


def merge_audio_segments(segment_paths: list[Path], *, output_path: Path) -> Path:
    if not segment_paths:
        raise AudioMergeError("没有可合并的音频片段。")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if len(segment_paths) == 1:
        shutil.copyfile(segment_paths[0], output_path)
        return output_path

    if all(path.suffix.lower() == ".wav" for path in segment_paths):
        return _merge_wav_files(segment_paths, output_path=output_path)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudioMergeError("多段非 WAV 音频合并需要系统安装 ffmpeg。")
    return _merge_with_ffmpeg(ffmpeg, segment_paths, output_path=output_path)


def _merge_wav_files(segment_paths: list[Path], *, output_path: Path) -> Path:
    params = None
    with wave.open(str(output_path), "wb") as writer:
        for path in segment_paths:
            with wave.open(str(path), "rb") as reader:
                current = reader.getparams()
                if params is None:
                    params = current
                    writer.setparams(current)
                elif current[:4] != params[:4]:
                    raise AudioMergeError("WAV 参数不一致，无法按天合并。")
                writer.writeframes(reader.readframes(reader.getnframes()))
    return output_path


def _merge_with_ffmpeg(ffmpeg: str, segment_paths: list[Path], *, output_path: Path) -> Path:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as manifest:
        manifest_path = Path(manifest.name)
        for path in segment_paths:
            manifest.write(f"file '{path.as_posix()}'\n")

    try:
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(manifest_path),
                "-c",
                "copy",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        manifest_path.unlink(missing_ok=True)

    if result.returncode != 0:
        raise AudioMergeError(result.stderr.strip() or "ffmpeg 合并失败。")
    return output_path
