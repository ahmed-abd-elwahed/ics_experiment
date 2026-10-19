"use strict";
// Flow diagrams of the Meeting 63 strategies for the View record tab (the proposal page's figures,
// laid out for the strategy column), and the steps that walk a case run through them. Each step
// lights one node and shows what that step read (In) and returned (Out), taken from the record:
// the iteration's question and rationale, the strategy's saved state (strategy_trace), the
// environment's answer, and the diagnosis.

const FLOWS = (() => {
  const NS = "http://www.w3.org/2000/svg";
  const RECT = { hw: 86, hh: 31 };
  const LANE = 190; // below the diagram: where the active step's In and Out appear
  const DEC = { hw: 92, hh: 46 };

  // --- diagrams ----------------------------------------------------------------------------------

  const loop = (o) => ({
    W: 470, H: 420,
    nodes: {
      ask: { x: 140, y: 90, kind: "llm", tag: "LLM", ...o.ask },
      upd: { x: 140, y: 230, kind: "llm", tag: "LLM", ...o.upd },
      stop: { x: 360, y: 230, kind: "dec", ...o.stop },
      dx: { x: 360, y: 360, kind: "llm", tag: "LLM", t: "Final differential", s: "up to 10, ranked" },
      end: { x: 140, y: 360, kind: "end", t: "Diagnosis" },
    },
    edges: {
      query: { pts: [[54, 90], [6, 90]], qa: true },
      answer: { pts: [[6, 230], [54, 230]], qa: true },
      toStop: { pts: [[226, 230], [268, 230]] },
      no: { pts: [[360, 184], [360, 90], [226, 90]], label: [368, 140, o.no || "no"] },
      yes: { pts: [[360, 276], [360, 329]], label: [368, 306, o.yes || "yes"] },
      toEnd: { pts: [[274, 360], [190, 360]] },
    },
  });

  const DIAGRAMS = {
    hypothesis: loop({
      ask: { t: "Pick the question", s: "that splits the top two" },
      upd: { t: "Update the differential", s: "probability per diagnosis" },
      stop: { t: "leader ≥ accept and", s: "ahead by ≥ margin?" },
    }),
    knowledge: loop({
      ask: { t: "Ask what is missing", s: "no diagnosis named" },
      upd: { t: "Recognise patterns", s: "findings → syndromes" },
      stop: { t: "a pattern with", s: "nothing missing?" },
    }),
    channel: {
      W: 470, H: 500,
      nodes: {
        ask: { x: 140, y: 100, kind: "llm", tag: "LLM ×2", t: "Ask within the channel", s: "then check its channel" },
        more: { x: 140, y: 230, kind: "dec", t: "channel", s: "used up?" },
        conf: { x: 360, y: 230, kind: "llm", tag: "LLM", t: "Diagnose and rate", s: "diagnosis + confidence" },
        sure: { x: 360, y: 360, kind: "dec", t: "confident, or", s: "no channel left?" },
        sw: { x: 140, y: 360, kind: "code", tag: "CODE", t: "Switch channel", s: "interview → exam" },
        dx: { x: 360, y: 470, kind: "llm", tag: "LLM", t: "Final differential", s: "up to 10, ranked" },
        end: { x: 140, y: 470, kind: "end", t: "Diagnosis" },
      },
      edges: {
        query: { pts: [[54, 92], [6, 92]], qa: true },
        answer: { pts: [[6, 230], [48, 230]], qa: true },
        no: { pts: [[140, 184], [140, 131]], label: [148, 162, "no"] },
        yes: { pts: [[232, 230], [274, 230]], label: [253, 222, "yes", "middle"] },
        toSure: { pts: [[360, 261], [360, 314]] },
        sureNo: { pts: [[268, 360], [226, 360]], label: [247, 352, "no", "middle"] },
        back: { pts: [[54, 360], [24, 360], [24, 116], [54, 116]], label: [30, 300, "ask"] },
        sureYes: { pts: [[452, 360], [462, 360], [462, 470], [446, 470]], label: [452, 420, "yes", "end"] },
        toEnd: { pts: [[274, 470], [190, 470]] },
      },
    },
    sequence: {
      W: 470, H: 420,
      bands: [[40, "Phase 1 · Initialization"], [160, "Phase 2 · Refinement"], [290, "Phase 3 · Final diagnosis"]],
      nodes: {
        open: { x: 150, y: 90, kind: "llm", tag: "LLM", t: "Ask opening questions", s: "complaint, history" },
        draft: { x: 370, y: 90, kind: "llm", tag: "LLM", t: "Draft the differential", s: "at most 5 candidates" },
        refine: { x: 150, y: 215, kind: "llm", tag: "LLM ×2", t: "Ask, then prune", s: "one candidate at a time" },
        confirm: { x: 150, y: 345, kind: "llm", tag: "LLM ×2", t: "Test the leader", s: "confirm or exclude" },
        dx: { x: 370, y: 345, kind: "llm", tag: "LLM", t: "Final differential", s: "up to 10, ranked" },
      },
      edges: {
        rail: { pts: [[40, 90], [40, 345]], plain: true },
        r1: { pts: [[40, 90], [62, 90]] }, r2: { pts: [[40, 215], [62, 215]] }, r3: { pts: [[40, 345], [62, 345]] },
        query: { pts: [[40, 262], [4, 262]], qa: true },
        answer: { pts: [[4, 290], [40, 290]], qa: true },
        toDraft: { pts: [[236, 90], [284, 90]], label: [260, 82, "after k", "middle"] },
        toRefine: { pts: [[370, 121], [370, 215], [236, 215]], label: [378, 170, "list ready"] },
        toFinal: { pts: [[150, 246], [150, 314]], label: [158, 282, "≤ 2 left or budget"] },
        toDx: { pts: [[236, 345], [284, 345]], label: [260, 337, "settled", "middle"] },
      },
    },
  };

  function el(tag, attrs = {}, text) {
    const node = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) if (v != null) node.setAttribute(k, String(v));
    if (text != null) node.textContent = text;
    return node;
  }

  function draw(name) {
    const d = DIAGRAMS[name];
    const svg = el("svg", { viewBox: `0 0 ${d.W} ${d.H + LANE}`, class: "flow-svg", role: "img", "aria-label": `Flow of the ${name} strategy` });
    const defs = el("defs");
    const marker = el("marker", { id: `fah-${name}`, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 9, markerHeight: 9, markerUnits: "userSpaceOnUse", orient: "auto-start-reverse" });
    marker.append(el("path", { d: "M0,1 L10,5 L0,9 Z", class: "fah" }));
    defs.append(marker);
    svg.append(defs);
    for (const [y, label] of d.bands || []) {
      svg.append(el("rect", { x: 56, y, width: d.W - 64, height: 110, rx: 8, class: "flow-band" }));
      svg.append(el("text", { x: d.W - 16, y: y + 102, "text-anchor": "end", class: "flow-band-label" }, label));
    }
    svg.append(el("line", { class: "flow-leader", x1: 0, y1: 0, x2: 0, y2: 0, visibility: "hidden" }));
    for (const [id, e] of Object.entries(d.edges)) {
      const g = el("g", { class: `flow-edge${e.qa ? " qa" : ""}`, "data-edge": id });
      g.append(el("polyline", { points: e.pts.map((p) => p.join(",")).join(" "), "marker-end": e.plain ? null : `url(#fah-${name})` }));
      if (e.label) g.append(el("text", { x: e.label[0], y: e.label[1], "text-anchor": e.label[3] || "start" }, e.label[2]));
      svg.append(g);
    }
    for (const [id, n] of Object.entries(d.nodes)) {
      const g = el("g", { class: `flow-node ${n.kind}`, "data-node": id });
      if (n.kind === "dec") {
        g.append(el("polygon", { class: "shape", points: [n.x - DEC.hw, n.y, n.x, n.y - DEC.hh, n.x + DEC.hw, n.y, n.x, n.y + DEC.hh].join(",") }));
        g.append(el("text", { x: n.x, y: n.y - 2, "text-anchor": "middle", class: "dtx" }, n.t));
        g.append(el("text", { x: n.x, y: n.y + 13, "text-anchor": "middle", class: "dtx" }, n.s));
      } else if (n.kind === "end") {
        g.append(el("rect", { class: "shape", x: n.x - 50, y: n.y - 22, width: 100, height: 44, rx: 22 }));
        g.append(el("text", { x: n.x, y: n.y + 4, "text-anchor": "middle", class: "ttl" }, n.t));
      } else {
        g.append(el("rect", { class: "shape", x: n.x - RECT.hw, y: n.y - RECT.hh, width: 2 * RECT.hw, height: 2 * RECT.hh, rx: 8 }));
        g.append(el("text", { x: n.x, y: n.y - 16, "text-anchor": "middle", class: "tag" }, n.tag));
        g.append(el("text", { x: n.x, y: n.y + 2, "text-anchor": "middle", class: "ttl" }, n.t));
        g.append(el("text", { x: n.x, y: n.y + 18, "text-anchor": "middle", class: "sub" }, n.s));
      }
      svg.append(g);
    }
    return svg;
  }

  // --- text of the inputs and outputs ------------------------------------------------------------

  const pct = (p) => `${Math.round(100 * (p ?? 0))}%`;
  const shorten = (text, n = 140) => (text && text.length > n ? `${text.slice(0, n - 1)}…` : text || "");

  function memoryLine(its, n) {
    if (!n) return "Memory: empty (nothing asked yet).";
    const last = its[n - 1];
    return `Memory: ${n} question${n === 1 ? "" : "s"} and answers; latest “${shorten(last.question, 70)}” → “${shorten(last.answer, 90)}”`;
  }
  function differentialLines(list) {
    if (!list || !list.length) return ["Differential: none yet."];
    return list.map((h) => `${pct(h.probability)} ${h.diagnosis}`);
  }
  function pictureLines(picture) {
    const patterns = picture?.patterns || [];
    if (!patterns.length) return ["Clinical picture: none yet."];
    return patterns.map((p) => `${p.name} — missing: ${(p.missing || []).join(", ") || "nothing"}`).concat(
      picture.basics_covered ? ["Basics covered."] : ["Basics not yet covered."],
    );
  }
  function finalLines(caseRun) {
    const d = caseRun.diagnosis;
    if (!d) return ["No diagnosis (the case run failed)."];
    if (d.error) return [`The diagnosis failed: ${d.error}`];
    return d.differential.map((x, i) => `${i + 1}. ${x.name} (${pct(x.probability)})`);
  }
  function truthLine(caseRun) {
    const truth = caseRun.case?.diagnosis;
    const names = (caseRun.diagnosis?.differential || []).map((x) => x.name.toLowerCase());
    const rank = truth ? names.indexOf(truth.toLowerCase()) : -1;
    return truth ? [`True diagnosis: ${truth}${rank >= 0 ? ` (named at rank ${rank + 1})` : ""}`] : [];
  }
  const questionLines = (it) => [`“${it.question}”`].concat(it.rationale ? [`Why: ${it.rationale}`] : []);
  const answerLines = (it) => (it.answer != null ? [`“${it.answer}”`] : [`The environment failed: ${it.error || "no answer"}`]);

  // --- steps --------------------------------------------------------------------------------------

  function envSteps(steps, it, i, from, to) {
    steps.push({ kind: "query", i, iteration: it, node: from, edges: ["query"] });
    steps.push({ kind: "answer", i, iteration: it, node: to, edges: ["answer"] });
  }

  function limitStep(caseRun, maxIter, node) {
    const reason = caseRun.stop_reason;
    if (reason === "max_iterations") {
      return { kind: "flow", node, title: "Iteration limit reached",
        input: [`${caseRun.iterations.length} of at most ${maxIter} questions asked.`],
        output: ["The runner ends the case run; the strategy's own stop rule is not checked."] };
    }
    return null;
  }

  function finalSteps(steps, caseRun, its, dxNode = "dx") {
    steps.push({ kind: "flow", node: dxNode, edges: [], title: "Final differential (LLM)",
      input: [memoryLine(its, its.length), "The strategy's notes from its last state."],
      output: finalLines(caseRun) });
    steps.push({ kind: "end", node: DIAGRAMS_HAS_END(caseRun) ? "end" : dxNode, edges: ["toEnd"], title: "Diagnosis",
      input: [`Stopped: ${caseRun.stop_reason.replace(/_/g, " ")}.`], output: [...finalLines(caseRun).slice(0, 3), ...truthLine(caseRun)] });
  }
  const DIAGRAMS_HAS_END = (caseRun) => Boolean(DIAGRAMS[caseRun.strategy_name]?.nodes.end);

  function loopSteps(caseRun, record, kind) {
    const its = caseRun.iterations;
    const params = record.strategies?.[caseRun.strategy]?.params || {};
    const maxIter = record.config?.stopping?.max_iterations;
    const state = (it) => (kind === "hypothesis" ? it?.strategy_trace?.differential : it?.strategy_trace?.picture);
    const lines = kind === "hypothesis" ? differentialLines : pictureLines;
    const updTitle = kind === "hypothesis" ? "Update the differential (LLM)" : "Recognise patterns (LLM)";
    const steps = [{ kind: "start", node: null }];
    const check = (st, stop) => {
      if (kind === "hypothesis") {
        const top = st?.[0]?.probability ?? 0;
        const second = st?.[1]?.probability ?? 0;
        return { input: [`Leader ${pct(top)}, runner-up ${pct(second)}; stop at ≥ ${pct(params.accept ?? 0.8)} with a lead ≥ ${pct(params.margin ?? 0.3)}.`],
          output: [stop ? "Yes: the hypothesis is satisficing; stop." : "No: keep collecting."] };
      }
      const done = (st?.patterns || []).filter((p) => (p.present || []).length && !(p.missing || []).length);
      return { input: [`${done.length} complete pattern${done.length === 1 ? "" : "s"}; basics ${st?.basics_covered ? "covered" : "not covered"}.`],
        output: [stop ? "Yes: the information is satisficing; stop." : "No: keep collecting."] };
    };
    its.forEach((it, i) => {
      if (i > 0) {
        steps.push({ kind: "flow", node: "upd", title: updTitle, input: [memoryLine(its, i), ...lines(state(its[i - 1])).map((l) => `Before: ${l}`)], output: lines(state(it)) });
        steps.push({ kind: "flow", node: "stop", edges: ["toStop"], title: "Stop rule (code)", ...check(state(it), false) });
      }
      const extra = kind === "hypothesis" ? (it.strategy_trace?.separates?.length ? [`Separates: ${it.strategy_trace.separates.join(" vs ")}`] : []) : it.strategy_trace?.fills ? [`Fills: ${it.strategy_trace.fills}`] : [];
      steps.push({ kind: "flow", node: "ask", edges: i > 0 ? ["no"] : [], title: kind === "hypothesis" ? "Pick the question (LLM)" : "Ask what is missing (LLM)",
        input: [memoryLine(its, i), ...lines(state(i > 0 ? it : null)).slice(0, 5)], output: [...questionLines(it), ...extra] });
      envSteps(steps, it, i, "ask", "upd");
    });
    if (caseRun.stop_reason === "strategy_done" && caseRun.diagnosis) {
      const last = caseRun.diagnosis.trace?.[kind === "hypothesis" ? "differential" : "picture"];
      steps.push({ kind: "flow", node: "upd", title: updTitle, input: [memoryLine(its, its.length)], output: lines(last) });
      steps.push({ kind: "flow", node: "stop", edges: ["toStop", "yes"], title: "Stop rule (code)", ...check(last, true) });
    } else {
      const limit = limitStep(caseRun, maxIter, "stop");
      if (limit) steps.push({ ...limit, edges: ["yes"] });
    }
    if (caseRun.status === "completed") finalSteps(steps, caseRun, its);
    else steps.push({ kind: "end", node: null, title: "Case run failed", input: [], output: [caseRun.error || caseRun.status] });
    return steps;
  }

  function channelSteps(caseRun, record) {
    const its = caseRun.iterations;
    const params = record.strategies?.[caseRun.strategy]?.params || {};
    const channels = params.channels || ["interview", "exam"];
    const maxIter = record.config?.stopping?.max_iterations;
    const cap = params.questions_per_channel || Math.max(1, Math.floor((maxIter || 2 * channels.length) / channels.length));
    const confident = params.confident ?? 0.8;
    const steps = [{ kind: "start", node: null }];
    let rejectedSeen = 0;
    let asked = 0;
    const assess = (a) => [`${a.diagnosis} — confidence ${pct(a.confidence)}`];
    its.forEach((it, i) => {
      const tr = it.strategy_trace || {};
      const prev = its[i - 1]?.strategy_trace;
      if (prev && tr.channel !== prev.channel) {
        const a = (tr.assessments || []).at(-1);
        steps.push({ kind: "flow", node: "more", edges: ["yes"], title: "Channel used up? (code)", input: [`${asked} of ${cap} questions asked in the ${prev.channel} channel.`], output: ["Yes: assess the diagnosis."] });
        if (a) steps.push({ kind: "flow", node: "conf", title: "Diagnose and rate (LLM)", input: [memoryLine(its, i)], output: assess(a) });
        steps.push({ kind: "flow", node: "sure", edges: ["toSure", "sureNo"], title: "Confident? (code)", input: [`Confidence ${pct(a?.confidence)}; threshold ${pct(confident)}.`], output: ["No: open the next channel."] });
        steps.push({ kind: "flow", node: "sw", edges: ["back"], title: "Switch channel (code)", input: [`Leaving: ${prev.channel}`], output: [`Now asking in: ${tr.channel}`] });
        asked = 0;
      } else if (i > 0) {
        steps.push({ kind: "flow", node: "more", edges: ["no"], title: "Channel used up? (code)", input: [`${asked} of ${cap} questions asked in the ${tr.channel} channel.`], output: ["No: ask again in this channel."] });
      }
      const rejected = (tr.rejected || []).slice(rejectedSeen);
      rejectedSeen = (tr.rejected || []).length;
      steps.push({ kind: "flow", node: "ask", title: `Ask within the ${tr.channel} channel (LLM ×2)`, input: [memoryLine(its, i), `Channel: ${tr.channel}`],
        output: [...rejected.map((r) => `Rejected (${r.kind}): “${shorten(r.question, 90)}”`), ...questionLines(it), `Classifier: ${tr.channel}`] });
      asked += 1;
      envSteps(steps, it, i, "ask", "more");
    });
    const end = caseRun.diagnosis?.trace || {};
    const last = its.at(-1)?.strategy_trace || {};
    if (caseRun.stop_reason === "strategy_done") {
      const a = (end.assessments || []).length > (last.assessments || []).length ? end.assessments.at(-1) : null;
      steps.push({ kind: "flow", node: "more", edges: ["yes"], title: "Channel used up? (code)", input: [`${asked} of ${cap} questions in the ${last.channel} channel, or nothing left to ask.`], output: ["Yes."] });
      if (a) steps.push({ kind: "flow", node: "conf", title: "Diagnose and rate (LLM)", input: [memoryLine(its, its.length)], output: assess(a) });
      steps.push({ kind: "flow", node: "sure", edges: ["toSure", "sureYes"], title: "Confident, or no channel left? (code)",
        input: [a ? `Confidence ${pct(a.confidence)}; threshold ${pct(confident)}.` : `${last.channel} is the last channel.`], output: ["Yes: stop."] });
    } else {
      const limit = limitStep(caseRun, maxIter, "more");
      if (limit) steps.push(limit);
    }
    if (caseRun.status === "completed") finalSteps(steps, caseRun, its);
    else steps.push({ kind: "end", node: null, title: "Case run failed", input: [], output: [caseRun.error || caseRun.status] });
    return steps;
  }

  function sequenceSteps(caseRun, record) {
    const its = caseRun.iterations;
    const maxIter = record.config?.stopping?.max_iterations;
    const steps = [{ kind: "start", node: null }];
    const askNode = { init: "open", refine: "refine", final: "confirm" };
    const cand = (list) => (list?.length ? list.map((c, i) => `${i + 1}. ${c}`) : ["(none yet)"]);
    its.forEach((it, i) => {
      const tr = it.strategy_trace || {};
      const prev = its[i - 1]?.strategy_trace;
      if (prev?.phase === "init" && tr.phase !== "init") {
        steps.push({ kind: "flow", node: "draft", edges: ["toDraft"], title: "Draft the differential (LLM)", input: [memoryLine(its, i)], output: cand(tr.candidates) });
      } else if (prev && prev.phase !== "init") {
        const title = prev.phase === "final" ? "Settle? (LLM): not settled" : "Prune the candidates (LLM)";
        steps.push({ kind: "flow", node: prev.phase === "final" ? "confirm" : "refine", title, input: [memoryLine(its, i), ...cand(prev.candidates).map((c) => `Before: ${c}`)], output: cand(tr.candidates) });
      }
      if (prev && prev.phase !== "final" && tr.phase === "final") {
        steps.push({ kind: "flow", node: "confirm", edges: ["toFinal"], title: "Move to the final phase (code)", input: [`${tr.candidates?.length ?? 0} candidates; ${i} of ${maxIter ?? "?"} questions asked.`], output: ["Two or fewer left, or the refinement budget is used."] });
      }
      steps.push({ kind: "flow", node: askNode[tr.phase] || "open", edges: ["r" + ({ init: 1, refine: 2, final: 3 }[tr.phase] || 1)], title: `Ask (${tr.phase} phase, LLM)`,
        input: [memoryLine(its, i), ...(tr.candidates?.length ? [`Candidates: ${tr.candidates.slice(0, 3).join("; ")}`] : [])], output: questionLines(it) });
      envSteps(steps, it, i, askNode[tr.phase] || "open", askNode[tr.phase] || "open");
    });
    const verdict = caseRun.diagnosis?.trace?.verdict;
    if (caseRun.stop_reason === "strategy_done" && verdict) {
      steps.push({ kind: "flow", node: "confirm", edges: ["toDx"], title: "Settle? (LLM)", input: [memoryLine(its, its.length)], output: [`${verdict.diagnosis}: ${verdict.settled ? "settled; stop" : "still open"}`] });
    } else {
      const limit = limitStep(caseRun, maxIter, "confirm");
      if (limit) steps.push({ ...limit, edges: ["toDx"] });
    }
    if (caseRun.status === "completed") finalSteps(steps, caseRun, its);
    else steps.push({ kind: "end", node: null, title: "Case run failed", input: [], output: [caseRun.error || caseRun.status] });
    return steps;
  }

  const BUILDERS = {
    hypothesis: (c, r) => loopSteps(c, r, "hypothesis"),
    knowledge: (c, r) => loopSteps(c, r, "knowledge"),
    channel: channelSteps,
    sequence: sequenceSteps,
  };
  const TITLES = {
    hypothesis: "1. Hypothesis-driven search",
    knowledge: "2. Knowledge-driven search",
    channel: "3. Channel-based",
    sequence: "4. Sequence-based",
  };

  // --- rendering ----------------------------------------------------------------------------------

  const cache = {};

  function render(host, name, step) {
    if (!cache[name]) cache[name] = draw(name);
    const svg = cache[name];
    let canvas = host.querySelector(".flow-canvas");
    if (!canvas || canvas.dataset.flow !== name) {
      host.replaceChildren();
      canvas = document.createElement("div");
      canvas.className = "flow-canvas";
      canvas.dataset.flow = name;
      canvas.append(svg);
      const card = document.createElement("div");
      card.className = "flow-card";
      card.hidden = true;
      canvas.append(card);
      host.append(canvas);
    }
    svg.querySelectorAll(".flow-node").forEach((g) => g.classList.toggle("active", g.dataset.node === step.node));
    svg.querySelectorAll(".flow-edge").forEach((g) => g.classList.toggle("active", (step.edges || []).includes(g.dataset.edge)));
    const card = canvas.querySelector(".flow-card");
    const node = DIAGRAMS[name].nodes[step.node];
    const text = step.kind === "flow" || step.kind === "end";
    card.hidden = !(text && node);
    if (card.hidden) {
      svg.querySelector(".flow-leader").setAttribute("visibility", "hidden");
      return;
    }
    const section = (label, lines) => {
      const div = document.createElement("div");
      div.className = "flow-io";
      const head = document.createElement("div");
      head.className = "flow-io-label";
      head.textContent = label;
      div.append(head);
      for (const line of lines || []) {
        const p = document.createElement("div");
        p.textContent = line;
        div.append(p);
      }
      return div;
    };
    const title = document.createElement("div");
    title.className = "flow-card-title";
    title.textContent = step.title || "";
    card.replaceChildren(title, section("In", step.input), section("Out", step.output));
    // The card fills the lane under the diagram; a dashed leader joins it to the node (drawn
    // under the nodes, so it never hides one).
    const d = DIAGRAMS[name];
    const total = d.H + LANE;
    card.style.top = `${((d.H + 8) / total) * 100}%`;
    card.style.height = `${((LANE - 12) / total) * 100}%`;
    const half = node.kind === "dec" ? DEC.hh : node.kind === "end" ? 22 : RECT.hh;
    const leader = svg.querySelector(".flow-leader");
    for (const [k, v] of Object.entries({ x1: node.x, y1: node.y + half, x2: node.x, y2: d.H + 8 })) leader.setAttribute(k, String(v));
    leader.setAttribute("visibility", "visible");
    card.scrollTop = 0;
  }

  return {
    has: (name) => Boolean(BUILDERS[name]),
    steps: (caseRun, record) => BUILDERS[caseRun.strategy_name](caseRun, record),
    title: (name) => TITLES[name] || name,
    render,
  };
})();
