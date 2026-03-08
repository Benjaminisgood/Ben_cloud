(() => {
  const bootstrap = window.BENJOURNAL_BOOTSTRAP;
  if (!bootstrap || !bootstrap.selected_date) {
    return;
  }

  const selectedDate = bootstrap.selected_date;
  const selectedDay = bootstrap.selected_day || null;

  const saveButton = document.getElementById("save-entry");
  const textArea = document.getElementById("entry-text");
  const uploadButton = document.getElementById("upload-file");
  const fileInput = document.getElementById("audio-file");
  const startButton = document.getElementById("record-start");
  const stopButton = document.getElementById("record-stop");
  const statusNode = document.getElementById("client-status");
  const captureStudio = document.getElementById("capture-studio");
  const phaseNode = document.getElementById("recording-phase");
  const elapsedNode = document.getElementById("recording-elapsed");

  let recordingState = null;
  let networkBusy = false;
  let timerId = null;
  let recordedAt = null;

  function setStatus(message, tone = "neutral") {
    if (!statusNode) return;
    statusNode.textContent = message;
    statusNode.dataset.tone = tone;
  }

  function formatDuration(milliseconds) {
    const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
    const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
    const seconds = String(totalSeconds % 60).padStart(2, "0");
    return `${minutes}:${seconds}`;
  }

  function setElapsed(milliseconds) {
    if (!elapsedNode) return;
    elapsedNode.textContent = formatDuration(milliseconds);
  }

  function setCaptureState(state, label) {
    if (captureStudio) {
      captureStudio.dataset.state = state;
    }
    if (phaseNode) {
      phaseNode.textContent = label;
    }
  }

  function clearTimer() {
    if (timerId) {
      window.clearInterval(timerId);
      timerId = null;
    }
  }

  function startTimer() {
    recordedAt = Date.now();
    setElapsed(0);
    clearTimer();
    timerId = window.setInterval(() => {
      if (!recordedAt) return;
      setElapsed(Date.now() - recordedAt);
    }, 1000);
  }

  function stopTimer() {
    const elapsed = recordedAt ? Date.now() - recordedAt : 0;
    clearTimer();
    recordedAt = null;
    setElapsed(elapsed);
    return elapsed;
  }

  function restoreIdleStage() {
    const hasSegments = Number(selectedDay?.segment_count || 0) > 0;
    setCaptureState("idle", hasSegments ? "继续录音" : "待开始");
    if (!recordingState) {
      setElapsed(0);
    }
  }

  function renderControls() {
    const recording = Boolean(recordingState);
    if (saveButton) saveButton.disabled = networkBusy || recording;
    if (uploadButton) uploadButton.disabled = networkBusy || recording;
    if (fileInput) fileInput.disabled = networkBusy || recording;
    if (startButton) startButton.disabled = networkBusy || recording;
    if (stopButton) stopButton.disabled = !recording;
  }

  async function uploadAudio(file, sourceLabel) {
    const endpoint = `/api/journal-days/${selectedDate}/segments`;
    const formData = new FormData();
    formData.append("audio_file", file);

    networkBusy = true;
    renderControls();
    setCaptureState("uploading", `${sourceLabel}上传中`);
    setStatus(`${sourceLabel}上传中...`, "neutral");

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        body: formData,
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "音频上传失败。");
      }
      setCaptureState("uploading", "上传完成");
      setStatus("音频已上传，页面即将刷新。", "ready");
      window.setTimeout(() => {
        window.location.search = `?date=${encodeURIComponent(selectedDate)}`;
      }, 500);
    } catch (error) {
      setCaptureState("error", "上传失败");
      setStatus(error.message || "音频上传失败。", "failed");
    } finally {
      networkBusy = false;
      renderControls();
    }
  }

  async function saveEntry() {
    if (!textArea) return;

    networkBusy = true;
    renderControls();
    setStatus("文本保存中...", "neutral");

    try {
      const response = await fetch(`/api/journal-days/${selectedDate}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ entry_text: textArea.value }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "文本保存失败。");
      }
      setStatus("文本已保存。", "ready");
    } catch (error) {
      setStatus(error.message || "文本保存失败。", "failed");
    } finally {
      networkBusy = false;
      renderControls();
    }
  }

  function encodeWav(chunks, sampleRate) {
    const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const samples = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      samples.set(chunk, offset);
      offset += chunk.length;
    }

    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    writeAscii(view, 0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeAscii(view, 8, "WAVE");
    writeAscii(view, 12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeAscii(view, 36, "data");
    view.setUint32(40, samples.length * 2, true);

    let position = 44;
    for (let index = 0; index < samples.length; index += 1) {
      const value = Math.max(-1, Math.min(1, samples[index]));
      view.setInt16(position, value < 0 ? value * 0x8000 : value * 0x7fff, true);
      position += 2;
    }
    return new Blob([buffer], { type: "audio/wav" });
  }

  function writeAscii(view, offset, text) {
    for (let index = 0; index < text.length; index += 1) {
      view.setUint8(offset + index, text.charCodeAt(index));
    }
  }

  async function startRecording() {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!navigator.mediaDevices?.getUserMedia || !AudioContextClass) {
      setCaptureState("error", "浏览器不支持");
      setStatus("当前浏览器不支持内置录音，请改用文件上传。", "failed");
      renderControls();
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const context = new AudioContextClass();
      const input = context.createMediaStreamSource(stream);
      const processor = context.createScriptProcessor(4096, 1, 1);
      const silence = context.createGain();
      silence.gain.value = 0;
      const chunks = [];

      processor.onaudioprocess = (event) => {
        chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };

      input.connect(processor);
      processor.connect(silence);
      silence.connect(context.destination);

      recordingState = {
        context,
        input,
        processor,
        silence,
        stream,
        sampleRate: context.sampleRate,
        chunks,
      };

      startTimer();
      setCaptureState("recording", "录音中");
      setStatus("录音中，点击“停止并上传”完成当前片段。", "neutral");
      renderControls();
    } catch (error) {
      setCaptureState("error", "麦克风不可用");
      setStatus(error.message || "麦克风启动失败。", "failed");
      renderControls();
    }
  }

  async function stopRecording() {
    if (!recordingState) {
      return;
    }

    const current = recordingState;
    recordingState = null;
    const elapsed = stopTimer();

    current.processor.disconnect();
    current.input.disconnect();
    current.silence.disconnect();
    current.stream.getTracks().forEach((track) => track.stop());
    await current.context.close();

    setCaptureState("uploading", "整理录音中");
    setElapsed(elapsed);
    renderControls();

    const blob = encodeWav(current.chunks, current.sampleRate);
    const filename = `${selectedDate}-${Date.now()}.wav`;
    const file = new File([blob], filename, { type: "audio/wav" });
    await uploadAudio(file, "录音片段");
  }

  if (saveButton) {
    saveButton.addEventListener("click", saveEntry);
  }

  if (uploadButton) {
    uploadButton.addEventListener("click", async () => {
      if (!fileInput?.files?.length) {
        setCaptureState("error", "缺少文件");
        setStatus("先选择一个音频文件。", "failed");
        return;
      }
      await uploadAudio(fileInput.files[0], "音频文件");
    });
  }

  if (startButton) {
    startButton.addEventListener("click", startRecording);
  }

  if (stopButton) {
    stopButton.addEventListener("click", stopRecording);
  }

  restoreIdleStage();
  renderControls();
})();
