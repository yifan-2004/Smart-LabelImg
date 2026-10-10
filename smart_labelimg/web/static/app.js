"use strict";

const API = {
  openDataset: "/api/dataset/open",
  dataset: "/api/dataset",
  image: (index) => `/api/images/${index}`,
  imageContent: (index) => `/api/images/${index}/content`,
  annotations: (index) => `/api/images/${index}/annotations`,
  refine: (index) => `/api/images/${index}/refine`,
  propagate: (index) => `/api/images/${index}/propagate`,
  previous: (index) => `/api/images/${index}/previous`,
};

const $ = (selector) => document.querySelector(selector);
const dom = {
  datasetForm: $("#dataset-form"), datasetPath: $("#dataset-path"), openDataset: $("#open-dataset"), format: $("#annotation-format"),
  imageList: $("#image-list"), imageSearch: $("#image-search"), imageCount: $("#image-count"),
  datasetName: $("#dataset-name"), saveState: $("#save-state"), canvas: $("#annotation-canvas"),
  stage: $("#canvas-stage"), empty: $("#empty-state"), loading: $("#loading-overlay"),
  boxCount: $("#box-count"), boxList: $("#box-list"), labelList: $("#label-list"),
  addLabelForm: $("#add-label-form"), newLabel: $("#new-label"), modeHint: $("#mode-hint"),
  manualMode: $("#manual-mode"), smartMode: $("#smart-mode"), undo: $("#undo-button"),
  redo: $("#redo-button"), save: $("#save-button"), previous: $("#previous-button"),
  next: $("#next-button"), copyPrevious: $("#copy-previous-button"), smartNext: $("#smart-next-button"),
  imagePosition: $("#image-position"), zoomOut: $("#zoom-out"), zoomIn: $("#zoom-in"),
  fit: $("#fit-button"), toast: $("#toast"),
  addLabel: $("#add-label-form button"),
};
const ctx = dom.canvas.getContext("2d");

const state = {
  datasetPath: "", sessionId: "", images: [], currentIndex: -1, image: null, boxes: [], pendingCandidates: [],
  labels: ["object"], activeLabel: "object", format: "yolo", mode: "manual", selected: new Set(),
  history: [], historyIndex: -1, dirty: false, busy: false, zoom: 1, fitScale: 1, scale: 1,
  offsetX: 0, offsetY: 0, pointer: null, imageCache: new Image(), autoSaveTimer: null,
  editRevision: 0, savePromise: null,
};

async function api(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try { const body = await response.json(); detail = body.detail || body.message || detail; } catch (_) { /* response is not JSON */ }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

function setBusy(value, message = "处理中…") {
  state.busy = value;
  dom.loading.hidden = !value;
  const label = dom.loading.querySelector("span:last-child");
  if (label) label.textContent = message;
  const busyControls = [
    dom.datasetPath, dom.openDataset, dom.format, dom.save, dom.previous, dom.next,
    dom.copyPrevious, dom.smartNext, dom.undo, dom.redo, dom.newLabel, dom.addLabel,
    dom.manualMode, dom.smartMode,
  ];
  busyControls.forEach((control) => { control.disabled = value; });
  if (!value) {
    renderNavigation();
    updateHistoryButtons();
    if (state.dirty) scheduleAutoSave();
  }
}

function toast(message, isError = false) {
  dom.toast.textContent = message;
  dom.toast.classList.toggle("error", isError);
  dom.toast.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { dom.toast.hidden = true; }, 2600);
}

function markDirty(value = true) {
  if (value) state.editRevision += 1;
  state.dirty = value;
  dom.saveState.textContent = value ? "未保存" : "已保存";
  dom.saveState.className = `save-state${value ? " dirty" : ""}`;
  if (value) scheduleAutoSave();
  else if (state.autoSaveTimer) { clearTimeout(state.autoSaveTimer); state.autoSaveTimer = null; }
}

