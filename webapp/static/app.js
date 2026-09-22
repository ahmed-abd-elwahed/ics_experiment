"use strict";

// ICS experiment web app: run an experiment (Run tab) and step through a record (View tab).
// Record content comes from LLMs and literature, so it is only ever inserted as text.

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

// Children may be nested arrays; null and false are skipped, anything else becomes text.
function nodes(children) {
  return children
    .flat(Infinity)
    .filter((child) => child != null && child !== false)
    .map((child) => (child instanceof Node ? child : document.createTextNode(String(child))));
}

function h(tag, props, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value == null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : String(value));
  }
  node.append(...nodes(children));
  return node;
}

function fill(node, ...children) {
  node.replaceChildren(...nodes(children));
}

async function api(path, { method = "GET", body } = {}) {
  const options = { method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!response.ok) throw new Error((data && data.error) || `${response.status} ${response.statusText}`);
  return data;
}

// --- formatting ------------------------------------------------------------------------------

function money(value) {
  if (value == null) return "–";
  if (value === 0) return "$0";
  return value < 0.01 ? `$${value.toFixed(4)}` : `$${value.toFixed(3)}`;
}

function duration(seconds) {
  if (seconds == null) return "–";
  const total = Math.round(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hours) return `${hours}h ${String(minutes).padStart(2, "0")}m`;
  if (minutes) return `${minutes}m ${String(secs).padStart(2, "0")}s`;
  return seconds < 10 && seconds !== total ? `${seconds.toFixed(1)}s` : `${secs}s`;
}

function plural(n, word, many = `${word}s`) {
  return `${n} ${n === 1 ? word : many}`;
}

