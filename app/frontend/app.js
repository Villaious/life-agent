const form = document.querySelector("#booking-form");
const submitButton = document.querySelector("#submit-button");
const resetButton = document.querySelector("#reset-button");
const missingDemoButton = document.querySelector("#missing-demo-button");
const copyButton = document.querySelector("#copy-button");

const statusBadge = document.querySelector("#status-badge");
const resultSubtitle = document.querySelector("#result-subtitle");
const replyText = document.querySelector("#reply-text");
const missingFields = document.querySelector("#missing-fields");
const candidateList = document.querySelector("#candidate-list");
const rawJson = document.querySelector("#raw-json");
const timelineItems = [...document.querySelectorAll("#timeline li")];

const defaultValues = {
  userId: "user_001",
  sessionId: "",
  message: "帮我预约保洁",
  location: "深圳南山",
  timePreference: "明天下午",
  permissions: ["booking:match", "booking:slot", "booking:order"],
};

function getPermissionValues() {
  return [...form.querySelectorAll('input[name="permission"]:checked')].map((item) => item.value);
}

function setPermissionValues(values) {
  form.querySelectorAll('input[name="permission"]').forEach((item) => {
    item.checked = values.includes(item.value);
  });
}

function buildPayload() {
  const sessionId = document.querySelector("#session-id").value.trim();
  const location = document.querySelector("#location").value.trim();
  const timePreference = document.querySelector("#time-preference").value.trim();
  const permissions = getPermissionValues();
  const context = { permissions };

  if (location) {
    context.location = location;
  }
  if (timePreference) {
    context.time_preference = timePreference;
  }

  return {
    user_id: document.querySelector("#user-id").value.trim() || "anonymous",
    session_id: sessionId || null,
    message: document.querySelector("#message").value.trim(),
    context,
  };
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "提交中" : "提交预约";
}

function setStatus(status) {
  statusBadge.className = `status-badge ${status || "idle"}`;
  statusBadge.textContent = status || "idle";
}

function renderTimeline(status, response) {
  timelineItems.forEach((item) => {
    item.classList.remove("done", "warn", "fail");
  });

  if (status === "needs_info") {
    timelineItems[0].classList.add("warn");
    return;
  }

  if (status === "failed") {
    const hasCandidates = Array.isArray(response.candidates) && response.candidates.length > 0;
    timelineItems[0].classList.add("done");
    if (hasCandidates) {
      timelineItems[1].classList.add("done");
      timelineItems[2].classList.add("done");
      timelineItems[3].classList.add("fail");
    } else {
      timelineItems[1].classList.add("fail");
    }
    return;
  }

  if (status === "created") {
    timelineItems.forEach((item) => item.classList.add("done"));
  }
}

function renderMissing(fields) {
  missingFields.replaceChildren();

  if (!fields || fields.length === 0) {
    const empty = document.createElement("span");
    empty.className = "empty-state";
    empty.textContent = "无";
    missingFields.append(empty);
    return;
  }

  fields.forEach((field) => {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = field;
    missingFields.append(tag);
  });
}

function renderCandidates(candidates) {
  candidateList.replaceChildren();

  if (!candidates || candidates.length === 0) {
    const empty = document.createElement("span");
    empty.className = "empty-state";
    empty.textContent = "暂无候选";
    candidateList.append(empty);
    return;
  }

  candidates.forEach((candidate) => {
    const row = document.createElement("article");
    row.className = "candidate";

    const main = document.createElement("div");
    const name = document.createElement("strong");
    const meta = document.createElement("p");
    const score = document.createElement("span");

    name.textContent = candidate.name || candidate.provider_id || "未命名服务商";
    meta.textContent = `${candidate.category || "unknown"} · ${candidate.location || "未指定区域"}`;
    score.className = "score";
    score.textContent = typeof candidate.score === "number" ? candidate.score.toFixed(2) : "-";

    main.append(name, meta);
    row.append(main, score);
    candidateList.append(row);
  });
}

function renderResponse(response) {
  const status = response.status || "idle";
  setStatus(status);
  resultSubtitle.textContent = response.task_id ? `任务 ${response.task_id}` : "请求已处理";
  replyText.textContent = response.reply || "无回复";
  renderTimeline(status, response);
  renderMissing(response.missing_fields);
  renderCandidates(response.candidates);
  rawJson.textContent = JSON.stringify(response, null, 2);
}

function resetForm() {
  document.querySelector("#user-id").value = defaultValues.userId;
  document.querySelector("#session-id").value = defaultValues.sessionId;
  document.querySelector("#message").value = defaultValues.message;
  document.querySelector("#location").value = defaultValues.location;
  document.querySelector("#time-preference").value = defaultValues.timePreference;
  setPermissionValues(defaultValues.permissions);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(true);
  setStatus("idle");
  resultSubtitle.textContent = "处理中";

  try {
    const response = await fetch("/api/v1/bookings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildPayload()),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "请求失败");
    }
    renderResponse(data);
  } catch (error) {
    renderResponse({
      status: "failed",
      reply: error instanceof Error ? error.message : "请求失败",
      task_id: null,
      missing_fields: [],
      candidates: [],
    });
  } finally {
    setLoading(false);
  }
});

resetButton.addEventListener("click", () => {
  resetForm();
});

missingDemoButton.addEventListener("click", () => {
  document.querySelector("#message").value = "帮我预约保洁";
  document.querySelector("#location").value = "";
  document.querySelector("#time-preference").value = "";
});

copyButton.addEventListener("click", async () => {
  await navigator.clipboard.writeText(rawJson.textContent);
  copyButton.textContent = "✓";
  setTimeout(() => {
    copyButton.textContent = "⧉";
  }, 900);
});

renderMissing([]);
renderCandidates([]);