function scheduleAutoSave() {
  if (state.currentIndex < 0 || state.busy) return;
  clearTimeout(state.autoSaveTimer);
  state.autoSaveTimer = setTimeout(() => {
    state.autoSaveTimer = null;
    if (state.dirty && !state.busy) saveAnnotations({ silent: true });
  }, 650);
}

function colorFor(label) {
  let hash = 0;
  for (const char of label) hash = ((hash << 5) - hash + char.charCodeAt(0)) | 0;
  return `hsl(${Math.abs(hash) % 360} 76% 54%)`;
}

function normalizeBox(box) {
  const maxX = state.image?.width ?? Infinity, maxY = state.image?.height ?? Infinity;
  return {
    label: box.label || state.activeLabel || "object",
    x1: Math.max(0, Math.min(maxX, Math.round(Math.min(box.x1, box.x2)))),
    y1: Math.max(0, Math.min(maxY, Math.round(Math.min(box.y1, box.y2)))),
    x2: Math.max(0, Math.min(maxX, Math.round(Math.max(box.x1, box.x2)))),
    y2: Math.max(0, Math.min(maxY, Math.round(Math.max(box.y1, box.y2)))),
    ...(box.score == null ? {} : { score: box.score }),
  };
}

function snapshot(record = true) {
  if (!record) return;
  const value = JSON.stringify({ boxes: state.boxes, labels: state.labels });
  if (state.history[state.historyIndex] === value) return;
  state.history = state.history.slice(0, state.historyIndex + 1);
  state.history.push(value);
  if (state.history.length > 100) state.history.shift();
  state.historyIndex = state.history.length - 1;
  updateHistoryButtons();
}

function restoreHistory(index) {
  if (index < 0 || index >= state.history.length) return;
  state.historyIndex = index;
  const value = JSON.parse(state.history[index]);
  state.boxes = value.boxes;
  state.labels = value.labels;
  state.selected.clear();
  markDirty();
  renderAll();
}

function updateHistoryButtons() {
  dom.undo.disabled = state.historyIndex <= 0;
  dom.redo.disabled = state.historyIndex < 0 || state.historyIndex >= state.history.length - 1;
}

async function openDataset(path) {
  if (state.busy) return;
  if (!path.trim()) return toast("请输入数据集文件夹路径", true);
  setBusy(true, state.dirty ? "正在保存当前数据集…" : "正在读取数据集…");
  try {
    if (state.dirty && !(await saveAnnotations({ silent: true }))) return;
    const session = await api(API.openDataset, {
      method: "POST", body: JSON.stringify({ path: path.trim(), format: state.format }),
    });
    applyDataset(session);
    if (state.images.length) await loadImage(Number.isInteger(session.currentIndex) ? session.currentIndex : 0, false, true);
    else toast("文件夹中没有支持的图片", true);
  } catch (error) { toast(`打开失败：${error.message}`, true); }
  finally { setBusy(false); }
}

function applyDataset(session) {
  state.datasetPath = session.path || dom.datasetPath.value.trim();
  state.sessionId = session.sessionId || "";
  state.images = Array.isArray(session.images)
    ? session.images.map((item) => typeof item === "string" ? { name: item } : item)
    : [];
  state.labels = session.labels?.length ? session.labels : ["object"];
  state.activeLabel = state.labels.includes(state.activeLabel) ? state.activeLabel : state.labels[0];
  state.format = session.format === "voc_xml" ? "voc_xml" : "yolo";
  dom.format.value = state.format;
  dom.datasetPath.value = state.datasetPath;
  dom.datasetName.textContent = state.datasetPath.split(/[\\/]/).filter(Boolean).pop() || state.datasetPath;
  renderImageList();
}

