
const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('sendBtn');
const planItemsEl = document.getElementById('planItems');
const emptyState = document.getElementById('emptyState');
const identitySwitchEl = document.getElementById('identitySwitch');
const toolsPanelEl = document.getElementById('toolsPanel');
const tokenInputEl = document.getElementById('tokenInput');
const tokenStatusEl = document.getElementById('tokenStatus');

let loading = false;
let currentPersona = null;
let controlMode = 'simulated';                 // 控制执行模式(/api/state 注入);默认不真下发
let runTimerHandle = null;                     // 运行计时器 interval 句柄
let lastEventMs = 0;                           // 上一个事件的 t_ms(算步间隔)

function fmtMs(ms) {                            // 毫秒 → 人话(320ms / 2.3s)
  if (ms == null || isNaN(ms)) return '';
  return ms < 1000 ? ms + 'ms' : (ms / 1000).toFixed(1) + 's';
}

// ── 身份治理面板:persona 切换 + 可见工具(rt.toolset_for 实算) ─────────────────
const CONTROL_TOOLS = new Set(['execute_proposal']);

function renderIdentity(view) {
  currentPersona = view.persona;
  if (view.control_mode) controlMode = view.control_mode;   // simulated(默认)/ real → 确认卡措辞
  // header 身份按钮
  identitySwitchEl.innerHTML = '';
  for (const p of (view.personas || [])) {
    const btn = document.createElement('button');
    btn.className = 'persona-btn' + (p.id === view.persona ? ' active' : '');
    btn.textContent = p.name;
    btn.title = p.role;
    btn.disabled = loading;
    btn.onclick = () => switchPersona(p.id);
    identitySwitchEl.appendChild(btn);
  }
  // sidebar 可见工具 + 权限码
  toolsPanelEl.innerHTML = '';
  const perms = document.createElement('div');
  perms.className = 'perms';
  perms.textContent = '权限码: ' + ((view.permissions || []).join(' · ') || '(无)');
  toolsPanelEl.appendChild(perms);
  if (!view.tools || view.tools.length === 0) {
    const e = document.createElement('div');
    e.className = 'plan-empty';
    e.textContent = '无可见工具';
    toolsPanelEl.appendChild(e);
  }
  for (const t of (view.tools || [])) {
    const row = document.createElement('div');
    const isControl = CONTROL_TOOLS.has(t.name);
    row.className = 'tool-row' + (isControl ? ' control' : '');
    const dot = document.createElement('span');
    dot.className = 'tool-dot';
    const txt = document.createElement('span');
    txt.textContent = t.label;
    row.appendChild(dot);
    row.appendChild(txt);
    toolsPanelEl.appendChild(row);
  }
  if ('token_hint' in view) renderTokenStatus(view.token_hint);
}

function renderTokenStatus(hint) {
  if (hint) {
    tokenStatusEl.textContent = '已设置 · ' + hint;
    tokenStatusEl.className = 'token-status set';
  } else {
    tokenStatusEl.textContent = '未设置 · 用默认';
    tokenStatusEl.className = 'token-status';
  }
}

async function applyToken() {
  const tok = tokenInputEl.value.trim();
  try {
    const resp = await fetch('/api/token', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({token: tok}),
    });
    if (resp.ok) {
      const v = await resp.json();
      renderTokenStatus(v.token_hint);
      tokenInputEl.value = '';   // 不在 DOM 里留存令牌
    }
  } catch (e) { /* demo:静默 */ }
}

async function loadState() {
  try {
    const resp = await fetch('/api/state');
    if (resp.ok) renderIdentity(await resp.json());
  } catch (e) { /* demo:静默 */ }
}

async function switchPersona(pid) {
  if (loading || pid === currentPersona) return;
  try {
    const resp = await fetch('/api/identity', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({persona: pid}),
    });
    if (resp.ok) renderIdentity(await resp.json());
  } catch (e) { /* demo:静默 */ }
}

// Auto-resize textarea
inputEl.addEventListener('input', () => {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
});

inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!loading) sendMessage();
  }
});

function setLoading(val) {
  loading = val;
  sendBtn.disabled = val;
  inputEl.disabled = val;
  // 运行中禁用身份切换(避免半途换身份导致 toolset/权限错位)
  identitySwitchEl.querySelectorAll('.persona-btn').forEach(b => { b.disabled = val; });
}

function hideEmpty() {
  if (emptyState) emptyState.style.display = 'none';
}

function scrollBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function sendChip(text) {
  if (loading) return;
  inputEl.value = text;
  sendMessage();
}

// ── plan 侧边栏渲染(结构化 items with live status badges) ────────────────────
const STATUS_ICON = { todo: '○', doing: '◐', done: '●' };
const STATUS_LABEL = { todo: '待办', doing: '进行中', done: '已完成' };

function renderPlanItems(items) {
  // 清空旧内容
  planItemsEl.innerHTML = '';
  if (!items || items.length === 0) {
    const emp = document.createElement('div');
    emp.className = 'plan-empty';
    emp.textContent = '暂无';
    planItemsEl.appendChild(emp);
    return;
  }
  for (const item of items) {
    const st = item.status || 'todo'; // todo|doing|done
    const div = document.createElement('div');
    div.className = 'plan-item status-' + st;
    div.dataset.id = item.id;

    const icon = document.createElement('span');
    icon.className = 'plan-item-icon ' + st;
    icon.textContent = STATUS_ICON[st] || '○';

    const body = document.createElement('div');
    body.className = 'plan-item-text';
    const txt = document.createElement('div');
    txt.textContent = item.content;
    const lbl = document.createElement('div');
    lbl.className = 'plan-item-label ' + st;
    lbl.textContent = STATUS_LABEL[st] || st;
    body.appendChild(txt);
    body.appendChild(lbl);

    div.appendChild(icon);
    div.appendChild(body);
    planItemsEl.appendChild(div);
  }
}

// ── done_what 进展行渲染(外部可见) ──────────────────────────────────────────
function appendDoneWhat(text) {
  const isError = text.startsWith('✗');
  const row = document.createElement('div');
  row.className = 'done-what-row' + (isError ? ' error' : '');
  row.textContent = text;
  messagesEl.appendChild(row);
  scrollBottom();
}

// ── 流式 fetch 核心 ───────────────────────────────────────────────────────────
function createTurnProcessBlock() {
  const details = document.createElement('details');
  details.className = 'process-details';
  const summary = document.createElement('summary');
  summary.textContent = '过程 (0 步)';
  details.appendChild(summary);
  const inner = document.createElement('div');
  inner.className = 'process-inner';
  details.appendChild(inner);
  messagesEl.appendChild(details);
  return { details, summary, inner, count: 0 };
}

async function streamRequest(url, bodyObj, block) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(bodyObj),
  });
  if (!resp.ok) {
    throw new Error('HTTP ' + resp.status);
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buf = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split('\n');
    buf = lines.pop();
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      let ev;
      try { ev = JSON.parse(trimmed); } catch { continue; }
      handleStreamEvent(ev, block);
    }
  }
  if (buf.trim()) {
    try {
      const ev = JSON.parse(buf.trim());
      handleStreamEvent(ev, block);
    } catch {}
  }
}