function when(iso) {
  if (!iso) return "–";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

function setMessage(element, text, kind = "info") {
  element.textContent = text || "";
  element.className = `message ${text ? kind : ""}`;
}

const STOP_LABELS = {
  max_iterations: "reached the iteration limit",
  max_seconds: "reached the time limit",
  strategy_done: "the strategy had nothing more to ask",
  cancelled: "the experiment was stopped",
  error: "an error ended the case run",
};

const PATH_LABELS = {
  case_study: "Answered from the case study",
  literature: "Synthesized from the literature (a simulation artifact, not a clinical claim)",
  ledger_hit: "Asked before: the stored answer was reused",
  ledger_hit_after_query_builder: "Asked before (same variable): the stored answer was reused",
  off_topic: "Not a question about the patient",
  withheld: "Withheld: the question asks for the diagnosis",
  query_builder_declined: "No literature answer is possible for this question",
  all_sources_failed: "The literature sources were unavailable",
  no_documents: "No relevant literature was found",
  inconsistent_with_case: "No answer consistent with the case could be synthesized",
  synthesizer_unanswerable: "The literature does not support an answer",
  empty_query: "Empty question",
};

const SOURCE_LABELS = { case_study: "case study", literature: "literature (synthesized)", unanswerable: "unanswerable" };

// --- tabs and the address bar ----------------------------------------------------------------

const app = { tab: "run" };
const VIEW_TABS = new Set(["view", "envruns"]);

function readHash() {
  const [tab, query] = location.hash.replace(/^#/, "").split("?");
  const params = new URLSearchParams(query || "");
  return { tab: VIEW_TABS.has(tab) ? tab : "run", params };
}

function writeHash() {
  let hash = `#${app.tab}`;
  if (VIEW_TABS.has(app.tab) && view.path) {
    const key = view.mode === "envruns" ? "source" : "record";
    const params = new URLSearchParams({ [key]: view.path, run: String(view.runIndex), step: String(view.step) });
    hash += `?${params}`;
  }
  if (location.hash !== hash) history.replaceState(null, "", hash);
}

function showTab(tab) {
  app.tab = tab;
  for (const button of $$(".tabs button")) button.setAttribute("aria-selected", String(button.dataset.tab === tab));
  $("#panel-run").hidden = tab !== "run";
  $("#panel-view").hidden = !VIEW_TABS.has(tab);
  if (VIEW_TABS.has(tab)) {
    view = viewers[tab];
    $("#panel-view").setAttribute("aria-labelledby", `tab-${tab}`);
    $("#record-source").hidden = tab !== "view";
    $("#envrun-source").hidden = tab !== "envruns";
    $("#caserun-label").textContent = tab === "envruns" ? "Case" : "Case run";
    $("#strategy-title").textContent = tab === "envruns" ? "Evaluation Questions" : "Information Gathering Strategy";
    renderViewer();
  }
  writeHash();
}

// =============================================================================================
// Run tab
// =============================================================================================

const run = { options: null, config: null, mode: "form", configName: null, pollTimer: null, lastStatus: null };

function numberOrNull(value) {
  if (value === "" || value == null) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function parseJsonField(textarea, label) {
  const text = textarea.value.trim();
  if (!text) return label === "Environment settings" ? {} : [];
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`${label} is not valid JSON: ${error.message}`);
  }
}

function formToConfig() {
  const f = $("#config-form").elements;
  const config = structuredClone(run.config || {});
  config.name = f.name.value.trim();
  config.cases_file = f.cases_file.value.trim();
  config.max_cases = numberOrNull(f.max_cases.value);
  const ids = f.case_ids.value.split(/[\s,]+/).filter(Boolean);
  config.case_ids = ids.length ? ids : null;
  config.initial_information = f.initial_information.value;
  config.stopping = {
    max_iterations: numberOrNull(f.max_iterations.value),
    max_seconds: numberOrNull(f.max_seconds.value),
  };
  config.workers = numberOrNull(f.workers.value) ?? 4;
  config.output = f.output.value.trim();
  config.strategies = parseJsonField(f.strategies, "Strategies");
  config.environment = parseJsonField(f.environment, "Environment settings");
  return config;
}

function configToForm(config) {
  const f = $("#config-form").elements;
  f.name.value = config.name ?? "";
  f.cases_file.value = config.cases_file ?? "";
  f.max_cases.value = config.max_cases ?? "";
  f.case_ids.value = (config.case_ids || []).join(", ");
  f.initial_information.value = config.initial_information || "none";
  f.max_iterations.value = config.stopping?.max_iterations ?? "";
  f.max_seconds.value = config.stopping?.max_seconds ?? "";
  f.workers.value = config.workers ?? 4;
  f.output.value = config.output ?? "";
  f.strategies.value = JSON.stringify(config.strategies ?? [], null, 2);
  f.environment.value = JSON.stringify(config.environment ?? {}, null, 2);
}

function currentConfig() {
  if (run.mode === "json") {
    try {
      return JSON.parse($("#config-json").value);
    } catch (error) {
      throw new Error(`The config is not valid JSON: ${error.message}`);
    }
  }
  return formToConfig();
}

function setConfig(config) {
  run.config = config;
  configToForm(config);
  $("#config-json").value = JSON.stringify(config, null, 2);
}

function setMode(mode) {
  const message = $("#config-message");
  try {
    const config = currentConfig();
    run.config = config;
    if (mode === "json") $("#config-json").value = JSON.stringify(config, null, 2);
    else configToForm(config);
  } catch (error) {
    setMessage(message, error.message, "error");
    return;
  }
  run.mode = mode;
  for (const button of $$(".segmented button")) button.setAttribute("aria-selected", String(button.dataset.mode === mode));
  $("#config-form").hidden = mode !== "form";
  $("#json-editor").hidden = mode !== "json";
}

function renderOptions() {
  const { options } = run;
  const select = $("#config-select");
  fill(select, ...options.configs.map((name) => h("option", { value: name, text: name })));
  if (run.configName) select.value = run.configName;
  fill($("#case-files"), ...options.case_files.map((path) => h("option", { value: path })));
  $("#environment-reference").textContent = JSON.stringify(options.environment_settings, null, 2);

  const help = $("#strategies-help");
  fill(help, 
    "A list of ",
    h("code", { text: "{name, label?, params}" }),
    ". Add the same strategy twice with different labels to compare settings. Available: ",
    ...options.strategies.flatMap((s, i) => [i ? "; " : "", h("strong", { text: s.name }), ` — ${s.description}`]),
  );
  fill($("#strategy-buttons"), 
    ...options.strategies.map((s) =>
      h("button", { type: "button", title: `Add the ${s.name} strategy with its default params`, onclick: () => addStrategy(s) }, `+ ${s.name}`),
    ),
  );
}

function addStrategy(strategy) {
  const textarea = $("#config-form").elements.strategies;
  let list;
  try {
    list = parseJsonField(textarea, "Strategies");
  } catch (error) {
    setMessage($("#config-message"), error.message, "error");
    return;
  }
  const entry = { name: strategy.name, params: structuredClone(strategy.params) };
  const keys = new Set(list.map((s) => (typeof s === "string" ? s : s.label || s.name)));
  if (keys.has(strategy.name)) {
    let n = 2;
    while (keys.has(`${strategy.name}_${n}`)) n += 1;
    entry.label = `${strategy.name}_${n}`;
  }
  list.push(entry);
  textarea.value = JSON.stringify(list, null, 2);
}

async function loadConfig(name) {
  const message = $("#config-message");
  try {
    const config = await api(`/api/configs/${encodeURIComponent(name)}`);
    run.configName = name;
    setConfig(config);
    setMessage(message, `Loaded configs/${name}.`, "info");
  } catch (error) {
    setMessage(message, error.message, "error");
  }
}

async function saveConfig(name) {
  const message = $("#config-message");
  try {
    const config = currentConfig();
    const result = await api(`/api/configs/${encodeURIComponent(name)}`, { method: "PUT", body: config });
    run.configName = name;
    run.options = await api("/api/options");
    renderOptions();
    setMessage(message, `Saved ${result.saved}.`, "ok");
  } catch (error) {
    setMessage(message, error.message, "error");
  }
}

function describePlan(plan) {
  const iterations = plan.max_iterations ? `, up to ${plan.max_iterations} iterations` : "";
  const strategies = plan.strategies.join(", ");
  return (
    `${plural(plan.cases, "case")} × ${plural(plan.strategies.length, "strategy", "strategies")} (${strategies}) = ` +
    `${plural(plan.case_runs, "case run")}${iterations}, ${plan.workers} in parallel.\n` +
    `Environment models: ${plan.models.join(", ")}.\nRecord: ${plan.output}`
  );
}

async function validateConfig() {
  const message = $("#config-message");
  let config;
  try {
    config = currentConfig();
  } catch (error) {
    setMessage(message, error.message, "error");
    return null;
  }
  const result = await api("/api/validate", { method: "POST", body: config });
  if (!result.ok) {
    setMessage(message, result.error, "error");
    return null;
  }
  setMessage(message, `Ready: ${describePlan(result.plan)}`, "ok");
  return { config, plan: result.plan };
}

async function startRun() {
  const message = $("#config-message");
  const button = $("#run-btn");
  button.disabled = true;
  try {
    const checked = await validateConfig();
    if (!checked) return;
    const ok = window.confirm(
      `Start the experiment?\n\n${describePlan(checked.plan)}\n\nThis calls OpenRouter and spends API credit.`,
    );
    if (!ok) return;
    await api("/api/runs", { method: "POST", body: checked.config });
    setMessage(message, "Experiment started.", "ok");
    pollRun();
  } catch (error) {
    setMessage(message, error.message, "error");
  } finally {
    button.disabled = false;
  }
}

async function stopRun() {
  if (!window.confirm("Stop the experiment? Running case runs stop after their current question; finished ones are kept.")) return;
  try {
    await api("/api/runs/current/cancel", { method: "POST", body: {} });
  } catch (error) {
    setMessage($("#config-message"), error.message, "error");
  }
}

const ACTIVE_STATES = new Set(["preparing", "running"]);

async function pollRun() {
  clearTimeout(run.pollTimer);
  let status;
  try {
    status = await api("/api/runs/current");
  } catch (error) {
    $("#progress-state").textContent = `Lost contact with the web app: ${error.message}`;
    run.pollTimer = setTimeout(pollRun, 3000);
    return;
  }
  renderProgress(status);
  if (ACTIVE_STATES.has(status.state)) run.pollTimer = setTimeout(pollRun, 1000);
}

function stat(label, value, wide = false) {
  return h("div", { class: wide ? "wide" : null }, h("dt", { text: label }), h("dd", { text: value }));
}

function renderProgress(status) {
  run.lastStatus = status;
  const state = status.state;
  const line = $("#progress-state");
  const texts = {
    idle: "No experiment running.",
    preparing: "Preparing: loading cases and checking models…",
    running: `Running “${status.name}”…`,
    completed: `Completed “${status.name}”.`,
    cancelled: `Stopped “${status.name}”. Finished case runs were saved.`,
    failed: `Failed: ${status.error || "unknown error"}`,
  };
  line.textContent = texts[state] || state;
  line.className = `state-line ${state}`;

  const fraction = state === "idle" ? 0 : status.fraction || 0;
  const bar = $("#progress-bar");
  bar.classList.toggle("running", state === "running");
  $(".progress-fill", bar).style.width = `${(fraction * 100).toFixed(1)}%`;
  $(".progress-label", bar).textContent = `${Math.floor(fraction * 100)}%`;
  bar.setAttribute("aria-valuenow", String(Math.floor(fraction * 100)));

  const stats = $("#progress-stats");
  if (state === "idle") {
    fill(stats);
  } else {
    fill(stats, 
      stat("Case runs", `${status.finished ?? 0} / ${status.total ?? "?"}`),
      stat("Iterations", String(status.iterations ?? 0)),
      stat("Cost", money(status.cost_usd)),
      stat("Elapsed", duration(status.elapsed_s)),
      stat("Time left", status.eta_s != null ? `~${duration(status.eta_s)}` : "–"),
      stat("Errors", String(status.errors ?? 0)),
      status.record ? stat("Record", status.record, true) : null,
    );
  }

  $("#stop-btn").hidden = !ACTIVE_STATES.has(state);
  const openButton = $("#open-record-btn");
  openButton.hidden = !(status.record && state !== "preparing" && (status.finished > 0 || !ACTIVE_STATES.has(state)));
  openButton.textContent = ACTIVE_STATES.has(state) ? "View finished case runs" : "Open record";
  $("#run-btn").disabled = ACTIVE_STATES.has(state);

  const active = $("#active-list");
  const runs = status.active || [];
  fill(active, 
    ...(runs.length
      ? runs.map((r) => {
          const limit = status.max_iterations ? ` / ${status.max_iterations}` : "";
          return h(
            "li",
            null,
            h("div", { class: "row" }, h("span", null, h("strong", { text: r.case_id }), ` · ${r.strategy}`), h("span", { class: "muted", text: `iteration ${r.iterations}${limit} · ${duration(r.elapsed_s)}` })),
            h("div", { class: "mini" }, h("div", { style: `width:${(r.fraction * 100).toFixed(1)}%` })),
          );
        })
      : [h("li", { class: "muted", text: "Nothing running." })]),
  );

  const recent = $("#recent-list");
  const finished = status.recent || [];
  fill(recent, 
    ...(finished.length
      ? finished.map((r) =>
          h(
            "li",
            { class: `status-${r.status}` },
            h(
              "div",
              { class: "row" },
              h("span", null, h("strong", { text: r.case_id }), ` · ${r.strategy}`),
              h("span", { class: "muted", text: `${plural(r.iterations, "iteration")} · ${duration(r.elapsed_s)} · ${money(r.cost_usd)}` }),
            ),
            h("div", { class: "muted", text: `Stopped: ${STOP_LABELS[r.stop_reason] || r.stop_reason}` }),
            r.error ? h("div", { class: "error", text: r.error }) : null,
          ),
        )
      : [h("li", { class: "muted", text: "None yet." })]),
  );
}

function openRunRecord() {
  const status = run.lastStatus;
  if (!status || !status.record) return;
  const path = ACTIVE_STATES.has(status.state) ? status.record.replace(/\.json$/, ".partial.jsonl") : status.record;
  showTab("view");
  refreshRecords(path).then(() => openRecord(path));
}

async function initRun() {
  try {
    run.options = await api("/api/options");
  } catch (error) {
    setMessage($("#config-message"), `Could not load options: ${error.message}`, "error");
    return;
  }
  const configs = run.options.configs;
  run.configName = configs.includes("basic.json") ? "basic.json" : configs[0] || null;
  renderOptions();
  if (run.configName) await loadConfig(run.configName);
  else setConfig({ name: "experiment", cases_file: run.options.case_files[0] || "", strategies: ["basic"], stopping: { max_iterations: 10 }, workers: 4, output: "records/{name}_{timestamp}.json", environment: {} });
  setMessage($("#config-message"), "");
  pollRun();
}

// =============================================================================================
// Viewer: experiment records (View record tab) and stored environment runs (Environment runs tab)
// =============================================================================================

// Each tab keeps its own position; both draw into the same scene.
const viewers = {
  view: { mode: "record", list: [], record: null, path: null, runIndex: 0, step: 0, steps: [], message: null },
  envruns: { mode: "envruns", list: [], record: null, path: null, runIndex: 0, step: 0, steps: [], message: null },
};
let view = viewers.view;

const isEnvRuns = () => view.mode === "envruns";

function viewMessage(target, text, kind = "info") {
  target.message = text ? { text, kind } : null;
  if (target === view && VIEW_TABS.has(app.tab)) setMessage($("#view-message"), text, kind);
}

function clamp(value, low, high) {
  return Math.max(low, Math.min(Number.isFinite(value) ? value : low, high));
}

// Show a loaded record (or environment run) in its tab; draw it if that tab is showing.
function loadInto(target, record, path, position = {}) {
  target.record = record;
  target.path = path;
  const runs = record.case_runs || [];
  target.runIndex = clamp(position.run ?? 0, 0, Math.max(0, runs.length - 1));
  target.steps = runs.length ? buildSteps(runs[target.runIndex]) : [];
  target.step = clamp(position.step ?? 0, 0, Math.max(0, target.steps.length - 1));
  if (!runs.length) {
    const text = record.status === "running" ? "No case run has finished yet. Refresh (↻) in a moment." : "Nothing to show: there are no case runs.";
    viewMessage(target, text, "info");
  }
  if (target === view && VIEW_TABS.has(app.tab)) renderViewer();
}

function renderViewer() {
  setMessage($("#view-message"), view.message?.text || "", view.message?.kind);
  const record = view.record;
  const runs = record?.case_runs || [];
  $("#viewer").hidden = runs.length === 0;
  if (!record) {
    fill($("#record-summary"));
    fill($("#caserun-select"));
    $("#strategy-select").hidden = true;
    writeHash();
    return;
  }
  renderRecordSummary();
  fillCaseRunSelect();
  if (runs.length) {
    $("#caserun-select").value = String(view.runIndex);
    renderStep();
  } else {
    writeHash();
  }
}

// --- experiment records ----------------------------------------------------------------------

async function refreshRecords(selectPath) {
  const target = viewers.view;
  try {
    const { records } = await api("/api/records");
    target.list = records;
  } catch (error) {
    viewMessage(target, error.message, "error");
    return;
  }
  const options = target.list.map((r) =>
    h("option", { value: r.path, text: `${r.path}${r.partial ? " (in progress)" : ""} — ${when(r.modified)}` }),
  );
  const wanted = selectPath || target.path;
  if (wanted && !target.list.some((r) => r.path === wanted)) options.unshift(h("option", { value: wanted, text: wanted }));
  if (!options.length) options.push(h("option", { value: "", text: "No records yet: run an experiment first" }));
  fill($("#record-select"), ...options);
  if (wanted) $("#record-select").value = wanted;
}

async function openRecord(path, position) {
  if (!path) return;
  const target = viewers.view;
  viewMessage(target, "Loading…");
  try {
    setRecord(await api(`/api/record?path=${encodeURIComponent(path)}`), path, position);
  } catch (error) {
    viewMessage(target, `Could not open ${path}: ${error.message}`, "error");
  }
}

function parseRecordText(text, name) {
  if (!name.endsWith(".jsonl")) return JSON.parse(text);
  let header = null;
  const caseRuns = [];
  for (const line of text.split("\n")) {
    if (!line.trim()) continue;
    let data;
    try {
      data = JSON.parse(line);
    } catch {
      continue; // a line cut short when the run stopped
    }
    if (data.type === "header") header = data;
    else if (data.type === "case_run") caseRuns.push(data);
  }
  if (!header) throw new Error("no header line");
  caseRuns.sort((a, b) => a.index - b.index);
  return { ...header, case_runs: caseRuns };
}

async function openRecordFile(file) {
  try {
    const record = parseRecordText(await file.text(), file.name);
    if (setRecord(record, null)) viewMessage(viewers.view, `Showing ${file.name} (opened from your computer).`, "info");
  } catch (error) {
    viewMessage(viewers.view, `${file.name} is not an experiment record: ${error.message}`, "error");
  }
}

function setRecord(record, path, position = {}) {
  if (!record || record.format !== "ics-experiment-record") {
    viewMessage(viewers.view, "This file is not an experiment record.", "error");
    return false;
  }
  viewMessage(viewers.view, "");
  loadInto(viewers.view, record, path, position);
  return true;
}

// --- stored environment runs -----------------------------------------------------------------

const ENV_KIND_LABELS = { medsim_runs: "Environment live checks", retrieval_benchmark: "Retrieval benchmark" };

async function refreshEnvRuns(selectPath) {
  const target = viewers.envruns;
  try {
    const { runs } = await api("/api/environment-runs");
    target.list = runs;
  } catch (error) {
    viewMessage(target, error.message, "error");
    return;
  }
  const groups = Object.entries(ENV_KIND_LABELS)
    .map(([kind, label]) => {
      const entries = target.list.filter((r) => r.kind === kind);
      if (!entries.length) return null;
      return h("optgroup", { label }, entries.map((r) => h("option", { value: r.path, text: `${r.name} — ${plural(r.questions, "question")}` })));
    })
    .filter(Boolean);
  if (!groups.length) groups.push(h("option", { value: "", text: "No stored environment runs found" }));
  fill($("#envrun-select"), ...groups);
  const wanted = selectPath || target.path;
  if (wanted) $("#envrun-select").value = wanted;
}

async function openEnvRun(path, position) {
  if (!path) return;
  const target = viewers.envruns;
  viewMessage(target, "Loading…");
  try {
    const data = await api(`/api/environment-run?path=${encodeURIComponent(path)}`);
    viewMessage(target, "");
    loadInto(target, envRunAsRecord(data), path, position);
  } catch (error) {
    viewMessage(target, `Could not open ${path}: ${error.message}`, "error");
  }
}

// An environment run in the shape the scene draws: each case is a "case run" whose iterations
// are the evaluation questions. There is no strategy; the questions were fixed in advance.
function envRunAsRecord(data) {
  const caseRuns = data.sessions.map((session, index) => {
    const iterations = session.questions.map((q, i) => ({
      index: i + 1,
      label: q.label,
      question: q.question,
      rationale: null,
      answer: q.response ? q.response.output_answer : null,
      answer_source: q.response ? q.response.answer_source : null,
      environment_response: q.response,
      environment_seconds: q.seconds,
      environment_cost_usd: q.cost_usd || 0,
      strategy_seconds: null,
      strategy_cost_usd: 0,
      error: q.error || (q.response ? null : "The run of this question failed."),
      truth: q.truth || null,
      removed_text: q.removed_text || [],
      grades: q.grades || {},
      answer_verdict: q.answer_verdict || null,
      meta: q.meta || {},
    }));
    return {
      index,
      case_id: session.case_id,
      strategy: null,
      case: session.case,
      note: session.note,
      initial_information: null,
      status: iterations.some((it) => it.error) ? "error" : "completed",
      stop_reason: null,
      error: null,
      elapsed_s: iterations.reduce((n, it) => n + (it.environment_seconds || 0), 0),
      strategy_cost_usd: 0,
      environment_cost_usd: iterations.reduce((n, it) => n + it.environment_cost_usd, 0),
      iterations,
    };
  });
  return { format: data.format, envrun: data, name: data.name, status: "completed", case_runs: caseRuns, case_runs_total: caseRuns.length };
}

// --- summary and case selection --------------------------------------------------------------

function renderRecordSummary() {
  const record = view.record;
  const runs = record.case_runs || [];
  const iterations = runs.reduce((n, r) => n + r.iterations.length, 0);
  const cost = runs.reduce((n, r) => n + r.strategy_cost_usd + r.environment_cost_usd, 0);
  const errors = runs.filter((r) => r.status === "error").length;
  if (isEnvRuns()) {
    const data = record.envrun;
    fill($("#record-summary"), 
      h("strong", { text: data.name }),
      h("span", { class: "badge", text: ENV_KIND_LABELS[data.kind] || data.kind }),
      h("span", { text: plural(runs.length, "case") }),
      h("span", { text: plural(iterations, "question") }),
      errors ? h("span", { class: "badge error", text: plural(errors, "case") + " with errors" }) : null,
      h("span", { text: `cost ${money(cost)}` }),
      data.model ? h("span", { class: "mono", text: data.model }) : null,
      data.generated_at ? h("span", { text: `run ${when(data.generated_at)}` }) : null,
      h("span", { class: "muted", text: data.description }),
    );
    return;
  }
  const overall = record.summary?.overall;
  const statusText = record.status === "running" ? "in progress" : record.status;
  fill($("#record-summary"), 
    h("strong", { text: record.name }),
    h("span", { class: `badge ${record.status === "completed" ? "ok" : record.status === "failed" ? "error" : ""}`, text: statusText }),
    h("span", { text: `${runs.length} / ${record.case_runs_total} case runs` }),
    h("span", { text: plural(overall?.iterations ?? iterations, "iteration") }),
    errors ? h("span", { class: "badge error", text: plural(errors, "error") }) : null,
    h("span", { text: `cost ${money(overall?.cost_usd?.total ?? cost)}` }),
    h("span", { text: `started ${when(record.started_at)}` }),
    record.elapsed_s != null ? h("span", { text: `took ${duration(record.elapsed_s)}` }) : null,
    record.error ? h("span", { class: "badge error", text: record.error }) : null,
    h(
      "details",
      null,
      h("summary", { text: "Config, environment settings, and strategies" }),
      h("pre", { text: JSON.stringify({ config: record.config, strategies: record.strategies, environment_settings: record.environment_settings, code_version: record.code_version }, null, 2) }),
    ),
  );
}

function caseRunLabel(r, i) {
  if (isEnvRuns()) {
    const set = r.iterations[0]?.meta?.question_set;
    return `${i + 1}. ${r.case_id}${set ? ` · set ${set}` : ""} — ${plural(r.iterations.length, "question")}${r.status === "error" ? " · error" : ""}`;
  }
  return `${i + 1}. ${r.case_id} · ${r.strategy} — ${plural(r.iterations.length, "iteration")}${r.status === "error" ? " · error" : ""}`;
}

function fillCaseRunSelect() {
  const runs = view.record.case_runs || [];
  fill($("#caserun-select"), ...runs.map((r, i) => h("option", { value: String(i), text: caseRunLabel(r, i) })));
  const strategies = [...new Set(runs.map((r) => r.strategy))];
  const strategySelect = $("#strategy-select");
  strategySelect.hidden = isEnvRuns() || strategies.length < 2;
  fill(strategySelect, ...strategies.map((s) => h("option", { value: s ?? "", text: s ?? "" })));
}

function currentRun() {
  return view.record?.case_runs?.[view.runIndex] || null;
}

function buildSteps(caseRun) {
  const steps = [{ kind: "start" }];
  caseRun.iterations.forEach((iteration, i) => {
    steps.push({ kind: "query", i, iteration });
    steps.push({ kind: "answer", i, iteration });
  });
  steps.push({ kind: "end" });
  return steps;
}

function selectRun(index, step = 0) {
  const runs = view.record.case_runs;
  view.runIndex = clamp(index, 0, runs.length - 1);
  view.steps = buildSteps(runs[view.runIndex]);
  view.step = clamp(step, 0, view.steps.length - 1);
  $("#caserun-select").value = String(view.runIndex);
  renderStep();
}

function goStep(step) {
  if (!view.steps.length) return;
  view.step = clamp(step, 0, view.steps.length - 1);
  renderStep();
}

function jumpCase(direction) {
  const runs = view.record?.case_runs || [];
  const current = currentRun();
  if (!current) return;
  if (isEnvRuns()) {
    selectRun(view.runIndex + direction, 0);
    return;
  }
  // The next case with the same strategy; any next case run if there is none.
  const indexes = runs.map((_, i) => i);
  const order = direction > 0 ? indexes.slice(view.runIndex + 1) : indexes.slice(0, view.runIndex).reverse();
  const target =
    order.find((i) => runs[i].strategy === current.strategy && runs[i].case_id !== current.case_id) ??
    order.find((i) => runs[i].case_id !== current.case_id) ??
    order[0];
  if (target != null) selectRun(target, 0);
}

function switchStrategy(strategy) {
  const runs = view.record.case_runs;
  const current = currentRun();
  const target = runs.findIndex((r) => r.strategy === strategy && r.case_id === current.case_id);
  const fallback = runs.findIndex((r) => r.strategy === strategy);
  if (target >= 0 || fallback >= 0) selectRun(target >= 0 ? target : fallback, 0);
}

// --- one step --------------------------------------------------------------------------------

function paths(response) {
  const params = response?.retriever_parameters || {};
  if (params.multi_part) return (params.sub_queries || []).map((s) => s.path);
  return params.path ? [params.path] : [];
}

function pathLabel(response) {
  const labels = [...new Set(paths(response).map((p) => PATH_LABELS[p] || p))];
  return labels.join("; ") || "Answered";
}

function stepText(caseRun, step) {
  const total = caseRun.iterations.length;
  const env = isEnvRuns();
  const unit = env ? "Question" : "Iteration";
  const response = step.iteration?.environment_response;
  if (step.kind === "start") {
    if (env) return ["Case loaded", `Case ${caseRun.case_id} is loaded into the environment; ${plural(total, "evaluation question")} follow.${caseRun.note ? ` ${caseRun.note}` : ""}`];
    return ["Case loaded", `Case ${caseRun.case_id} is loaded into the environment. The strategy ${caseRun.initial_information ? "is given the case's presentation" : "starts with no information about the patient"}.`];
  }
  if (step.kind === "query") {
    return [`${unit} ${step.i + 1} of ${total} · Query`, `${env ? "The evaluation asks" : "The strategy asks"}: “${step.iteration.question}”`];
  }
  if (step.kind === "answer") {
    if (step.iteration.error && !response) return [`${unit} ${step.i + 1} of ${total} · Answer`, `The environment failed: ${step.iteration.error}`];
    const next = env ? "" : " The answer is added to the strategy's memory.";
    return [`${unit} ${step.i + 1} of ${total} · Answer`, `${pathLabel(response)}.${next}`];
  }
  if (env) return ["All questions answered", `${plural(total, "question")} answered in ${duration(caseRun.elapsed_s)}.`];
  return ["Case run finished", `Stopped because ${STOP_LABELS[caseRun.stop_reason] || caseRun.stop_reason}, after ${plural(total, "iteration")} in ${duration(caseRun.elapsed_s)}.`];
}

function renderStep() {
  const caseRun = currentRun();
  if (!caseRun) return;
  const step = view.steps[view.step];
  const response = step.iteration?.environment_response || null;

  $("#step-range").max = String(view.steps.length - 1);
  $("#step-range").value = String(view.step);
  $("#step-count").textContent = `Step ${view.step + 1} of ${view.steps.length}`;
  $("#prev-step").disabled = view.step === 0;
  $("#next-step").disabled = view.step === view.steps.length - 1;
  $("#prev-case").disabled = view.runIndex === 0;
  $("#next-case").disabled = view.runIndex === view.record.case_runs.length - 1;
  $("#strategy-select").value = caseRun.strategy ?? "";

  const [title, caption] = stepText(caseRun, step);
  $("#step-title").textContent = title;
  $("#step-caption").textContent = caption;

  renderCaseRunHead(caseRun);
  renderCaseBox(caseRun, step, response);
  renderLiteratureBox(caseRun, step, response);
  renderLlmBox(caseRun, step, response);
  renderMessages(step);
  if (isEnvRuns()) renderQuestionsBox(caseRun, step);
  else renderStrategyBox(caseRun, step);

  const usedCase = step.kind === "start" || (step.kind === "answer" && step.iteration.answer_source === "case_study");
  const usedLiterature = step.kind === "answer" && Boolean(response?.literature_search);
  $("#node-case").classList.toggle("active", usedCase);
  $("#node-lit").classList.toggle("active", usedLiterature);
  $("#node-llm").classList.toggle("active", step.kind === "query" || step.kind === "answer");
  $("#msg-query").classList.toggle("active", step.kind === "query");
  $("#msg-answer").classList.toggle("active", step.kind === "answer");
  $("#node-strategy").classList.toggle("active", step.kind !== "answer" && step.kind !== "start");
  view.arrows = { case: usedCase && step.kind === "answer", lit: usedLiterature };
  requestAnimationFrame(drawEnvArrows);
  writeHash();
}

function renderCaseRunHead(caseRun) {
  const statusBadge = h("span", { class: `badge ${caseRun.status === "error" ? "error" : caseRun.status === "completed" ? "ok" : ""}`, text: caseRun.status });
  const cost = h("span", { text: `cost ${money(caseRun.strategy_cost_usd + caseRun.environment_cost_usd)}` });
  if (isEnvRuns()) {
    const meta = caseRun.iterations[0]?.meta || {};
    fill($("#caserun-head"), 
      h("strong", { text: caseRun.case_id }),
      meta.question_set ? h("span", { class: "badge", text: `set ${meta.question_set}` }) : null,
      h("span", { text: plural(caseRun.iterations.length, "question") }),
      statusBadge,
      h("span", { text: duration(caseRun.elapsed_s) }),
      cost,
    );
    return;
  }
  const strategy = view.record.strategies?.[caseRun.strategy];
  fill($("#caserun-head"), 
    h("strong", { text: caseRun.case_id }),
    h("span", { text: `strategy ${caseRun.strategy}${strategy && strategy.name !== caseRun.strategy ? ` (${strategy.name})` : ""}` }),
    h("span", { text: plural(caseRun.iterations.length, "iteration") }),
    statusBadge,
    h("span", { text: `stopped: ${STOP_LABELS[caseRun.stop_reason] || caseRun.stop_reason}` }),
    h("span", { text: duration(caseRun.elapsed_s) }),
    cost,
  );
}

function highlighted(text, spans) {
  const lower = text.toLowerCase();
  const ranges = [];
  for (const raw of spans) {
    const span = raw.trim().replace(/^["“]|["”]$/g, "");
    if (span.length < 4) continue;
    let from = 0;
    let at;
    while ((at = lower.indexOf(span.toLowerCase(), from)) !== -1) {
      ranges.push([at, at + span.length]);
      from = at + span.length;
    }
  }
  ranges.sort((a, b) => a[0] - b[0]);
  const merged = [];
  for (const range of ranges) {
    const last = merged[merged.length - 1];
    if (last && range[0] <= last[1]) last[1] = Math.max(last[1], range[1]);
    else merged.push([...range]);
  }
  const node = h("div", { class: "text" });
  let position = 0;
  for (const [start, end] of merged) {
    node.append(text.slice(position, start), h("mark", { text: text.slice(start, end) }));
    position = end;
  }
  node.append(text.slice(position));
  return node;
}

function renderCaseBox(caseRun, step, response) {
  const box = $("#box-case");
  const study = caseRun.case;
  if (!study) {
    fill(box, 
      h("div", { class: "kv" }, h("span", { class: "k", text: "Case" }), h("span", { class: "mono", text: caseRun.case_id })),
      h("p", { class: "placeholder", text: "The case text was not stored with this run." }),
    );
    return;
  }
  const spans = step.kind === "answer" && step.iteration.answer_source === "case_study" ? response?.evidence || [] : [];
  const background = study.metadata?.background_and_presentation;
  const hiddenFrom = isEnvRuns() ? "ground truth · never revealed by the environment" : "ground truth · never shown to the strategy";
  fill(box, 
    h("div", { class: "kv" }, h("span", { class: "k", text: "Case" }), h("span", { class: "mono", text: study.case_id })),
    caseRun.note ? h("p", { class: "muted", text: caseRun.note }) : null,
    h("div", { class: "diagnosis" }, h("span", { class: "badge", text: hiddenFrom }), h("strong", { text: study.diagnosis })),
    background ? [h("h4", { text: "Background and presentation" }), highlighted(background, spans)] : null,
    h("h4", { text: "Narrative" }),
    highlighted(study.narrative, spans),
  );
  const mark = $("mark", box);
  box.scrollTop = mark ? Math.max(0, mark.offsetTop - 60) : 0;
}

const GRADE_TITLES = {
  relevance: "Relevance (0-3): same variable, condition, and population as the question",
  usefulness: "Usefulness (0-2): gives a usable value for this variable",
};

function gradeBadges(grade) {
  if (!grade) return null;
  const badge = (name, value, max) =>
    value == null ? null : h("span", { class: `badge grade-${Math.min(value, 3)}`, title: GRADE_TITLES[name], text: `${name} ${value}/${max}` });
  return [
    badge("relevance", grade.relevance, 3),
    badge("usefulness", grade.usefulness, 2),
    grade.verdict ? h("span", { class: "badge", title: "The document's value compared with the hidden value", text: `vs truth: ${grade.verdict.replace("_", " ")}` }) : null,
  ];
}

function renderLiteratureBox(caseRun, step, response) {
  const box = $("#box-lit");
  box.scrollTop = 0;
  const placeholder = (text) => fill(box, h("p", { class: "placeholder", text }));
  if (step.kind === "start") return placeholder("Searched only when the case study cannot answer a question.");
  if (step.kind === "query") return placeholder("Waiting: the case study is checked first.");
  if (step.kind === "end") {
    const searched = caseRun.iterations.filter((it) => it.environment_response?.literature_search).length;
    return placeholder(`Searched for ${searched} of ${plural(caseRun.iterations.length, "question")}.`);
  }
  if (!response) return placeholder(step.iteration.error ? "No answer: the environment failed." : "No response recorded.");
  if (!response.literature_search) return placeholder(`Not searched. ${pathLabel(response)}.`);

  const result = response.literature_search_result;
  const cited = new Set(response.evidence || []);
  const grades = step.iteration.grades || {};
  const documents = result?.documents || [];
  const counts = Object.entries(result?.per_source_counts || {}).map(([source, n]) => `${source} ${n}`).join(", ");
  const excluded = response.retriever_parameters?.excluded_source_docs || [];
  fill(box, 
    h("h4", { text: "Query sent" }),
    h("div", { class: "query-text", text: result?.query || response.retriever_parameters?.literature_query || "–" }),
    h("p", { class: "muted", text: `${plural(documents.length, "document")}${counts ? ` (${counts})` : ""}${result?.latency_ms ? ` · ${duration(result.latency_ms / 1000)}` : ""}` }),
    excluded.length ? h("p", { class: "muted", text: `The case's own article was removed from the results (${excluded.join(", ")}).` }) : null,
    (result?.errors || []).map((e) => h("p", { class: "badge error", text: e })),
    h(
      "ol",
      { class: "docs" },
      documents.map((doc) => {
        const grade = grades[doc.doc_id];
        const link = /^https?:\/\//i.test(doc.url || "");
        return h(
          "li",
          null,
          h("div", { class: "badges" }, h("span", { class: "badge", text: doc.source }), cited.has(doc.doc_id) ? h("span", { class: "badge cited", text: "cited" }) : null, gradeBadges(grade)),
          h("div", { class: "doc-title" }, link ? h("a", { href: doc.url, target: "_blank", rel: "noopener noreferrer", text: doc.title || doc.doc_id }) : doc.title || doc.doc_id),
          h("div", { class: "doc-meta mono", text: [doc.doc_id, doc.journal, doc.pub_year].filter(Boolean).join(" · ") }),
          h("details", null, h("summary", { text: doc.text.length > 140 ? `${doc.text.slice(0, 140)}…` : doc.text }), h("div", { class: "text", text: doc.full_text || doc.text })),
          grade?.rationale
            ? h(
                "details",
                null,
                h("summary", { text: "Judge's reasoning" }),
                h("div", { class: "text", text: grade.rationale }),
                grade.evidence_quote ? h("div", { class: "muted text", text: `Quote: “${grade.evidence_quote}”` }) : null,
              )
            : null,
        );
      }),
    ),
  );
}

function callsTable(calls) {
  if (!calls?.length) return h("p", { class: "muted", text: "No LLM calls." });
  return h(
    "table",
    { class: "calls" },
    h(
      "tbody",
      null,
      calls.map((c) =>
        h(
          "tr",
          { class: c.success === false ? "failed" : null },
          h("td", { text: `${c.stage}${c.purpose && c.purpose !== "initial" ? ` (${c.purpose.replace("_", " ")})` : ""}` }),
          h("td", { text: `${c.prompt_tokens ?? "?"}→${c.completion_tokens ?? "?"} tok` }),
          h("td", { text: duration((c.latency_ms || 0) / 1000) }),
          h("td", { text: money(c.cost_usd) }),
        ),
      ),
    ),
  );
}

function renderLlmBox(caseRun, step, response) {
  const box = $("#box-llm");
  box.scrollTop = 0;
  if (step.kind === "start") {
    const settings = view.record.environment_settings || {};
    const model = settings.default_model || view.record.envrun?.model;
    const sources = settings.enabled_sources || [];
    fill(box, 
      h("p", { text: "Answers each question from the case study. When the case is silent, it searches the literature and synthesizes a plausible answer." }),
      model ? h("div", { class: "kv" }, h("span", { class: "k", text: "Model" }), h("span", { class: "mono", text: model })) : null,
      sources.length ? h("div", { class: "kv" }, h("span", { class: "k", text: "Sources" }), h("span", { text: sources.join(", ") })) : null,
    );
    return;
  }
  if (step.kind === "query") {
    fill(box, h("p", { class: "placeholder", text: "Received the question. Checking whether the case study answers it…" }));
    return;
  }
  if (step.kind === "end") {
    const counts = {};
    for (const it of caseRun.iterations) if (it.answer_source) counts[it.answer_source] = (counts[it.answer_source] || 0) + 1;
    const seconds = caseRun.iterations.reduce((n, it) => n + (it.environment_seconds || 0), 0);
    fill(box, 
      h("h4", { text: "Answers" }),
      h("div", { class: "badges" }, Object.entries(counts).map(([source, n]) => h("span", { class: `badge src-${source}`, text: `${SOURCE_LABELS[source] || source}: ${n}` }))),
      h("div", { class: "kv" }, h("span", { class: "k", text: "Time answering" }), h("span", { text: duration(seconds) })),
      h("div", { class: "kv" }, h("span", { class: "k", text: "Environment cost" }), h("span", { text: money(caseRun.environment_cost_usd) })),
    );
    return;
  }
  const iteration = step.iteration;
  if (!response) {
    fill(box, h("p", { class: "badge error", text: "Failed" }), h("p", { class: "text", text: iteration.error || "No response recorded." }));
    return;
  }
  const evidence = (response.evidence || []).filter(Boolean);
  fill(box, 
    h("div", { class: "badges" }, h("span", { class: `badge src-${response.answer_source}`, text: SOURCE_LABELS[response.answer_source] || response.answer_source }), h("span", { class: "badge", text: `confidence ${response.confidence}` })),
    h("p", { text: pathLabel(response) }),
    evidence.length ? [h("h4", { text: "Evidence" }), h("ul", null, evidence.map((e) => h("li", { text: e })))] : null,
    h("h4", { text: "LLM calls" }),
    callsTable(response.llm_calls),
    h("div", { class: "kv" }, h("span", { class: "k", text: "Answered in" }), h("span", { text: duration(iteration.environment_seconds) }), h("span", { class: "k", text: "· cost" }), h("span", { text: money(iteration.environment_cost_usd) })),
    response.used_llm ? h("div", { class: "kv" }, h("span", { class: "k", text: "Model" }), h("span", { class: "mono", text: response.used_llm })) : null,
  );
}

function renderMessages(step) {
  const query = $("#box-query");
  const answer = $("#box-answer");
  if (step.kind === "query" || step.kind === "answer") {
    fill(query, h("div", { class: "text", text: step.iteration.question }));
  } else {
    fill(query, h("span", { class: "placeholder", text: step.kind === "start" ? "No question yet." : "No more questions." }));
  }
  if (step.kind === "answer") {
    const it = step.iteration;
    fill(answer, it.error && it.answer == null ? h("div", { class: "badge error", text: "The environment failed; see the LLM box." }) : h("div", { class: "text", text: it.answer }));
  } else {
    fill(answer, h("span", { class: "placeholder", text: step.kind === "query" ? "Waiting for the environment…" : "—" }));
  }
}

function answeredCount(caseRun, step) {
  if (step.kind === "start") return 0;
  if (step.kind === "query") return step.i;
  if (step.kind === "answer") return step.i + 1;
  return caseRun.iterations.length;
}

function renderStrategyBox(caseRun, step) {
  const box = $("#box-strategy");
  const info = view.record.strategies?.[caseRun.strategy] || {};
  const memory = caseRun.iterations.slice(0, answeredCount(caseRun, step)).filter((it) => it.answer != null);
  const params = info.params ? Object.entries(info.params).map(([k, v]) => `${k}: ${v ?? "default"}`).join(" · ") : "";

  let current = null;
  if (step.kind === "query") {
    const it = step.iteration;
    current = h(
      "div",
      { class: "asking" },
      h("strong", { text: "Asks: " }),
      it.question,
      it.rationale ? h("div", { class: "muted", text: `Why: ${it.rationale}` }) : null,
      h("div", { class: "muted", text: `Took ${duration(it.strategy_seconds)} · ${money(it.strategy_cost_usd)}` }),
    );
  } else if (step.kind === "end") {
    const kind = caseRun.status === "error" ? "error" : caseRun.status === "cancelled" ? "cancelled" : "";
    current = h(
      "div",
      { class: `stop-banner ${kind}` },
      `Stopped: ${STOP_LABELS[caseRun.stop_reason] || caseRun.stop_reason}.`,
      caseRun.error ? h("div", { class: "text", text: caseRun.error }) : null,
    );
  }

  fill(box, 
    h("div", { class: "kv" }, h("span", { class: "k", text: "Strategy" }), h("strong", { text: caseRun.strategy }), info.name && info.name !== caseRun.strategy ? h("span", { class: "muted", text: `(${info.name})` }) : null),
    params ? h("div", { class: "kv muted", text: params }) : null,
    h("p", { class: "muted", text: caseRun.initial_information ? `Told at the start: ${caseRun.initial_information}` : "Started with no information about the patient." }),
    current,
    h("h4", { text: `Memory · ${plural(memory.length, "answer")}` }),
    memory.length
      ? h(
          "ol",
          { class: "memory" },
          memory.map((it, i) =>
            h("li", { class: step.kind === "answer" && i === memory.length - 1 ? "new" : null }, h("div", { class: "q", text: it.question }), h("div", { text: it.answer })),
          ),
        )
      : h("p", { class: "placeholder", text: "Empty." }),
  );
  const fresh = $(".memory li.new", box) || $(".asking", box) || $(".stop-banner", box);
  box.scrollTop = fresh ? Math.max(0, fresh.offsetTop - 40) : 0;
}

const VERDICT_LABELS = {
  close: "close to the hidden value",
  same_category: "same category as the hidden value (low / normal / high)",
  different_category: "a different category from the hidden value",
  not_comparable: "not comparable with the hidden value",
};

// Environment runs: the questions were fixed in advance, so the right-hand panel lists them all
// and, for benchmark questions, shows the hidden value and the judge's verdict on the answer.
function renderQuestionsBox(caseRun, step) {
  const box = $("#box-strategy");
  const answered = answeredCount(caseRun, step);
  const currentIndex = step.kind === "query" || step.kind === "answer" ? step.i : -1;
  const it = currentIndex >= 0 ? caseRun.iterations[currentIndex] : null;

  let detail = null;
  if (it) {
    const meta = it.meta || {};
    const truth = it.truth;
    const verdict = step.kind === "answer" ? it.answer_verdict : null;
    detail = [
      h("div", { class: "asking" }, h("strong", { text: "Asks: " }), it.question, it.label ? h("div", { class: "muted mono", text: it.label }) : null),
      meta.variable ? h("div", { class: "kv" }, h("span", { class: "k", text: "Variable" }), h("span", { text: `${meta.variable}${meta.category ? ` (${meta.category.replace("_", " ")})` : ""}` })) : null,
      truth
        ? h(
            "div",
            { class: "truth" },
            h("strong", { text: "Hidden value: " }),
            `${truth.value}${truth.unit ? ` ${truth.unit}` : ""}`,
            h("div", { class: "muted text", text: `Removed from the case: “${truth.span}”` }),
          )
        : meta.question_set === "B"
          ? h("p", { class: "muted", text: "Set B: there is no hidden value; the case never states this." })
          : null,
      verdict
        ? h(
            "div",
            null,
            h("h4", { text: "Judge on the answer" }),
            h("div", { class: `verdict-${verdict.verdict}` }, h("strong", { text: VERDICT_LABELS[verdict.verdict] || verdict.verdict })),
            verdict.reference_range ? h("div", { class: "muted", text: `Reference range: ${verdict.reference_range}` }) : null,
            h("div", { class: "text", text: verdict.rationale }),
          )
        : null,
    ];
  }

  fill(box, 
    detail,
    h("h4", { text: `Questions · ${answered} of ${caseRun.iterations.length} answered` }),
    h(
      "ol",
      { class: "memory" },
      caseRun.iterations.map((q, i) =>
        h(
          "li",
          { class: i === currentIndex ? "current" : i >= answered ? "upcoming" : null },
          h("div", { class: "q", text: q.question }),
          i < answered ? h("div", { text: q.answer ?? q.error ?? "" }) : null,
        ),
      ),
    ),
  );
  const current = $(".memory li.current", box);
  box.scrollTop = current && step.kind !== "query" && step.kind !== "answer" ? Math.max(0, current.offsetTop - 40) : 0;
}

// --- arrows inside the environment -----------------------------------------------------------

function drawEnvArrows() {
  const svg = $("#env-arrows");
  if (!svg || $("#viewer").hidden || !VIEW_TABS.has(app.tab) || getComputedStyle(svg).display === "none") return;
  const env = $("#env").getBoundingClientRect();
  const robot = $("#node-llm .robot").getBoundingClientRect();
  const llmBox = $("#box-llm").getBoundingClientRect();
  const lines = [];
  const arrows = view.arrows || {};
  for (const [key, nodeId, offset] of [["case", "#node-case", -10], ["lit", "#node-lit", 10]]) {
    const node = $(nodeId).getBoundingClientRect();
    const icon = $(`${nodeId} .icon`).getBoundingClientRect();
    const x1 = node.right - env.left + 8;
    const y1 = icon.top + icon.height / 2 - env.top;
    let x2 = robot.left - env.left - 4;
    let y2 = robot.top + robot.height * 0.55 + offset - env.top;
    // Stop short of the LLM's text box when the line would run underneath it.
    const [bx, by, bw, bh] = [llmBox.left - env.left - 8, llmBox.top - env.top - 8, llmBox.width + 16, llmBox.height + 16];
    for (let t = 0; t <= 1; t += 0.01) {
      const x = x1 + (x2 - x1) * t;
      const y = y1 + (y2 - y1) * t;
      if (x >= bx && x <= bx + bw && y >= by && y <= by + bh) {
        [x2, y2] = [x, y];
        break;
      }
    }
    const marker = arrows[key] ? "url(#head-active)" : "url(#head)";
    lines.push(`<line class="${arrows[key] ? "active" : ""}" x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" marker-start="${marker}" marker-end="${marker}"/>`);
  }
  svg.setAttribute("viewBox", `0 0 ${env.width.toFixed(1)} ${env.height.toFixed(1)}`);
  svg.innerHTML =
    '<defs><marker id="head" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path class="head" d="M0,0 L10,5 L0,10 z"/></marker>' +
    '<marker id="head-active" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="11" markerHeight="11" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path class="head-active" d="M0,0 L10,5 L0,10 z"/></marker></defs>' +
    lines.join("");
}

// --- wiring ----------------------------------------------------------------------------------

function wire() {
  for (const button of $$(".tabs button")) button.addEventListener("click", () => showTab(button.dataset.tab));

  for (const button of $$(".segmented button")) button.addEventListener("click", () => setMode(button.dataset.mode));
  $("#config-load").addEventListener("click", () => loadConfig($("#config-select").value));
  $("#config-save").addEventListener("click", () => {
    const name = $("#config-select").value;
    if (name && window.confirm(`Overwrite configs/${name}?`)) saveConfig(name);
  });
  $("#config-save-as").addEventListener("click", () => {
    let name = window.prompt("Save as (a file name in configs/):", "my_experiment.json");
    if (!name) return;
    name = name.trim();
    if (!name.endsWith(".json")) name += ".json";
    saveConfig(name);
  });
  $("#validate-btn").addEventListener("click", () => validateConfig().catch((e) => setMessage($("#config-message"), e.message, "error")));
  $("#run-btn").addEventListener("click", startRun);
  $("#stop-btn").addEventListener("click", stopRun);
  $("#open-record-btn").addEventListener("click", openRunRecord);

  $("#record-select").addEventListener("change", (event) => openRecord(event.target.value));
  $("#records-refresh").addEventListener("click", async () => {
    const target = viewers.view;
    await refreshRecords();
    if (target.path) openRecord(target.path, { run: target.runIndex, step: target.step });
  });
  $("#record-file").addEventListener("change", (event) => {
    const [file] = event.target.files;
    if (file) openRecordFile(file);
    event.target.value = "";
  });
  $("#envrun-select").addEventListener("change", (event) => openEnvRun(event.target.value));
  $("#envruns-refresh").addEventListener("click", async () => {
    const target = viewers.envruns;
    await refreshEnvRuns();
    if (target.path) openEnvRun(target.path, { run: target.runIndex, step: target.step });
  });
  $("#caserun-select").addEventListener("change", (event) => selectRun(Number(event.target.value), 0));
  $("#strategy-select").addEventListener("change", (event) => switchStrategy(event.target.value));
  $("#prev-case").addEventListener("click", () => jumpCase(-1));
  $("#next-case").addEventListener("click", () => jumpCase(1));
  $("#prev-step").addEventListener("click", () => goStep(view.step - 1));
  $("#next-step").addEventListener("click", () => goStep(view.step + 1));
  $("#step-range").addEventListener("input", (event) => goStep(Number(event.target.value)));

  document.addEventListener("keydown", (event) => {
    if (!VIEW_TABS.has(app.tab) || !view.steps.length || event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.target instanceof Element && event.target.closest("input, textarea, select, [contenteditable]")) return;
    const actions = {
      ArrowRight: () => goStep(view.step + 1),
      ArrowLeft: () => goStep(view.step - 1),
      Home: () => goStep(0),
      End: () => goStep(view.steps.length - 1),
      n: () => jumpCase(1),
      N: () => jumpCase(1),
      p: () => jumpCase(-1),
      P: () => jumpCase(-1),
    };
    if (actions[event.key]) {
      event.preventDefault();
      actions[event.key]();
    }
  });

  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(drawEnvArrows, 80);
  });
}

function positionFrom(params) {
  return { run: Number(params.get("run") || 0), step: Number(params.get("step") || 0) };
}

async function init() {
  wire();
  const { tab, params } = readHash();
  showTab(tab);

  const recordPath = tab === "view" ? params.get("record") : null;
  await refreshRecords(recordPath);
  if (recordPath) openRecord(recordPath, positionFrom(params));
  else if (viewers.view.list.length) openRecord(viewers.view.list[0].path);
  else viewMessage(viewers.view, "No records yet. Run an experiment in the Run tab, or open a record file.", "info");

  const sourcePath = tab === "envruns" ? params.get("source") : null;
  await refreshEnvRuns(sourcePath);
  if (sourcePath) openEnvRun(sourcePath, positionFrom(params));
  else if (viewers.envruns.list.length) openEnvRun(viewers.envruns.list[0].path);
  else viewMessage(viewers.envruns, "No stored environment runs found under environment/.", "info");

  initRun();
}

init();