async function loadImage(index, preservePrevious = true, allowBusy = false) {
  if (index < 0 || index >= state.images.length || (state.busy && !allowBusy)) return;
  if (state.dirty && !(await saveAnnotations())) return;
  setBusy(true, "正在加载图片…");
  try {
    const data = await api(API.image(index));
    const image = new Image();
    image.decoding = "async";
    image.src = `${API.imageContent(index)}?v=${Date.now()}`;
    await image.decode();
    void preservePrevious;
    state.currentIndex = index;
    state.image = { ...data, width: data.width || image.naturalWidth, height: data.height || image.naturalHeight };
    state.imageCache = image;
    state.boxes = (data.boxes || []).map(normalizeBox);
    state.images[index].annotated = state.boxes.length > 0;
    if (data.labels?.length) state.labels = data.labels;
    if (data.format) state.format = data.format;
    state.activeLabel = state.labels.includes(state.activeLabel) ? state.activeLabel : (state.labels[0] || "object");
    state.selected.clear();
    state.pendingCandidates = [];
    state.history = [];
    state.historyIndex = -1;
    snapshot();
    state.zoom = 1;
    markDirty(false);
    dom.empty.hidden = true;
    resizeCanvas();
    renderAll();
  } catch (error) { toast(`图片加载失败：${error.message}`, true); }
  finally { setBusy(false); }
}

async function saveAnnotations({ silent = false } = {}) {
  if (state.currentIndex < 0) return true;
  if (state.savePromise) {
    try { await state.savePromise; } catch (_) { return false; }
    if (!state.dirty) return true;
  }
  const revisionAtStart = state.editRevision;
  const imageIndexAtStart = state.currentIndex;
  const request = api(API.annotations(imageIndexAtStart), {
    method: "PUT",
    body: JSON.stringify({ sessionId: state.sessionId, boxes: state.boxes.map(normalizeBox), labels: state.labels, format: state.format }),
  });
  state.savePromise = request;
  try {
    await request;
    if (state.editRevision === revisionAtStart && state.currentIndex === imageIndexAtStart) markDirty(false);
    if (state.images[imageIndexAtStart]) state.images[imageIndexAtStart].annotated = state.boxes.length > 0;
    renderImageList();
    if (!silent) toast("标注已保存");
  } catch (error) {
    dom.saveState.textContent = "保存失败";
    dom.saveState.className = "save-state error";
    toast(`保存失败：${error.message}`, true);
    return false;
  } finally {
    if (state.savePromise === request) state.savePromise = null;
  }
  if (state.dirty) return saveAnnotations({ silent: true });
  return true;
}

async function navigate(delta) { await loadImage(state.currentIndex + delta); }

async function copyPreviousBoxes() {
  if (state.currentIndex <= 0 || state.busy) return toast("当前图片没有上一张", true);
  setBusy(true, "正在复制上一张标注…");
  try {
    const result = await api(API.previous(state.currentIndex));
    const boxes = (result.boxes || []).map(normalizeBox);
    if (!boxes.length) return toast("上一张图片没有可复制的框", true);
    state.boxes = boxes;
    state.selected = new Set(state.boxes.map((_, index) => index));
    snapshot(); markDirty(); renderAll();
    toast(`已复制 ${state.boxes.length} 个框`);
  } catch (error) { toast(`复制上一张失败：${error.message}`, true); }
  finally { setBusy(false); }
}

async function smartNext() {
  if (state.busy || state.currentIndex < 0 || state.currentIndex >= state.images.length - 1) return;
  if (!(await saveAnnotations({ silent: true }))) return;
  setBusy(true, "MobileSAM 正在传播并微调…");
  try {
    const nextIndex = state.currentIndex + 1;
    const result = await api(API.propagate(nextIndex), { method: "POST", body: "{}" });
    await loadImageWithoutBusy(nextIndex);
    const propagated = result.boxes || [];
    const candidates = (result.candidates || []).map((item) => item.box || item);
    if (state.boxes.length && (propagated.length || candidates.length)) {
      toast("目标图片已有标注，已保留原框；可手动复制或调整", true);
    } else {
      if (propagated.length) {
        state.boxes = propagated.map(normalizeBox);
        state.selected = new Set(state.boxes.map((_, index) => index));
        snapshot(); markDirty();
      }
      state.pendingCandidates = candidates.map(normalizeBox);
      renderAll();
      toast(candidates.length
        ? `已传播 ${propagated.length} 个框；另有 ${candidates.length} 个候选框，按 Enter 接受`
        : `已传播并微调 ${propagated.length} 个框`);
    }
  } catch (error) { toast(`智能下一张失败：${error.message}`, true); }
  finally { setBusy(false); }
}

