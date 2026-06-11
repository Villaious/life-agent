const bookingForm = document.querySelector("#booking-form");
const actionForm = document.querySelector("#action-form");
const queryForm = document.querySelector("#query-form");
const submitButton = document.querySelector("#submit-button");
const actionSubmitButton = document.querySelector("#action-submit-button");
const resetButton = document.querySelector("#reset-button");
const missingDemoButton = document.querySelector("#missing-demo-button");
const copyButton = document.querySelector("#copy-button");
const copyActionButton = document.querySelector("#copy-action-button");
const queryOrdersButton = document.querySelector("#query-orders-button");

const statusBadge = document.querySelector("#status-badge");
const actionStatusBadge = document.querySelector("#action-status-badge");
const resultSubtitle = document.querySelector("#result-subtitle");
const actionSubtitle = document.querySelector("#action-subtitle");
const querySubtitle = document.querySelector("#query-subtitle");
const replyText = document.querySelector("#reply-text");
const actionReplyText = document.querySelector("#action-reply-text");
const missingFields = document.querySelector("#missing-fields");
const parsedIntent = document.querySelector("#parsed-intent");
const candidateList = document.querySelector("#candidate-list");
const rawJson = document.querySelector("#raw-json");
const actionJson = document.querySelector("#action-json");
const orderList = document.querySelector("#order-list");
const timelineItems = [...document.querySelectorAll("#timeline li")];
const permissionAlert = document.querySelector("#permission-alert");
const healthState = document.querySelector("#health-state");

const defaultValues = {
  userId: "user_001",
  sessionId: "",
  message: "帮我预约明天下午深圳南山的上门保洁",
  permissions: [
    "booking:match",
    "booking:slot",
    "booking:order",
    "external_api:local_life",
    "privacy:user_context",
    "order:write",
  ],
};

const featureGroups = [
  {
    title: "自然语言预订",
    detail: "从用户描述中抽取服务类型、地点和时间偏好，用户不需要单独填写地点和时间。",
    status: "可操作",
  },
  {
    title: "服务商匹配",
    detail: "展示候选服务商的商家电话、价格、履约时长和库存锁。",
    status: "可操作",
  },
  {
    title: "时段确认",
    detail: "把用户时间偏好转为候选预约时段，并保留确认状态和库存锁信息。",
    status: "已接入",
  },
  {
    title: "订单草单",
    detail: "根据候选服务和时段创建草单，返回任务 ID 供后续动作复用。",
    status: "可操作",
  },
  {
    title: "支付 / 改期 / 取消 / 评价",
    detail: "订单动作走统一入口，每次动作后更新 PostgreSQL 中的订单状态。",
    status: "可操作",
  },
  {
    title: "订单查询",
    detail: "通过用户 ID，可选会话 ID 或任务 ID 查询 PostgreSQL 订单记录。",
    status: "可操作",
  },
  {
    title: "权限沙箱",
    detail: "每个工具声明所需权限，缺失权限时阻断调用并返回失败响应。",
    status: "已接入",
  },
  {
    title: "持久化与审计",
    detail: "写入任务、订单、工具审计日志和会话检查点，便于追踪闭环。",
    status: "配置启用",
  },
];

const toolRows = [
  ["ServiceMatchTool", "服务匹配", "booking:match, external_api:local_life, privacy:user_context"],
  ["SlotConfirmTool", "时段确认", "booking:slot, external_api:local_life, privacy:user_context"],
  ["OrderDraftTool", "订单草单", "booking:order, external_api:local_life, order:write"],
  ["PaymentTool", "发起支付", "payment:write, external_api:local_life, order:read"],
  ["RescheduleTool", "订单改期", "order:reschedule, external_api:local_life, privacy:user_context"],
  ["CancelOrderTool", "取消订单", "order:cancel, external_api:local_life, order:read"],
  ["ReviewOrderTool", "提交评价", "order:review, external_api:local_life, privacy:user_context"],
];

const actionFields = {
  payment: ["payment_method"],
  reschedule: ["new_time_preference", "reason"],
  cancel: ["reason"],
  review: ["rating", "comment"],
};

function valueOf(selector, fallback = "") {
  return document.querySelector(selector)?.value?.trim() || fallback;
}