function handleStreamEvent(ev, block) {
  switch (ev.event) {
    case 'process': {
      // 对内隐式:追加到过程折叠器
      const el = buildProcessItem(ev);
      if (el) {
        block.inner.appendChild(el);
        block.count++;
        block.summary.textContent = '过程 (' + block.count + ' 步)';
      }
      scrollBottom();
      break;
    }
    case 'done_what': {
      // 对外显式:在对话区显示进展行(NOT 在过程折叠器内)
      if (ev.text && ev.text.trim()) {
        appendDoneWhat(ev.text.trim());
      }
      break;
    }
    case 'plan': {
      // 对外显式:渲染结构化 plan 侧边栏(带状态徽章)
      if (ev.items && ev.items.length > 0) {
        renderPlanItems(ev.items);
      } else if (ev.text) {
        // 回退:纯文本渲染
        planItemsEl.innerHTML = '<div style="padding:8px;font-size:12px;color:var(--muted);white-space:pre-wrap;font-family:monospace;">' + escHtml(ev.text) + '</div>';
      }
      break;
    }
    case 'pending': {
      for (const p of (ev.items || [])) {
        const card = buildConfirmCard(p);
        messagesEl.appendChild(card);
      }
      scrollBottom();
      break;
    }
    case 'answer': {
      if (ev.text && ev.text.trim()) {
        typewriterBubble(ev.text.trim());     // 逐字显现(流式感)
      }
      break;
    }
    case 'done': {
      stopRunTimer();
      const ind = document.getElementById('runningIndicator');
      if (ind) ind.remove();
      if (ev.t_ms != null) {                  // 本次总耗时(对外显式)
        const tt = document.createElement('div');
        tt.className = 'run-total';
        tt.textContent = '⏱ 本次耗时 ' + fmtMs(ev.t_ms);
        messagesEl.appendChild(tt);
      }
      if (ev.status && ev.status !== 'completed') {
        const badge = document.createElement('span');
        badge.className = 'status-badge ' + statusClass(ev.status);
        badge.textContent = statusLabel(ev.status, ev.reason);
        messagesEl.appendChild(badge);
      }
      scrollBottom();
      break;
    }
  }
}

async function sendMessage() {
  const msg = inputEl.value.trim();
  if (!msg || loading) return;
  inputEl.value = '';
  inputEl.style.height = 'auto';
  hideEmpty();
  appendUserBubble(msg);
  setLoading(true);

  const indicator = appendRunningIndicator();
  const block = createTurnProcessBlock();

  try {
    await streamRequest('/api/chat', {message: msg}, block);
  } catch(err) {
    appendError('请求失败:' + err.message);
  } finally {
    stopRunTimer();
    indicator.remove();
    setLoading(false);
    scrollBottom();
  }
}

async function resetSession() {
  if (loading) return;
  await fetch('/api/reset', {method: 'POST'});
  messagesEl.innerHTML = '';
  messagesEl.appendChild(buildEmptyState());
  renderPlanItems([]);
  loadState();   // reset 重建运行时(清提案/账本),刷新身份面板
}

function buildEmptyState() {
  const d = document.createElement('div');
  d.className = 'empty-state';
  d.id = 'emptyState';
  d.innerHTML = '<h2>欢迎</h2><p>选个示例或直接发消息。设备控制(执行工具)会触发人工确认红线;右上角可切换身份,看可见工具随权限收缩。</p>';
  return d;
}

function appendUserBubble(text) {
  const d = document.createElement('div');
  d.className = 'bubble user';
  d.textContent = text;
  messagesEl.appendChild(d);
  scrollBottom();
}

function appendRunningIndicator() {
  const d = document.createElement('div');
  d.className = 'running-indicator';
  d.id = 'runningIndicator';
  d.innerHTML = '<div class="spinner"></div><span>运行中</span><span class="run-timer" id="runTimer">0.0s</span>';
  messagesEl.appendChild(d);
  // 实时秒表:每 100ms 刷新累计耗时(qwen 单步可达数十秒,让用户看见在跑、跑了多久)
  const start = performance.now();
  lastEventMs = 0;
  if (runTimerHandle) clearInterval(runTimerHandle);
  runTimerHandle = setInterval(() => {
    const t = document.getElementById('runTimer');
    if (t) t.textContent = ((performance.now() - start) / 1000).toFixed(1) + 's';
  }, 100);
  scrollBottom();
  return d;
}

function stopRunTimer() {
  if (runTimerHandle) { clearInterval(runTimerHandle); runTimerHandle = null; }
}