async function loadImageWithoutBusy(index) {
  const data = await api(API.image(index));
  const image = new Image();
  image.src = `${API.imageContent(index)}?v=${Date.now()}`;
  await image.decode();
  state.currentIndex = index;
  state.image = { ...data, width: data.width || image.naturalWidth, height: data.height || image.naturalHeight };
  state.imageCache = image;
  state.boxes = (data.boxes || []).map(normalizeBox);
    state.images[index].annotated = state.boxes.length > 0;
  if (data.labels?.length) state.labels = data.labels;
  state.selected.clear(); state.history = []; state.historyIndex = -1; snapshot(); state.zoom = 1; markDirty(false);
  state.pendingCandidates = [];
  dom.empty.hidden = true; resizeCanvas(); renderAll();
}

async function refineBox(box) {
  setBusy(true, "MobileSAM 正在微调…");
  try {
    const result = await api(API.refine(state.currentIndex), {
      method: "POST", body: JSON.stringify({ box: normalizeBox(box), label: box.label }),
    });
    return result.boxes?.[0] ? normalizeBox(result.boxes[0]) : normalizeBox(box);
  } catch (error) { toast(`MobileSAM 微调失败，已保留粗框：${error.message}`, true); return normalizeBox(box); }
  finally { setBusy(false); }
}

function setMode(mode) {
  state.mode = mode;
  const smart = mode === "smart";
  dom.manualMode.classList.toggle("active", !smart); dom.manualMode.setAttribute("aria-pressed", String(!smart));
  dom.smartMode.classList.toggle("active", smart); dom.smartMode.setAttribute("aria-pressed", String(smart));
  dom.modeHint.textContent = smart ? "拖出粗框，MobileSAM 会自动贴合目标边界" : "拖动画框；点击框可选择、移动或缩放";
}