function getCheckedValues(form, name) {
  if (!form) {
    return [];
  }
  return [...form.querySelectorAll(`input[name="${name}"]:checked`)].map((item) => item.value);
}

function setPermissionValues(values) {
  bookingForm.querySelectorAll('input[name="permission"]').forEach((item) => {
    item.checked = values.includes(item.value);
  });
}

function buildBookingPayload() {
  return {
    user_id: valueOf("#user-id", "anonymous"),
    session_id: valueOf("#session-id") || null,
    message: valueOf("#message"),
    context: { permissions: getCheckedValues(bookingForm, "permission") },
  };
}

function buildActionPayload() {
  const action = valueOf("#action-type", "payment");
  const taskId = valueOf("#action-task-id");
  const context = {
    action,
    task_id: taskId,
    order_id: taskId,
    permissions: getCheckedValues(actionForm, "action-permission"),
  };

  const allFields = {
    payment_method: valueOf("#payment-method"),
    new_time_preference: valueOf("#new-time-preference"),
    reason: valueOf("#action-reason"),
    rating: Number(valueOf("#review-rating", "0")),
    comment: valueOf("#review-comment"),
  };

  Object.entries(allFields).forEach(([key, value]) => {
    if (!actionFields[action].includes(key)) {
      return;
    }
    if (value || value === 0) {
      context[key] = value;
    }
  });

  return {
    user_id: valueOf("#user-id", "user_001"),
    session_id: valueOf("#session-id") || null,
    message: `执行订单动作：${action}`,
    context,
  };
}

function toggleActionFields() {
  const action = valueOf("#action-type", "payment");
  document.querySelectorAll(".action-field").forEach((field) => {
    const actions = (field.dataset.actions || "").split(" ");
    field.hidden = !actions.includes(action);
  });
  document.querySelectorAll(".field-grid").forEach((grid) => {
    const actionItems = [...grid.querySelectorAll(".action-field")];
    if (actionItems.length > 0) {
      grid.hidden = actionItems.every((item) => item.hidden);
    }
  });
}

function setLoading(button, isLoading, idleText) {
  button.disabled = isLoading;
  button.textContent = isLoading ? "处理中" : idleText;
}

function setStatus(badge, status) {
  const nextStatus = status || "idle";
  badge.className = `status-badge ${nextStatus}`;
  badge.textContent = nextStatus;
}