function typewriterBubble(text) {
  // 最终答案逐字显现:模型调用本身不流式(qwen 整段返回),前端做打字机效果给"流式输出"观感。
  const bubble = document.createElement('div');
  bubble.className = 'bubble assistant';
  messagesEl.appendChild(bubble);
  const step = Math.max(1, Math.round(text.length / 100));   // ~100 帧内显现完
  let i = 0;
  const iv = setInterval(() => {
    i += step;
    if (i >= text.length) {
      bubble.innerHTML = renderMarkdown(text);
      clearInterval(iv);
    } else {
      bubble.innerHTML = renderMarkdown(text.slice(0, i));
    }
    scrollBottom();
  }, 16);
}

function appendError(msg) {
  const d = document.createElement('div');
  d.className = 'trace-blocked';
  d.textContent = '⛔ ' + msg;
  messagesEl.appendChild(d);
}

function buildProcessItem(item) {
  const el = document.createElement('div');
  if (item.kind === 'think') {
    el.className = 'trace-think';
    el.textContent = '思考: ' + item.text;
  } else if (item.kind === 'say') {
    el.className = 'trace-say';
    el.textContent = item.text;
  } else if (item.kind === 'tool_call') {
    el.className = 'trace-tool-call';
    const argsStr = typeof item.args === 'object' ? JSON.stringify(item.args, null, 0) : String(item.args || '');
    el.textContent = '调用 ' + item.name + '(' + argsStr + ')';
  } else if (item.kind === 'tool_result') {
    el.className = 'trace-tool-result' + (item.is_error ? ' error' : '');
    const prefix = item.is_error ? '警告' : '返回';
    el.textContent = prefix + ' ' + item.name + ': ' + item.text;
  } else if (item.kind === 'blocked') {
    el.className = 'trace-blocked';
    el.textContent = '拦截 ' + item.text;
  } else {
    return null;
  }
  // 步耗时徽章(右侧):本步累计耗时 @X.Xs + 距上一步的增量(+Y.Ys),让慢在哪一步一目了然
  if (item.t_ms != null) {
    const delta = item.t_ms - lastEventMs;
    lastEventMs = item.t_ms;
    const t = document.createElement('span');
    t.className = 'trace-t';
    t.textContent = '@' + fmtMs(item.t_ms) + (delta > 50 ? ' +' + fmtMs(delta) : '');
    el.appendChild(t);
  }
  return el;
}

function buildConfirmCard(pending) {
  const card = document.createElement('div');
  card.className = 'confirm-card';
  // 无效/过期提案(模型编造 handle 或未先登记提案)→ 治理拦截:展示警示、不给"批准"
  if (pending.name === '__invalid_proposal__') {
    card.style.borderColor = 'var(--error)';
    card.innerHTML = `
      <h3 style="color:var(--error)">⛔ 提案无效 · 已被治理拦截</h3>
      <div class="confirm-action">模型给出的提案编号无效或已过期(未走「先登记提案、再执行」的流程)。系统**未下发任何控制**。</div>
      <div class="confirm-btns"><button class="btn-reject" onclick="cancelAction(this)">知道了</button></div>
    `;
    return card;
  }
  // 真实控制提案:把 grounded 参数渲染成人话 + 折叠原始 payload
  const a = pending.args || {};
  const human = (a.paramTypeName || a.paramTypeNo)
    ? `${a.paramTypeName || a.paramTypeNo} → ${a.paramValue || a.paramStatus || ''}` : '';
  const target = a.deviceId ? `设备 ${a.deviceId}` : '';
  const argsStr = typeof pending.args === 'object' ? JSON.stringify(pending.args, null, 2) : String(pending.args);
  const sim = controlMode !== 'real';
  const h3 = sim
    ? '🧪 控制操作 · 需要确认(模拟模式 · 确认后<b>不真实下发</b>)'
    : '⚠️ 控制操作 · 需要确认(不可逆,确认后<b>真实下发</b>)';
  card.innerHTML = `
    <h3>${h3}</h3>
    <div class="confirm-action"><b>${escHtml(pending.name)}</b>${human ? ' · ' + escHtml(human) : ''}${target ? '<br>' + escHtml(target) : ''}
      <br><span style="color:var(--muted);font-size:11px;">${escHtml(argsStr)}</span></div>
    <div class="confirm-btns">
      <button class="btn-approve" onclick="approveAction('${escAttr(pending.tool_call_id)}', this)">${sim ? '批准(模拟)' : '批准下发'}</button>
      <button class="btn-reject" onclick="cancelAction(this)">拒绝并取消</button>
    </div>
  `;
  return card;
}