function resizeCanvas() {
  const rect = dom.stage.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  dom.canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  dom.canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  dom.canvas.style.width = `${rect.width}px`;
  dom.canvas.style.height = `${rect.height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  calculateTransform(rect.width, rect.height);
  drawCanvas();
}

function calculateTransform(viewWidth = dom.stage.clientWidth, viewHeight = dom.stage.clientHeight) {
  if (!state.image) return;
  state.fitScale = Math.min(viewWidth / state.image.width, viewHeight / state.image.height);
  state.scale = state.fitScale * state.zoom;
  state.offsetX = (viewWidth - state.image.width * state.scale) / 2;
  state.offsetY = (viewHeight - state.image.height * state.scale) / 2;
  dom.fit.textContent = `${Math.round(state.zoom * 100)}%`;
}

function screenPoint(event) {
  const rect = dom.canvas.getBoundingClientRect();
  return {
    x: (event.clientX - rect.left - state.offsetX) / state.scale,
    y: (event.clientY - rect.top - state.offsetY) / state.scale,
  };
}

function drawCanvas() {
  const rect = dom.stage.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  if (!state.image || !state.imageCache.complete) return;
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(state.imageCache, state.offsetX, state.offsetY, state.image.width * state.scale, state.image.height * state.scale);
  ctx.beginPath();
  ctx.rect(state.offsetX, state.offsetY, state.image.width * state.scale, state.image.height * state.scale);
  ctx.clip();
  state.boxes.forEach((box, index) => drawBox(box, index, state.selected.has(index)));
  state.pendingCandidates.forEach((box) => drawBox(box, -1, false, true));
  if (state.pointer?.kind === "draw") drawBox(normalizeBox({ ...state.pointer.start, ...state.pointer.end, label: state.activeLabel }), -1, false, true);
  ctx.restore();
}

function drawBox(box, index, selected, drafting = false) {
  const x = state.offsetX + box.x1 * state.scale, y = state.offsetY + box.y1 * state.scale;
  const w = (box.x2 - box.x1) * state.scale, h = (box.y2 - box.y1) * state.scale;
  const color = drafting && state.mode === "smart" ? "#a98bff" : colorFor(box.label);
  ctx.save();
  ctx.strokeStyle = color; ctx.lineWidth = selected ? 3 : 2; ctx.setLineDash(drafting ? [6, 4] : []);
  ctx.fillStyle = color.replace(")", selected ? " / 0.15)" : " / 0.07)");
  ctx.fillRect(x, y, w, h); ctx.strokeRect(x, y, w, h);
  const text = box.score == null ? box.label : `${box.label} ${Math.round(box.score * 100)}%`;
  ctx.font = "600 11px -apple-system, sans-serif";
  const textWidth = ctx.measureText(text).width + 10;
  ctx.fillStyle = color; ctx.fillRect(x, Math.max(state.offsetY, y - 20), textWidth, 20);
  ctx.fillStyle = "white"; ctx.fillText(text, x + 5, Math.max(state.offsetY + 14, y - 6));
  if (selected && index >= 0) {
    ctx.setLineDash([]);
    for (const point of handlePoints(box)) {
      ctx.fillStyle = "white"; ctx.strokeStyle = color; ctx.lineWidth = 2;
      ctx.fillRect(point.x - 4, point.y - 4, 8, 8); ctx.strokeRect(point.x - 4, point.y - 4, 8, 8);
    }
  }
  ctx.restore();
}

function handlePoints(box) {
  const sx = (x) => state.offsetX + x * state.scale, sy = (y) => state.offsetY + y * state.scale;
  return [
    { name: "nw", x: sx(box.x1), y: sy(box.y1) }, { name: "ne", x: sx(box.x2), y: sy(box.y1) },
    { name: "se", x: sx(box.x2), y: sy(box.y2) }, { name: "sw", x: sx(box.x1), y: sy(box.y2) },
  ];
}

function hitTest(point) {
  const tolerance = 8 / state.scale;
  const selected = [...state.selected].reverse();
  for (const index of selected) {
    const box = state.boxes[index];
    const corners = [{ name: "nw", x: box.x1, y: box.y1 }, { name: "ne", x: box.x2, y: box.y1 }, { name: "se", x: box.x2, y: box.y2 }, { name: "sw", x: box.x1, y: box.y2 }];
    for (const corner of corners) if (Math.abs(point.x - corner.x) <= tolerance && Math.abs(point.y - corner.y) <= tolerance) return { index, handle: corner.name };
  }
  for (let index = state.boxes.length - 1; index >= 0; index--) {
    const box = state.boxes[index];
    if (point.x >= box.x1 && point.x <= box.x2 && point.y >= box.y1 && point.y <= box.y2) return { index, handle: null };
  }
  return null;
}

function onPointerDown(event) {
  if (!state.image || state.busy || event.button !== 0) return;
  dom.canvas.setPointerCapture(event.pointerId);
  const point = screenPoint(event), hit = hitTest(point);
  if (hit) {
    if (!event.metaKey && !event.ctrlKey && !state.selected.has(hit.index)) state.selected = new Set([hit.index]);
    else if ((event.metaKey || event.ctrlKey) && state.selected.has(hit.index)) state.selected.delete(hit.index);
    else state.selected.add(hit.index);
    state.pointer = { kind: hit.handle ? "resize" : "move", start: point, last: point, hit, originals: state.boxes.map((box) => ({ ...box })) };
  } else {
    state.selected.clear();
    state.pointer = { kind: "draw", start: { x1: point.x, y1: point.y }, end: { x2: point.x, y2: point.y } };
  }
  renderAll();
}

function onPointerMove(event) {
  if (!state.pointer || !state.image) return;
  const point = screenPoint(event), action = state.pointer;
  if (action.kind === "draw") action.end = { x2: point.x, y2: point.y };
  if (action.kind === "move") {
    const dx = point.x - action.start.x, dy = point.y - action.start.y;
    state.selected.forEach((index) => {
      const original = action.originals[index];
      const width = original.x2 - original.x1, height = original.y2 - original.y1;
      const x1 = Math.max(0, Math.min(state.image.width - width, original.x1 + dx));
      const y1 = Math.max(0, Math.min(state.image.height - height, original.y1 + dy));
      state.boxes[index] = normalizeBox({ ...original, x1, y1, x2: x1 + width, y2: y1 + height });
    });
  }
  if (action.kind === "resize") {
    const original = action.originals[action.hit.index], resized = { ...original };
    if (action.hit.handle.includes("n")) resized.y1 = point.y;
    if (action.hit.handle.includes("s")) resized.y2 = point.y;
    if (action.hit.handle.includes("w")) resized.x1 = point.x;
    if (action.hit.handle.includes("e")) resized.x2 = point.x;
    state.boxes[action.hit.index] = normalizeBox(resized);
  }
  drawCanvas();
}

async function onPointerUp(event) {
  if (!state.pointer) return;
  try { dom.canvas.releasePointerCapture(event.pointerId); } catch (_) { /* pointer already released */ }
  const action = state.pointer;
  state.pointer = null;
  if (action.kind === "draw") {
    let box = normalizeBox({ label: state.activeLabel, ...action.start, ...action.end });
    if (box.x2 - box.x1 >= 3 && box.y2 - box.y1 >= 3) {
      if (state.mode === "smart") box = await refineBox(box);
      state.boxes.push(box); state.selected = new Set([state.boxes.length - 1]); snapshot(); markDirty();
    }
  } else if (action.kind === "move" || action.kind === "resize") { snapshot(); markDirty(); }
  renderAll();
}

function deleteSelected() {
  if (!state.selected.size) return;
  state.boxes = state.boxes.filter((_, index) => !state.selected.has(index));
  state.selected.clear(); snapshot(); markDirty(); renderAll();
}

function moveSelected(dx, dy) {
  if (!state.selected.size) return;
  state.selected.forEach((index) => {
    const box = state.boxes[index], width = box.x2 - box.x1, height = box.y2 - box.y1;
    const x1 = Math.max(0, Math.min(state.image.width - width, box.x1 + dx));
    const y1 = Math.max(0, Math.min(state.image.height - height, box.y1 + dy));
    state.boxes[index] = normalizeBox({ ...box, x1, y1, x2: x1 + width, y2: y1 + height });
  });
  snapshot(); markDirty(); renderAll();
}

function acceptPendingCandidates() {
  if (!state.pendingCandidates.length) return;
  const start = state.boxes.length;
  state.boxes.push(...state.pendingCandidates.map(normalizeBox));
  state.pendingCandidates = [];
  state.selected = new Set(state.boxes.map((_, index) => index).filter((index) => index >= start));
  snapshot(); markDirty(); renderAll();
  toast("已接受候选框");
}

function changeSelectedLabel(label) {
  state.activeLabel = label;
  if (state.selected.size) {
    state.selected.forEach((index) => { state.boxes[index].label = label; });
    snapshot(); markDirty();
  }
  renderAll();
}

function addLabel(name) {
  const label = name.trim();
  if (!label || state.labels.includes(label)) return;
  state.labels.push(label); state.activeLabel = label; snapshot(); markDirty(); renderAll();
}

function cancelPointer() {
  if (state.pointer?.originals) state.boxes = state.pointer.originals;
  state.pointer = null;
  renderAll();
}

function setZoom(value) {
  state.zoom = Math.max(.2, Math.min(8, value)); calculateTransform(); drawCanvas();
}

function renderImageList() {
  const query = dom.imageSearch.value.trim().toLowerCase();
  dom.imageList.replaceChildren();
  state.images.forEach((image, index) => {
    const name = image.name || image.path || `图片 ${index + 1}`;
    if (query && !name.toLowerCase().includes(query)) return;
    const li = document.createElement("li"); li.className = `image-item${index === state.currentIndex ? " active" : ""}`;
    const button = document.createElement("button"); button.type = "button"; button.title = name;
    const status = document.createElement("span"); status.className = `image-status${image.annotated ? " annotated" : ""}`;
    const text = document.createElement("span"); text.className = "image-name"; text.textContent = name;
    const number = document.createElement("span"); number.className = "image-number"; number.textContent = String(index + 1).padStart(3, "0");
    button.append(status, text, number); button.addEventListener("click", () => loadImage(index)); li.append(button); dom.imageList.append(li);
  });
  dom.imageCount.textContent = `${state.images.length} 张图片`;
}

function renderLabels() {
  dom.labelList.replaceChildren();
  state.labels.forEach((label) => {
    const count = state.boxes.filter((box) => box.label === label).length;
    const li = document.createElement("li"); li.className = `label-item${label === state.activeLabel ? " active" : ""}`;
    const dot = document.createElement("span"); dot.className = "color-dot"; dot.style.background = colorFor(label);
    const text = document.createElement("span"); text.className = "item-text"; text.textContent = label;
    const badge = document.createElement("span"); badge.className = "item-count"; badge.textContent = count;
    li.append(dot, text, badge); li.addEventListener("click", () => changeSelectedLabel(label)); dom.labelList.append(li);
  });
}

function renderBoxes() {
  dom.boxList.replaceChildren();
  state.boxes.forEach((box, index) => {
    const li = document.createElement("li"); li.className = `box-item${state.selected.has(index) ? " active" : ""}`;
    const dot = document.createElement("span"); dot.className = "color-dot"; dot.style.background = colorFor(box.label);
    const text = document.createElement("span"); text.className = "item-text"; text.textContent = `${index + 1}. ${box.label}`;
    const coords = document.createElement("span"); coords.className = "box-coords"; coords.textContent = `${box.x2 - box.x1}×${box.y2 - box.y1}`;
    li.append(dot, text, coords); li.addEventListener("click", (event) => {
      if (event.metaKey || event.ctrlKey) state.selected.has(index) ? state.selected.delete(index) : state.selected.add(index);
      else state.selected = new Set([index]);
      state.activeLabel = box.label; renderAll();
    });
    dom.boxList.append(li);
  });
  dom.boxCount.textContent = `${state.boxes.length} 个框`;
}

function renderNavigation() {
  const available = state.currentIndex >= 0;
  dom.previous.disabled = !available || state.currentIndex <= 0;
  dom.next.disabled = !available || state.currentIndex >= state.images.length - 1;
  dom.copyPrevious.disabled = !available || state.currentIndex <= 0;
  dom.smartNext.disabled = dom.next.disabled;
  dom.imagePosition.textContent = available ? `${state.currentIndex + 1} / ${state.images.length}` : `0 / ${state.images.length}`;
}

function renderAll() { renderImageList(); renderLabels(); renderBoxes(); renderNavigation(); updateHistoryButtons(); drawCanvas(); }

function isTyping(event) { return ["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName) || event.target.isContentEditable; }

function handleShortcut(event) {
  const command = event.metaKey || event.ctrlKey;
  if (command && event.key.toLowerCase() === "s") { event.preventDefault(); saveAnnotations(); return; }
  if (isTyping(event)) return;
  if (state.busy) return;
  const key = event.key.toLowerCase();
  if (command && key === "a") { event.preventDefault(); state.selected = new Set(state.boxes.map((_, index) => index)); renderAll(); return; }
  if (command && key === "z") { event.preventDefault(); restoreHistory(state.historyIndex + (event.shiftKey ? 1 : -1)); return; }
  if (command && key === "v") { event.preventDefault(); copyPreviousBoxes(); return; }
  if (command && key === "0") { event.preventDefault(); setZoom(1); return; }
  if (event.shiftKey && key === "d") { event.preventDefault(); smartNext(); return; }
  if (event.key === "Enter" && state.pendingCandidates.length) { event.preventDefault(); acceptPendingCandidates(); return; }
  if (!command && key === "w") { event.preventDefault(); setMode("manual"); return; }
  if (!command && key === "s") { event.preventDefault(); setMode("smart"); return; }
  if (!command && key === "a") { event.preventDefault(); navigate(-1); return; }
  if (!command && key === "d") { event.preventDefault(); navigate(1); return; }
  if (["delete", "backspace"].includes(key)) { event.preventDefault(); deleteSelected(); return; }
  if (event.key === "ArrowLeft") { event.preventDefault(); moveSelected(-1, 0); }
  if (event.key === "ArrowRight") { event.preventDefault(); moveSelected(1, 0); }
  if (event.key === "ArrowUp") { event.preventDefault(); moveSelected(0, -1); }
  if (event.key === "ArrowDown") { event.preventDefault(); moveSelected(0, 1); }
}

dom.datasetForm.addEventListener("submit", (event) => { event.preventDefault(); openDataset(dom.datasetPath.value); });
dom.format.addEventListener("change", () => { state.format = dom.format.value; markDirty(); });
dom.imageSearch.addEventListener("input", renderImageList);
dom.addLabelForm.addEventListener("submit", (event) => { event.preventDefault(); addLabel(dom.newLabel.value); dom.newLabel.value = ""; });
dom.manualMode.addEventListener("click", () => setMode("manual")); dom.smartMode.addEventListener("click", () => setMode("smart"));
dom.undo.addEventListener("click", () => restoreHistory(state.historyIndex - 1)); dom.redo.addEventListener("click", () => restoreHistory(state.historyIndex + 1));
dom.save.addEventListener("click", () => saveAnnotations()); dom.previous.addEventListener("click", () => navigate(-1)); dom.next.addEventListener("click", () => navigate(1));
dom.copyPrevious.addEventListener("click", copyPreviousBoxes); dom.smartNext.addEventListener("click", smartNext);
dom.zoomOut.addEventListener("click", () => setZoom(state.zoom / 1.2)); dom.zoomIn.addEventListener("click", () => setZoom(state.zoom * 1.2)); dom.fit.addEventListener("click", () => setZoom(1));
dom.canvas.addEventListener("pointerdown", onPointerDown); dom.canvas.addEventListener("pointermove", onPointerMove); dom.canvas.addEventListener("pointerup", onPointerUp); dom.canvas.addEventListener("pointercancel", cancelPointer);
dom.canvas.addEventListener("wheel", (event) => { if (!event.ctrlKey && !event.metaKey) return; event.preventDefault(); setZoom(state.zoom * (event.deltaY < 0 ? 1.1 : .9)); }, { passive: false });
document.addEventListener("keydown", handleShortcut);
window.addEventListener("beforeunload", (event) => { if (state.dirty) { event.preventDefault(); event.returnValue = ""; } });
new ResizeObserver(resizeCanvas).observe(dom.stage);

setMode("manual");
renderAll();
api(API.dataset).then((session) => {
  if (session?.path) {
    applyDataset(session);
    if (state.images.length) loadImage(Number.isInteger(session.currentIndex) ? session.currentIndex : 0, false);
  }
}).catch(() => { /* no active dataset yet */ });