function renderTimeline(status, response) {
  timelineItems.forEach((item) => item.classList.remove("done", "warn", "fail"));
  if (status === "needs_info") {
    timelineItems[0].classList.add("warn");
    return;
  }
  if (status === "failed") {
    const hasCandidates = Array.isArray(response.candidates) && response.candidates.length > 0;
    timelineItems[0].classList.add("done");
    timelineItems[hasCandidates ? 3 : 1].classList.add("fail");
    if (hasCandidates) {
      timelineItems[1].classList.add("done");
      timelineItems[2].classList.add("done");
    }
    return;
  }
  if (status === "created" || status === "completed") {
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

function renderParsedIntent(intent) {
  parsedIntent.replaceChildren();
  const rows = [
    ["事件", intent?.event || intent?.raw_text || "待识别"],
    ["地点", intent?.location || "待补充"],
    ["时间", intent?.time_preference || "待补充"],
    ["服务分类", intent?.service_category || "unknown"],
  ];

  rows.forEach(([label, value]) => {
    const item = document.createElement("article");
    const title = document.createElement("span");
    const content = document.createElement("strong");
    title.textContent = label;
    content.textContent = value;
    item.append(title, content);
    parsedIntent.append(item);
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
    const detail = document.createElement("p");
    const scoreWrap = document.createElement("span");
    const score = document.createElement("span");
    const scoreTip = document.createElement("span");

    name.textContent = candidate.name || candidate.provider_id || "未命名服务商";
    meta.textContent = `${candidate.category || "unknown"} · ${candidate.location || "地址待确认"}`;
    detail.textContent = `${formatPrice(candidate.price)} · ${formatPhone(candidate.phone)} · ${formatDuration(candidate.fulfillment)} · ${formatLock(candidate.inventory_lock)}`;
    scoreWrap.className = "score-wrap";
    scoreWrap.tabIndex = 0;
    score.className = "score";
    const expectedScore =
      typeof candidate.expected_score === "number" ? candidate.expected_score : candidate.score;
    score.textContent = typeof expectedScore === "number" ? `${expectedScore.toFixed(0)}分` : "-";
    if (candidate.score_explanation) {
      scoreTip.className = "score-tip";
      scoreTip.textContent = candidate.score_explanation;
      scoreWrap.setAttribute("aria-label", candidate.score_explanation);
      scoreWrap.append(score, scoreTip);
    } else {
      scoreWrap.append(score);
    }

    main.append(name, meta, detail);
    row.append(main, scoreWrap);
    candidateList.append(row);
  });
}

function formatPhone(phone) {
  return phone ? `电话 ${phone}` : "电话待确认";
}

function formatPrice(price) {
  if (!price || typeof price.amount !== "number") {
    return "价格待确认";
  }
  return price.display_text || `${price.currency || "CNY"} ${price.amount}${price.unit ? `/${price.unit}` : ""}`;
}

function formatDuration(fulfillment) {
  if (!fulfillment || !fulfillment.duration_minutes) {
    return "时长待确认";
  }
  return `${fulfillment.duration_minutes} 分钟`;
}

function formatLock(lock) {
  if (!lock || !lock.locked) {
    return "未锁库存";
  }
  return lock.expires_at ? "库存已锁" : "库存已锁";
}

function renderBookingResponse(response) {
  const status = response.status || "idle";
  setStatus(statusBadge, status);
  resultSubtitle.textContent = response.task_id ? `任务 ${response.task_id}` : "请求已处理";
  replyText.textContent = response.reply || "无回复";
  permissionAlert.hidden = !(status === "failed" && (response.reply || "").includes("权限"));
  renderTimeline(status, response);
  renderParsedIntent(response.parsed_intent);
  renderMissing(response.missing_fields);
  renderCandidates(response.candidates);
  rawJson.textContent = JSON.stringify(response, null, 2);
  if (response.task_id) {
    document.querySelector("#action-task-id").value = response.task_id;
    syncQueryDefaults(response.task_id);
  }
}

function renderActionResponse(response) {
  const status = response.status || "idle";
  setStatus(actionStatusBadge, status);
  actionSubtitle.textContent = response.task_id ? `任务 ${response.task_id}` : "请求已处理";
  actionReplyText.textContent = response.reply || "无回复";
  actionJson.textContent = JSON.stringify(response, null, 2);
  if (response.task_id) {
    syncQueryDefaults(response.task_id);
  }
}

function syncQueryDefaults(taskId = "") {
  document.querySelector("#query-user-id").value = valueOf("#user-id", "user_001");
  document.querySelector("#query-session-id").value = valueOf("#session-id");
  if (taskId) {
    document.querySelector("#query-task-id").value = taskId;
  }
}

function renderOrders(orders) {
  orderList.replaceChildren();
  if (!orders || orders.length === 0) {
    const empty = document.createElement("span");
    empty.className = "empty-state";
    empty.textContent = "暂无订单记录";
    orderList.append(empty);
    return;
  }
  orders.forEach((order) => {
    const item = document.createElement("article");
    item.className = "order-item";
    const main = document.createElement("div");
    const title = document.createElement("strong");
    const detail = document.createElement("p");
    const provider = document.createElement("p");
    const status = document.createElement("span");
    const lastAction = order.raw_payload?.last_action;
    const providerName = order.provider?.name || order.provider_id || "服务商待确认";

    title.textContent = order.task_id;
    detail.textContent = `用户 ${order.user_id}${order.session_id ? ` · 会话 ${order.session_id}` : ""}`;
    provider.textContent = `${providerName} · ${formatPrice(order.price)} · ${formatOrderSlot(order.slot)}${lastAction ? ` · 最近动作 ${lastAction.action}` : ""}`;
    status.className = "status-badge completed";
    status.textContent = order.status || "draft";
    main.append(title, detail, provider);
    item.append(main, status);
    orderList.append(item);
  });
}

function formatOrderSlot(slot) {
  if (!slot) {
    return "时间待确认";
  }
  return slot.start_time || slot.value || "时间待确认";
}

async function postBooking(payload) {
  const response = await fetch("/api/v1/bookings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "请求失败");
  }
  return data;
}

async function queryOrders() {
  const params = new URLSearchParams();
  params.set("user_id", valueOf("#query-user-id", "anonymous"));
  const sessionId = valueOf("#query-session-id");
  const taskId = valueOf("#query-task-id");
  if (sessionId) {
    params.set("session_id", sessionId);
  }
  if (taskId) {
    params.set("task_id", taskId);
  }
  const response = await fetch(`/api/v1/bookings/orders?${params.toString()}`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "查询失败");
  }
  return data.orders || [];
}

function resetForm() {
  document.querySelector("#user-id").value = defaultValues.userId;
  document.querySelector("#session-id").value = defaultValues.sessionId;
  document.querySelector("#message").value = defaultValues.message;
  setPermissionValues(defaultValues.permissions);
}

function renderFeatureGrid() {
  const grid = document.querySelector("#feature-grid");
  featureGroups.forEach((feature) => {
    const item = document.createElement("article");
    item.className = "feature-item";
    item.innerHTML = `<span>${feature.status}</span><strong>${feature.title}</strong><p>${feature.detail}</p>`;
    grid.append(item);
  });
}

function renderToolTable() {
  const table = document.querySelector("#tool-table");
  toolRows.forEach(([tool, action, permissions]) => {
    const row = document.createElement("article");
    row.innerHTML = `<strong>${tool}</strong><span>${action}</span><p>${permissions}</p>`;
    table.append(row);
  });
}

async function refreshHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    const ok = response.ok && data.status === "ok";
    healthState.innerHTML = `<span class="dot ${ok ? "ok" : "fail"}"></span><span>${ok ? "服务正常" : "服务异常"}</span>`;
  } catch {
    healthState.innerHTML = '<span class="dot fail"></span><span>服务不可用</span>';
  }
}

bookingForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(submitButton, true, "提交预订");
  setStatus(statusBadge, "idle");
  resultSubtitle.textContent = "处理中";
  try {
    renderBookingResponse(await postBooking(buildBookingPayload()));
  } catch (error) {
    renderBookingResponse({
      status: "failed",
      reply: error instanceof Error ? error.message : "请求失败",
      task_id: null,
      missing_fields: [],
      candidates: [],
    });
  } finally {
    setLoading(submitButton, false, "提交预订");
  }
});

actionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(actionSubmitButton, true, "提交动作并更新订单");
  setStatus(actionStatusBadge, "idle");
  actionSubtitle.textContent = "处理中";
  try {
    renderActionResponse(await postBooking(buildActionPayload()));
  } catch (error) {
    renderActionResponse({
      status: "failed",
      reply: error instanceof Error ? error.message : "请求失败",
      task_id: null,
      action_result: null,
    });
  } finally {
    setLoading(actionSubmitButton, false, "提交动作并更新订单");
  }
});

queryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  queryOrdersButton.disabled = true;
  queryOrdersButton.textContent = "查询中";
  querySubtitle.textContent = "查询中";
  try {
    const orders = await queryOrders();
    renderOrders(orders);
    querySubtitle.textContent = `找到 ${orders.length} 条订单`;
  } catch (error) {
    renderOrders([]);
    querySubtitle.textContent = error instanceof Error ? error.message : "查询失败";
  } finally {
    queryOrdersButton.disabled = false;
    queryOrdersButton.textContent = "查询订单";
  }
});

document.querySelector("#action-type").addEventListener("change", toggleActionFields);
resetButton.addEventListener("click", resetForm);
missingDemoButton.addEventListener("click", () => {
  document.querySelector("#message").value = "帮我预约上门保洁";
});

copyButton.addEventListener("click", async () => {
  await navigator.clipboard.writeText(rawJson.textContent);
  copyButton.textContent = "✓";
  setTimeout(() => {
    copyButton.textContent = "⧉";
  }, 900);
});

copyActionButton.addEventListener("click", async () => {
  await navigator.clipboard.writeText(actionJson.textContent);
  copyActionButton.textContent = "✓";
  setTimeout(() => {
    copyActionButton.textContent = "⧉";
  }, 900);
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((item) => item.classList.remove("active"));
    tab.classList.add("active");
    document.querySelector(`#${tab.dataset.panel}`).classList.add("active");
  });
});

renderMissing([]);
renderParsedIntent(null);
renderCandidates([]);
renderFeatureGrid();
renderToolTable();
toggleActionFields();
syncQueryDefaults();
renderOrders([]);
refreshHealth();