async function approveAction(toolCallId, btn) {
  if (loading) return;
  const card = btn.closest('.confirm-card');
  card.querySelector('.confirm-btns').innerHTML = '<span style="color:var(--muted);font-size:13px;">处理中…</span>';
  setLoading(true);
  const indicator = appendRunningIndicator();
  const block = createTurnProcessBlock();
  try {
    await streamRequest('/api/confirm', {decisions: {[toolCallId]: 'approve'}}, block);
    card.remove();
  } catch(err) {
    appendError('确认请求失败:' + err.message);
    card.remove();
  } finally {
    indicator.remove();
    setLoading(false);
    scrollBottom();
  }
}

async function cancelAction(btn) {
  if (loading) return;
  const card = btn.closest('.confirm-card');
  card.querySelector('.confirm-btns').innerHTML = '<span style="color:var(--muted);font-size:13px;">处理中…</span>';
  setLoading(true);
  const indicator = appendRunningIndicator();
  const block = createTurnProcessBlock();
  try {
    await streamRequest('/api/confirm', {cancel: true}, block);
    card.remove();
  } catch(err) {
    appendError('取消请求失败:' + err.message);
    card.remove();
  } finally {
    indicator.remove();
    setLoading(false);
    scrollBottom();
  }
}

function statusClass(status) {
  if (status === 'completed') return 'completed';
  if (status === 'awaiting_confirmation') return 'awaiting';
  if (status === 'budget_exhausted') return 'budget';
  return 'failed';
}

// 失败/停止原因 → 人话(对齐引擎 reason:看门狗如实停,不伪装完成)
const REASON_LABEL = {
  no_progress: '连续多轮无有效进展,已停止',
  stall: '检测到原地踏步,已停止',
  tool_failures: '工具连续失败,已停止',
  model_error: '模型调用失败',
  empty_response: '模型空响应',
  persist_error: '持久化失败',
  interrupted: '已中断',
};

function statusLabel(status, reason) {
  if (status === 'budget_exhausted') return '步数用尽(已尽力收尾)';
  if (status === 'failed') return REASON_LABEL[reason] || ('失败' + (reason ? ':' + reason : ''));
  const map = {
    completed: '完成',
    awaiting_confirmation: '等待确认',
    interrupted: '已中断',
  };
  return map[status] || status;
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escAttr(s) {
  return String(s).replace(/'/g, "\'");
}

// 轻量 markdown -> 安全 HTML:先整体转义防 XSS,再按行转换结构,最后还原代码块。
// 覆盖:```代码块```、行内 `code`、# / ## / ### 标题、**粗体**、*斜体*、[文本](链接)、
// 无序(-/*)与有序(1.)列表、段落与换行。仅给助手回答气泡用。
function renderMarkdown(text) {
  const esc = (t) => String(t)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const blocks = [];
  // 1) 先抽出围栏代码块,用 \u0000B{n}\u0000 占位,内容转义后待还原。
  let s = String(text).replace(/```(\w*)\r?\n?([\s\S]*?)```/g, (m, lang, code) => {
    blocks.push('<pre><code>' + esc(code.replace(/\r?\n$/, '')) + '</code></pre>');
    return '\u0000B' + (blocks.length - 1) + '\u0000';
  });
  // 2) 转义剩余文本(占位符不含特殊字符,不受影响)。
  s = esc(s);
  // 行内变换(只作用于文本片段,不碰已抽出的代码块占位符)。
  const inline = (t) => t
    .replace(/`([^`\n]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="nofollow noopener">$1</a>');
  // 3) 按行解析结构。
  // 表格(表头 + 分隔行 + 数据行)整块抽成占位符,复用 blocks,避免走段落逻辑。
  {
    const isSep = (l) => /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/.test(l) && l.indexOf('-') >= 0;
    const splitRow = (l) => {
      let r = l.trim();
      if (r.charAt(0) === '|') r = r.slice(1);
      if (r.charAt(r.length - 1) === '|') r = r.slice(0, -1);
      return r.split('|').map((c) => c.trim());
    };
    const tl = s.split('\n'), ts = [];
    let ti = 0;
    while (ti < tl.length) {
      const cur = tl[ti];
      if (cur.indexOf('|') >= 0 && ti + 1 < tl.length && isSep(tl[ti + 1])) {
        const header = splitRow(cur);
        const aligns = splitRow(tl[ti + 1]).map((sep) => {
          const lc = sep.charAt(0) === ':', rc = sep.charAt(sep.length - 1) === ':';
          return (lc && rc) ? 'center' : (lc ? 'left' : (rc ? 'right' : ''));
        });
        ti += 2;
        const rows = [];
        while (ti < tl.length && tl[ti].indexOf('|') >= 0 && tl[ti].trim() !== '') { rows.push(splitRow(tl[ti])); ti += 1; }
        let h = '<table><thead><tr>';
        header.forEach((c, j) => { const a = aligns[j] ? ' style="text-align:' + aligns[j] + '"' : ''; h += '<th' + a + '>' + inline(c) + '</th>'; });
        h += '</tr></thead><tbody>';
        rows.forEach((row) => { h += '<tr>'; header.forEach((_, j) => { const a = aligns[j] ? ' style="text-align:' + aligns[j] + '"' : ''; h += '<td' + a + '>' + inline(row[j] || '') + '</td>'; }); h += '</tr>'; });
        h += '</tbody></table>';
        blocks.push(h);
        ts.push('\u0000B' + (blocks.length - 1) + '\u0000');
      } else { ts.push(cur); ti += 1; }
    }
    s = ts.join('\n');
  }
  const lines = s.split('\n');
  const out = [];
  let inUl = false, inOl = false, para = [];
  const closeLists = () => { if (inUl) { out.push('</ul>'); inUl = false; } if (inOl) { out.push('</ol>'); inOl = false; } };
  const flushPara = () => { if (para.length) { out.push('<p>' + para.join('<br>') + '</p>'); para = []; } };
  for (const line of lines) {
    if (/^\u0000B\d+\u0000$/.test(line)) { flushPara(); closeLists(); out.push(line); continue; }
    let m;
    if ((m = line.match(/^###\s+(.*)$/)))      { flushPara(); closeLists(); out.push('<h4>' + inline(m[1]) + '</h4>'); continue; }
    if ((m = line.match(/^##\s+(.*)$/)))       { flushPara(); closeLists(); out.push('<h3>' + inline(m[1]) + '</h3>'); continue; }
    if ((m = line.match(/^#\s+(.*)$/)))        { flushPara(); closeLists(); out.push('<h3>' + inline(m[1]) + '</h3>'); continue; }
    if ((m = line.match(/^\s*[-*]\s+(.*)$/)))  { flushPara(); if (!inUl) { closeLists(); out.push('<ul>'); inUl = true; } out.push('<li>' + inline(m[1]) + '</li>'); continue; }
    if ((m = line.match(/^\s*\d+\.\s+(.*)$/))) { flushPara(); if (!inOl) { closeLists(); out.push('<ol>'); inOl = true; } out.push('<li>' + inline(m[1]) + '</li>'); continue; }
    if (line.trim() === '') { flushPara(); closeLists(); continue; }
    closeLists();
    para.push(inline(line));
  }
  flushPara();
  closeLists();
  // 4) 还原代码块占位符。
  return out.join('\n').replace(/\u0000B(\d+)\u0000/g, (m, i) => blocks[+i]);
}

// 页面加载:拉取当前身份 + 可见工具(渲染身份面板)
loadState();
