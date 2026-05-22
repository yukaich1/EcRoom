let currentSessionId = null;
let selectedSkill = null;
let pendingRenameId = "";
let pendingDeleteId = "";
let pendingEvolutionProposalId = "";
let sessionsCache = [];
let assetsCache = [];
let currentManifest = null;
let currentAsset = null;
let currentPreviewItem = null;
let activeFeedCategory = "discover";
let activeProfileTab = "published";
let activeAssetFilter = "all";
let activeSettingsSection = "model";
let pendingTypingTimer = null;
let learningCollapsed = true;
let learningCandidatesCache = [];
let learningSessionCompleted = false;
let avatarState = { image: null, offsetX: 0, offsetY: 0, scale: 1, minScale: 1, dragging: false, lastX: 0, lastY: 0 };

const els = {
  appFrame: document.querySelector("#appFrame"),
  inspirationScreen: document.querySelector("#inspirationScreen"),
  generateScreen: document.querySelector("#generateScreen"),
  chatScreen: document.querySelector("#chatScreen"),
  assetsScreen: document.querySelector("#assetsScreen"),
  assetDetailScreen: document.querySelector("#assetDetailScreen"),
  profileScreen: document.querySelector("#profileScreen"),
  settingsScreen: document.querySelector("#settingsScreen"),
  inspirationNavBtn: document.querySelector("#inspirationNavBtn"),
  generateNavBtn: document.querySelector("#generateNavBtn"),
  brandHomeBtn: document.querySelector("#brandHomeBtn"),
  assetButton: document.querySelector("#assetButton"),
  newChatBtn: document.querySelector("#newChatBtn"),
  collapseSidebarBtn: document.querySelector("#collapseSidebarBtn"),
  expandSidebarBtn: document.querySelector("#expandSidebarBtn"),
  sessionList: document.querySelector("#sessionList"),
  createForm: document.querySelector("#createForm"),
  inspirationCreateForm: document.querySelector("#inspirationCreateForm"),
  request: document.querySelector("#request"),
  inspirationRequest: document.querySelector("#inspirationRequest"),
  skillButton: document.querySelector("#skillButton"),
  inspirationSkillButton: document.querySelector("#inspirationSkillButton"),
  chatSkillButton: document.querySelector("#chatSkillButton"),
  selectedSkillLabel: document.querySelector("#selectedSkillLabel"),
  inspirationSkillLabel: document.querySelector("#inspirationSkillLabel"),
  chatSkillLabel: document.querySelector("#chatSkillLabel"),
  skillMenu: document.querySelector("#skillMenu"),
  feedTabs: document.querySelectorAll(".feed-tab"),
  inspirationGrid: document.querySelector("#inspirationGrid"),
  feedSearch: document.querySelector("#feedSearch"),
  assetSearch: document.querySelector("#assetSearch"),
  assetFilterButtons: document.querySelectorAll(".asset-filter-button"),
  assetGrid: document.querySelector("#assetGrid"),
  assetNewButton: document.querySelector("#assetNewButton"),
  assetBackButton: document.querySelector("#assetBackButton"),
  assetDetailTitle: document.querySelector("#assetDetailTitle"),
  assetWorkType: document.querySelector("#assetWorkType"),
  assetFinalContent: document.querySelector("#assetFinalContent"),
  assetPrompt: document.querySelector("#assetPrompt"),
  assetMeta: document.querySelector("#assetMeta"),
  remixAssetButton: document.querySelector("#remixAssetButton"),
  openAssetSessionButton: document.querySelector("#openAssetSessionButton"),
  chatTitle: document.querySelector("#chatTitle"),
  chatUpdatedAt: document.querySelector("#chatUpdatedAt"),
  chatTitleEditBtn: document.querySelector("#chatTitleEditBtn"),
  themeToggleBtn: document.querySelector("#themeToggleBtn"),
  messageList: document.querySelector("#messageList"),
  learningPanel: document.querySelector("#learningPanel"),
  learningToggleBtn: document.querySelector("#learningToggleBtn"),
  learningSummary: document.querySelector("#learningSummary"),
  learningToggleText: document.querySelector("#learningToggleText"),
  learningList: document.querySelector("#learningList"),
  feedbackForm: document.querySelector("#feedbackForm"),
  feedbackNote: document.querySelector("#feedbackNote"),
  settingsBtn: document.querySelector("#settingsBtn"),
  profileBtn: document.querySelector("#profileBtn"),
  settingsForm: document.querySelector("#settingsForm"),
  memoryPolicyForm: document.querySelector("#memoryPolicyForm"),
  settingsNavItems: document.querySelectorAll(".settings-nav-item"),
  settingsPanels: document.querySelectorAll(".settings-panel"),
  llmProvider: document.querySelector("#llmProvider"),
  llmModel: document.querySelector("#llmModel"),
  llmBaseUrl: document.querySelector("#llmBaseUrl"),
  llmApiKey: document.querySelector("#llmApiKey"),
  testLlmBtn: document.querySelector("#testLlmBtn"),
  preferenceList: document.querySelector("#preferenceList"),
  refreshPreferencesBtn: document.querySelector("#refreshPreferencesBtn"),
  memoryCandidateLimit: document.querySelector("#memoryCandidateLimit"),
  memoryMinConfidence: document.querySelector("#memoryMinConfidence"),
  memoryCompleteOnly: document.querySelector("#memoryCompleteOnly"),
  profilePageNickname: document.querySelector("#profilePageNickname"),
  profilePageBio: document.querySelector("#profilePageBio"),
  profilePageSaveBtn: document.querySelector("#profilePageSaveBtn"),
  profileAvatarBtn: document.querySelector("#profileAvatarBtn"),
  profileAvatarImage: document.querySelector("#profileAvatarImage"),
  avatarFileInput: document.querySelector("#avatarFileInput"),
  profileShareBtn: document.querySelector("#profileShareBtn"),
  profileWorksCount: document.querySelector("#profileWorksCount"),
  profileLikesCount: document.querySelector("#profileLikesCount"),
  profileCollectsCount: document.querySelector("#profileCollectsCount"),
  profileTabs: document.querySelectorAll(".profile-tab"),
  profileGrid: document.querySelector("#profileGrid"),
  evolutionList: document.querySelector("#evolutionList"),
  renameModal: document.querySelector("#renameModal"),
  renameInput: document.querySelector("#renameInput"),
  cancelRenameBtn: document.querySelector("#cancelRenameBtn"),
  confirmRenameBtn: document.querySelector("#confirmRenameBtn"),
  deleteModal: document.querySelector("#deleteModal"),
  cancelDeleteBtn: document.querySelector("#cancelDeleteBtn"),
  confirmDeleteBtn: document.querySelector("#confirmDeleteBtn"),
  applyEvolutionModal: document.querySelector("#applyEvolutionModal"),
  applyEvolutionNote: document.querySelector("#applyEvolutionNote"),
  cancelApplyEvolutionBtn: document.querySelector("#cancelApplyEvolutionBtn"),
  confirmApplyEvolutionBtn: document.querySelector("#confirmApplyEvolutionBtn"),
  avatarModal: document.querySelector("#avatarModal"),
  avatarCanvas: document.querySelector("#avatarCanvas"),
  avatarZoom: document.querySelector("#avatarZoom"),
  cancelAvatarBtn: document.querySelector("#cancelAvatarBtn"),
  chooseAvatarBtn: document.querySelector("#chooseAvatarBtn"),
  saveAvatarBtn: document.querySelector("#saveAvatarBtn"),
  previewModal: document.querySelector("#previewModal"),
  closePreviewBtn: document.querySelector("#closePreviewBtn"),
  previewType: document.querySelector("#previewType"),
  previewTitle: document.querySelector("#previewTitle"),
  previewPrompt: document.querySelector("#previewPrompt"),
  previewOutput: document.querySelector("#previewOutput"),
  previewMeta: document.querySelector("#previewMeta"),
  likePreviewBtn: document.querySelector("#likePreviewBtn"),
  collectPreviewBtn: document.querySelector("#collectPreviewBtn"),
  applyPreviewBtn: document.querySelector("#applyPreviewBtn"),
  toast: document.querySelector("#toast"),
};

const providerDefaults = {
  mistral: { model: "mistral-small-latest", base_url: "https://api.mistral.ai/v1" },
  openai: { model: "gpt-4.1-mini", base_url: "https://api.openai.com/v1" },
  deepseek: { model: "deepseek-v4-pro", base_url: "https://api.deepseek.com" },
};

const skills = [
  ["creative_brief", "创作诊断", "模糊想法、需求拆解、路线判断"],
  ["source_grounded", "资料驱动", "链接、资料、规范、事实边界"],
  ["narrative_canon", "叙事设定", "角色、世界观、剧情一致性"],
  ["publish_ready", "发布适配", "平台语气、长度、标题、风险边界"],
  ["revision_studio", "深度改稿", "反馈响应、去模板感、风格重写"],
  ["variant_lab", "方案实验", "标题、开头、卖点、多方向比较"],
];

const feedItems = [
  { id: "seed_character_cold", category: "discover", title: "冷面新角色登场", type: "叙事设定", prompt: "写一个冷感新角色登场文案，适合后续改成微博宣发。要求：角色有压迫感，但不要中二；正文保留一个可继续扩展的世界观暗线。", final_content: "他走进来时，房间里先安静了一秒。\n\n没人知道他的名字，只看见那枚旧徽章被放在桌面中央。它来自早已消失的北境军团，也来自一场没人愿意再提起的失败。\n\n这不是英雄登场，更像一段旧账终于找到了债主。", tone: "cyan", skills: ["narrative_canon"], platforms: ["微博"] },
  { id: "seed_xhs_campaign", category: "campaign", title: "小红书活动笔记", type: "发布适配", prompt: "把游戏版本活动包装成小红书体验笔记，不要太硬广。需要包含：一句自然标题、体验感开头、三个玩家会在意的亮点，以及避免夸张承诺的表达。", final_content: "标题：这个版本最打动我的，反而是那些很小的细节\n\n本来只是想上线看看新活动，结果被几个不太起眼的地方留住了。比如任务节奏没有催着你跑，角色对话里也藏了不少后续伏笔。它不是那种一眼很炸的更新，但玩下来会觉得世界真的往前走了一点。", tone: "amber", skills: ["publish_ready"], platforms: ["小红书"] },
  { id: "seed_tide_city", category: "discover", title: "潮汐钟城市", type: "叙事设定", prompt: "写一段被潮汐钟控制的城市设定，带一点阴谋感。请输出：城市简介、核心冲突、三个可继续扩写的剧情钩子。", final_content: "这座城市每天只准在潮汐钟响起后醒来。\n\n钟声决定开市、审判、婚礼和葬礼，也决定一个人是否还能拥有明天。没人知道钟是谁造的，只知道每当它慢一拍，城里就会少掉一条街。\n\n剧情钩子：\n1. 守钟人发现自己的名字从城市档案里消失。\n2. 叛逃的修表师声称潮汐并不存在。\n3. 主角听见钟声里传来未来自己的求救。", tone: "violet", skills: ["narrative_canon"], platforms: [] },
  { id: "seed_polish_human", category: "short", title: "去掉 AI 味", type: "深度改稿", prompt: "请把一段明显像 AI 的文案改得更像真人写作。保留核心信息，减少套路连接词，让语气更具体、更自然。", final_content: "改法不是简单把句子写短，而是先删掉那些看起来很正确、但没人真的会这么说的话。保留信息点，再把它们放回一个具体场景里。读起来像有人真的经历过，这篇稿子才会站得住。", tone: "green", skills: ["revision_studio"], platforms: [] },
  { id: "seed_release_titles", category: "short", title: "发布节奏三连", type: "方案实验", prompt: "给我一组预热、上线当天、反馈转发的微博文案。要求每条都短，避免模板化感叹句，保留一点故事感。", final_content: "预热：有些门不是被打开的，是终于撑不住了。\n\n上线当天：新版本已开。先别急着做任务，去听听城门口那段对话。\n\n反馈转发：看到有人猜到了徽章的来历。只能说，你们离真相很近，也很危险。", tone: "red", skills: ["variant_lab"], platforms: ["微博"] },
  { id: "seed_norm_boundary", category: "campaign", title: "平台规范边界", type: "资料驱动", prompt: "生成内容时自动检查小红书和微博的表达边界。请给出一版发布前检查清单，并写一段更稳妥的活动说明。", final_content: "发布前先看四件事：有没有夸张承诺，是否像硬广，是否暗示未证实效果，是否把平台规则写进正文里。\n\n稳妥版本：这次活动更适合慢慢体验。它的重点不是奖励堆得多，而是把角色关系和地图细节往前推了一步。感兴趣的话，可以从支线任务开始看。", tone: "blue", skills: ["source_grounded"], platforms: ["小红书", "微博"] },
];

const agentNames = {
  orchestrator: "任务编排",
  intent_interpreter: "需求理解",
  researcher: "资料检索",
  strategist: "策略",
  draft_writer: "写作",
  editor: "编辑",
  critic: "评审",
  norm_steward: "规范",
  memory_curator: "记忆整理",
  context_builder: "上下文召回",
  canon_keeper: "设定",
};

initTheme();

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "请求失败");
  return data;
}

function showToast(text) {
  els.toast.textContent = text;
  els.toast.classList.add("show");
  window.setTimeout(() => els.toast.classList.remove("show"), 2200);
}

function initTheme() {
  const saved = localStorage.getItem("ecroom-theme") || "dark";
  document.documentElement.dataset.theme = saved === "light" ? "light" : "dark";
}

function toggleTheme() {
  const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("ecroom-theme", next);
  showToast(next === "light" ? "已切换到白天" : "已切换到黑夜");
}

function setBusy(isBusy, text = "生成中") {
  document.body.classList.toggle("is-busy", isBusy);
  if (isBusy) showToast(text);
}

function showScreen(name, push = true) {
  currentSessionId = name === "chat" ? currentSessionId : null;
  if (name !== "assetDetail") currentAsset = null;
  for (const screen of [els.inspirationScreen, els.generateScreen, els.chatScreen, els.assetsScreen, els.assetDetailScreen, els.profileScreen, els.settingsScreen]) {
    screen.classList.remove("active");
  }
  const target = name === "generate" ? els.generateScreen : name === "chat" ? els.chatScreen : name === "assets" ? els.assetsScreen : name === "assetDetail" ? els.assetDetailScreen : name === "profile" ? els.profileScreen : name === "settings" ? els.settingsScreen : els.inspirationScreen;
  target.classList.add("active");
  els.inspirationNavBtn.classList.toggle("active", name === "inspiration");
  els.generateNavBtn.classList.toggle("active", name === "generate" || name === "chat");
  els.assetButton.classList.toggle("active", name === "assets" || name === "assetDetail");
  els.profileBtn.classList.toggle("active", name === "profile");
  els.settingsBtn.classList.toggle("active", name === "settings");
  const historyVisible = name === "generate" || name === "chat";
  els.appFrame.classList.toggle("history-hidden", !historyVisible);
  if (push) {
    const path = name === "generate" ? "/#generate" : name === "assets" ? "/assets" : name === "profile" ? "/profile" : name === "settings" ? `/settings/${activeSettingsSection}` : "/";
    history.pushState({}, "", path);
  }
}

async function openSession(sessionId, push = true) {
  setBusy(true, "载入对话");
  try {
    const data = await api(`/api/session/${sessionId}`);
    currentSessionId = sessionId;
    await renderChat(data);
    showScreen("chat", false);
    if (push) history.pushState({ sessionId }, "", `/chat/${sessionId}`);
    await loadSessions();
  } finally {
    setBusy(false);
  }
}

async function openAssets(push = true) {
  await loadAssets();
  showScreen("assets", false);
  if (push) history.pushState({}, "", "/assets");
}

async function openProfile(push = true) {
  await loadAssets();
  renderProfile();
  showScreen("profile", false);
  if (push) history.pushState({}, "", "/profile");
}

async function openSettings(section = activeSettingsSection, push = true) {
  await loadSettings();
  setSettingsSection(section || "model", false);
  showScreen("settings", false);
  if (push) history.pushState({}, "", `/settings/${activeSettingsSection}`);
}

async function openAsset(assetId, push = true) {
  setBusy(true, "载入资产");
  try {
    const data = await api(`/api/asset/${assetId}`);
    currentAsset = data.asset || null;
    currentManifest = data.manifest || null;
    renderAssetDetail(currentAsset);
    renderEvolution(currentManifest);
    showScreen("assetDetail", false);
    if (push) history.pushState({ assetId }, "", `/asset/${assetId}`);
  } finally {
    setBusy(false);
  }
}

async function renderChat(data, options = {}) {
  stopPendingTyping();
  const state = data.state || {};
  const session = data.session || {};
  currentManifest = data.manifest || null;
  renderEvolution(currentManifest);
  const isCompleted = Boolean(session.completed);
  renderLearning(isCompleted ? data.learning?.candidates || [] : [], { completed: isCompleted });
  els.chatTitle.textContent = session.title || sessionTitle(state.session_id, state.intent?.raw_request || "新的创作");
  els.chatUpdatedAt.textContent = formatSessionTime(session.updated_at);
  els.messageList.innerHTML = "";
  appendMessage("user", state.intent?.raw_request || "", "你");
  const drafts = state.drafts || [];
  const feedbacks = state.human_feedback || [];
  if (!drafts.length) return appendMessage("assistant", "我还没有生成草稿。", "EcRoom");
  if (!feedbacks.length) return appendDraft(drafts[drafts.length - 1], state.comments || [], "创作版本", { stream: options.streamLastDraft, showComplete: true, completed: isCompleted });
  appendDraft(drafts[Math.min(1, drafts.length - 1)], [], "初始版本");
  for (const feedback of feedbacks) {
    const text = feedback.note || feedback.edited_text || "继续调整";
    appendMessage("user", text, "反馈");
  }
  await appendDraft(drafts[drafts.length - 1], state.comments || [], "根据反馈生成", { stream: options.streamLastDraft, showComplete: true, completed: isCompleted });
  els.messageList.scrollTop = els.messageList.scrollHeight;
}

function renderLearning(candidates = [], options = {}) {
  if (!els.learningPanel || !els.learningList) return;
  learningCandidatesCache = candidates;
  learningSessionCompleted = Boolean(options.completed ?? learningSessionCompleted);
  const visible = candidates.filter((item) => item.status === "candidate");
  if (!visible.length) {
    els.learningPanel.hidden = true;
    els.learningList.innerHTML = "";
    return;
  }
  els.learningPanel.hidden = false;
  els.learningPanel.classList.toggle("collapsed", learningCollapsed);
  els.learningSummary.textContent = learningSessionCompleted ? `${visible.length} 条偏好待确认` : `${visible.length} 条偏好待确认`;
  els.learningToggleText.textContent = learningCollapsed ? "展开" : "收起";
  els.learningList.innerHTML = "";
  for (const candidate of visible.slice(0, 5)) {
    const card = document.createElement("article");
    card.className = "learning-card";
    card.innerHTML = `
      <div class="learning-copy">
        <span>${escapeHtml(learningKindLabel(candidate.kind))}</span>
        <strong>${escapeHtml(normalizeCreativeText(candidate.content || ""))}</strong>
        <small>${escapeHtml(candidate.effect || candidate.reason || "")}</small>
      </div>
      <div class="learning-actions">
        <button type="button" data-learning-id="${escapeHtml(candidate.candidate_id)}" data-learning-action="preference">设为偏好</button>
        <button type="button" data-learning-id="${escapeHtml(candidate.candidate_id)}" data-learning-action="cancel">取消</button>
      </div>`;
    els.learningList.appendChild(card);
  }
}

function learningKindLabel(kind) {
  const labels = {
    preference: "偏好",
    project_rule: "项目规则",
    platform_rule: "平台规则",
  };
  return labels[kind] || "学习项";
}

function learningStatusLabel(status) {
  const labels = {
    global_active: "已设为偏好",
    ignored: "已取消",
  };
  return labels[status] || "已处理";
}

async function applyLearningItem(candidateId, action) {
  if (!candidateId || !action) return;
  await api(`/api/learning/${candidateId}`, { method: "POST", body: JSON.stringify({ action }) });
  showToast(action === "preference" || action === "global" ? "已保存到偏好" : "已取消");
  if (currentSessionId) {
    const data = await api(`/api/session/${currentSessionId}`);
    await renderChat(data);
  }
  if (action === "preference" || action === "global") await loadPreferences();
}

function toggleLearningPanel() {
  learningCollapsed = !learningCollapsed;
  renderLearning(learningCandidatesCache, { completed: learningSessionCompleted });
}

async function getWorkflowPreview(request, preferences = "") {
  try {
    return await api("/api/workflow/preview", { method: "POST", body: JSON.stringify({ request, preferences, project_id: "default" }) });
  } catch (error) {
    return { stages: defaultWorkflowStages(request) };
  }
}

function defaultWorkflowStages(request = "") {
  const platforms = [];
  if (request.includes("微博")) platforms.push("微博");
  if (request.includes("小红书")) platforms.push("小红书");
  return [
    { role: "intent_interpreter", name: "需求理解", detail: "提取目标、载体、约束和偏好。" },
    { role: "researcher", name: "资料检索", detail: platforms.length ? `识别到平台：${platforms.join("、")}，准备召回对应规范。` : "召回记忆和资料库。" },
    { role: "strategist", name: "创作策略", detail: "把需求、资料和规则转成创作策略。" },
    { role: "draft_writer", name: "初稿写作", detail: "生成第一版可继续讨论的草稿。" },
    { role: "editor", name: "改稿整理", detail: "整理表达，减少模板感。" },
    { role: "critic", name: "质量评审", detail: "检查清晰度和风格贴合度。" },
    { role: "norm_steward", name: "规范检查", detail: "检查平台规则和发布边界。" },
    { role: "memory_curator", name: "记忆沉淀", detail: "判断哪些信号需要进入记忆。" },
  ];
}

function renderPendingChat(request, preview = {}, status = "正在打磨第一版") {
  stopPendingTyping();
  currentSessionId = null;
  currentManifest = null;
  renderEvolution(null);
  renderLearning([], { completed: false });
  els.chatTitle.textContent = truncate(request, 22);
  els.chatUpdatedAt.textContent = "正在生成";
  els.messageList.innerHTML = "";
  appendMessage("user", request, "你");
  const item = document.createElement("article");
  item.className = "message assistant typing-message";
  item.id = "pendingTypingMessage";
  item.innerHTML = `
    <div class="message-label">EcRoom</div>
    <div class="typing-card">
      <div class="typing-title"><span class="typing-dot"></span><strong>${escapeHtml(status)}</strong></div>
      <div class="typing-line" id="typingLine"></div>
      <div class="workflow-steps" id="workflowSteps"></div>
    </div>`;
  els.messageList.appendChild(item);
  const stages = preview.stages?.length ? preview.stages : defaultWorkflowStages(request);
  renderWorkflowSteps(stages, 0);
  showScreen("chat", false);
  history.pushState({}, "", "/#working");
  let index = 0;
  pendingTypingTimer = window.setInterval(() => {
    index = Math.min(index + 1, stages.length - 1);
    renderWorkflowSteps(stages, index);
    if (index >= stages.length - 1 && pendingTypingTimer) window.clearInterval(pendingTypingTimer);
  }, 1100);
}

function renderWorkflowSteps(stages, activeIndex) {
  const line = document.querySelector("#typingLine");
  const box = document.querySelector("#workflowSteps");
  const active = stages[activeIndex] || stages[0] || {};
  if (line) line.textContent = `${active.name || agentNames[active.role] || "处理中"}：${active.detail || "正在处理当前阶段。"}`;
  if (!box) return;
  box.innerHTML = "";
  stages.forEach((stage, index) => {
    const step = document.createElement("div");
    step.className = `workflow-step ${index < activeIndex ? "done" : ""} ${index === activeIndex ? "active" : ""}`;
    step.textContent = stage.name || agentNames[stage.role] || stage.role || "阶段";
    box.appendChild(step);
  });
}

function workflowPreviewFromTrace(trace = []) {
  const stages = [];
  for (const item of trace) {
    const role = item.role || "";
    if (!role || stages.some((stage) => stage.role === role)) continue;
    stages.push({ role, name: item.name || agentNames[role] || role, detail: normalizeCreativeText(item.content || "已完成。").slice(0, 96) });
  }
  return stages;
}

function appendInlineTyping(status = "正在继续打磨", preview = {}) {
  stopPendingTyping();
  const item = document.createElement("article");
  item.className = "message assistant typing-message";
  item.id = "pendingTypingMessage";
  item.innerHTML = `
    <div class="message-label">EcRoom</div>
    <div class="typing-card compact">
      <div class="typing-title"><span class="typing-dot"></span><strong>${escapeHtml(status)}</strong></div>
      <div class="typing-line" id="typingLine"></div>
      <div class="workflow-steps" id="workflowSteps"></div>
    </div>`;
  els.messageList.appendChild(item);
  els.messageList.scrollTop = els.messageList.scrollHeight;
  const stages = preview.stages?.length ? preview.stages : [
    { role: "memory_curator", name: "反馈理解", detail: "识别反馈里的偏好、规则和直接修改要求。" },
    { role: "researcher", name: "上下文召回", detail: "重新召回相关记忆、资料和规范。" },
    { role: "editor", name: "改稿整理", detail: "根据反馈生成新版本。" },
    { role: "critic", name: "质量评审", detail: "检查新版本是否回应了反馈。" },
    { role: "memory_curator", name: "记忆沉淀", detail: "把稳定偏好和规则写入记忆。" },
  ];
  renderWorkflowSteps(stages, 0);
  let index = 0;
  pendingTypingTimer = window.setInterval(() => {
    index = Math.min(index + 1, stages.length - 1);
    renderWorkflowSteps(stages, index);
    if (index >= stages.length - 1 && pendingTypingTimer) window.clearInterval(pendingTypingTimer);
  }, 1100);
}

function stopPendingTyping() {
  if (pendingTypingTimer) {
    window.clearInterval(pendingTypingTimer);
    pendingTypingTimer = null;
  }
  document.querySelector("#pendingTypingMessage")?.remove();
}

function appendMessage(role, content, label) {
  const item = document.createElement("article");
  item.className = `message ${role}`;
  item.innerHTML = `<div class="message-label">${escapeHtml(label)}</div><div class="message-bubble"></div>`;
  item.querySelector(".message-bubble").textContent = normalizeCreativeText(content || "空内容");
  els.messageList.appendChild(item);
}

async function appendDraft(draft, comments, label = "创作版本", options = {}) {
  const item = document.createElement("article");
  item.className = "message assistant";
  const card = document.createElement("div");
  card.className = "draft-card";
  card.innerHTML = `<div class="draft-card-head">${escapeHtml(label)}</div><div class="draft-content"></div>`;
  const contentEl = card.querySelector(".draft-content");
  const content = normalizeCreativeText(draft?.content || "还没有内容。");
  if (options.stream) {
    contentEl.classList.add("is-streaming");
  } else {
    contentEl.textContent = content;
  }
  const notes = (comments || []).slice(-4);
  if (notes.length) {
    const noteBox = document.createElement("details");
    noteBox.className = "agent-notes";
    noteBox.innerHTML = `<summary>创作检查 · ${notes.length} 条</summary><div class="agent-note-list"></div>`;
    const noteList = noteBox.querySelector(".agent-note-list");
    for (const comment of notes) {
      const note = document.createElement("div");
      note.className = "agent-note";
      note.textContent = `${agentNames[comment.agent] || comment.agent || "Agent"}：${normalizeCreativeText(comment.comment)}`;
      noteList.appendChild(note);
    }
    card.appendChild(noteBox);
  }
  if (options.showComplete) {
    const actionBar = document.createElement("div");
    actionBar.className = "draft-card-actions";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "draft-complete-button";
    button.dataset.completed = options.completed ? "true" : "false";
    button.title = options.completed ? "回到继续创作状态，暂不沉淀长期偏好。" : "确认这轮话题已经完成，再选择是否沉淀偏好。";
    button.textContent = options.completed ? "撤销完成状态" : "完成话题";
    actionBar.appendChild(button);
    card.appendChild(actionBar);
  }
  item.innerHTML = '<div class="message-label">EcRoom</div>';
  item.appendChild(card);
  els.messageList.appendChild(item);
  if (options.stream) {
    await typeText(contentEl, content);
    contentEl.classList.remove("is-streaming");
  }
}

async function toggleSessionCompleted() {
  if (!currentSessionId) return;
  const currentButton = document.querySelector(".draft-complete-button");
  const completed = currentButton?.dataset.completed !== "true";
  setBusy(true, completed ? "确认完成" : "撤销完成");
  try {
    await api(`/api/session/${currentSessionId}/complete`, { method: "POST", body: JSON.stringify({ completed }) });
    const data = await api(`/api/session/${currentSessionId}`);
    await renderChat(data);
    showToast(completed ? "话题已完成，可以选择是否保存偏好" : "已回到继续创作状态");
  } finally {
    setBusy(false);
  }
}

function typeText(element, text) {
  return new Promise((resolve) => {
    const value = String(text || "");
    let index = 0;
    const chunkSize = value.length > 900 ? 5 : 3;
    const timer = window.setInterval(() => {
      index = Math.min(value.length, index + chunkSize);
      element.textContent = value.slice(0, index);
      els.messageList.scrollTop = els.messageList.scrollHeight;
      if (index >= value.length) {
        window.clearInterval(timer);
        resolve();
      }
    }, 18);
  });
}

function normalizeCreativeText(value) {
  return String(value || "")
    .replace(/\r\n/g, "\n")
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/\*\*([^*\n]+)\*\*/g, "$1")
    .replace(/__([^_\n]+)__/g, "$1")
    .replace(/\*([^*\n]+)\*/g, "$1")
    .replace(/`([^`\n]+)`/g, "$1")
    .replace(/^\s{0,3}[-*_]{3,}\s*$/gm, "")
    .replace(/^\s{0,3}[-*+]\s+/gm, "")
    .replace(/^\s{0,3}\d+[.)、]\s+/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function sessionTitle(sessionId, fallback = "新的创作") {
  const session = sessionsCache.find((item) => item.session_id === sessionId);
  return session?.title || truncate(fallback, 22);
}

function formatSessionTime(value) {
  const timestamp = Number(value || 0);
  if (!timestamp) return "最新对话";
  const date = new Date(timestamp * 1000);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const dayDiff = Math.round((startOfToday - startOfDate) / 86400000);
  const time = date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false });
  if (dayDiff === 0) return `今天 ${time}`;
  if (dayDiff === 1) return `昨天 ${time}`;
  const day = date.toLocaleDateString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" }).replaceAll("/", "/");
  return `${day} ${time}`;
}

function truncate(value, length) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > length ? `${text.slice(0, length)}...` : text;
}

async function loadSessions() {
  const data = await api("/api/sessions");
  sessionsCache = data.sessions || [];
  renderSessions(sessionsCache);
  renderInspirationGrid();
  renderEvolution(currentManifest);
  return sessionsCache;
}

async function loadAssets() {
  const data = await api("/api/assets?project_id=default");
  assetsCache = data.assets || [];
  renderAssetsPage();
  renderInspirationGrid();
  renderProfile();
  return assetsCache;
}

function renderSessions(sessions) {
  els.sessionList.innerHTML = "";
  if (!sessions.length) {
    els.sessionList.innerHTML = '<div class="empty-row">还没有对话。</div>';
    return;
  }
  for (const session of sessions) {
    const row = document.createElement("div");
    row.className = "session-row";
    row.tabIndex = 0;
    row.setAttribute("role", "button");
    row.dataset.sessionId = session.session_id;
    if (session.session_id === currentSessionId) row.classList.add("active");
    row.innerHTML = `
      <span class="session-icon"><svg aria-hidden="true"><use href="#i-chat"></use></svg></span>
      <span class="session-main"><span class="session-title">${escapeHtml(session.title || session.raw_request || "未命名对话")}</span></span>
      <span class="icon-button session-menu-button" role="button" aria-label="更多"><svg aria-hidden="true"><use href="#i-more"></use></svg></span>
      <span class="session-menu" aria-hidden="true">
        <button type="button" data-action="pin"><svg aria-hidden="true"><use href="#i-pin"></use></svg>${session.pinned ? "取消置顶" : "置顶"}</button>
        <button type="button" data-action="rename"><svg aria-hidden="true"><use href="#i-pen"></use></svg>重命名</button>
        <button type="button" data-action="delete"><svg aria-hidden="true"><use href="#i-trash"></use></svg>删除</button>
      </span>`;
    els.sessionList.appendChild(row);
  }
}

function renderInspirationGrid() {
  const query = (els.feedSearch?.value || "").trim();
  const reusableAssets = assetsCache.filter((item) => item.source !== "inspiration" || item.collected);
  const fromAssets = activeFeedCategory === "discover" ? reusableAssets.slice(0, 8).map((item, index) => ({
    id: item.asset_id,
    category: "discover",
    title: item.title || item.prompt,
    type: "你的创作",
    prompt: item.prompt,
    final_content: item.final_content,
    asset_id: item.asset_id,
    skills: item.skills || [],
    platforms: item.platforms || [],
    tone: ["cyan", "amber", "violet", "green", "red", "blue"][index % 6],
  })) : [];
  const sourceItems = feedItems.filter((item) => item.category === activeFeedCategory);
  const items = [...sourceItems, ...fromAssets].filter((item) => !query || `${item.title}${item.type}${item.prompt}${item.final_content || ""}`.includes(query));
  els.inspirationGrid.innerHTML = "";
  for (const item of items) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = `inspire-card tone-${item.tone}`;
    card.innerHTML = `<span>${escapeHtml(item.type)}</span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(truncate(item.prompt, 58))}</small>`;
    card.addEventListener("click", () => openPreview(item));
    els.inspirationGrid.appendChild(card);
  }
}

function openPreview(item) {
  const related = relatedAsset(item);
  const collectedAssetId = related?.collected ? related.asset_id : "";
  currentPreviewItem = { ...item, liked: Boolean(item.liked || related?.liked), asset_id: item.asset_id || collectedAssetId };
  els.previewTitle.textContent = currentPreviewItem.title || "灵感详情";
  els.previewType.textContent = currentPreviewItem.type || assetLabel(currentPreviewItem);
  els.previewPrompt.textContent = normalizeCreativeText(currentPreviewItem.prompt || "无");
  els.previewOutput.textContent = normalizeCreativeText(currentPreviewItem.final_content || "这条灵感还没有示例输出。");
  const meta = [];
  if (currentPreviewItem.platforms?.length) meta.push(currentPreviewItem.platforms.join(" / "));
  if (currentPreviewItem.skills?.length) meta.push(currentPreviewItem.skills.join(" / "));
  if (currentPreviewItem.category) meta.push(categoryName(currentPreviewItem.category));
  els.previewMeta.textContent = meta.join("  |  ") || "内容灵感";
  const collected = isCollected(currentPreviewItem);
  els.collectPreviewBtn.textContent = collected ? "取消收藏" : "收藏";
  els.likePreviewBtn.textContent = currentPreviewItem.liked ? "已喜欢" : "喜欢";
  els.previewModal.classList.add("open");
}

function closePreview() {
  els.previewModal.classList.remove("open");
}

function categoryName(category) {
  return { discover: "发现", short: "短文", campaign: "活动" }[category] || "发现";
}

function isCollected(item) {
  return Boolean(relatedAsset(item)?.collected);
}

function relatedAsset(item) {
  return assetsCache.find((asset) => asset.source_id === item.id || asset.asset_id === item.asset_id);
}

async function collectPreview() {
  if (!currentPreviewItem) return;
  const item = currentPreviewItem;
  const collected = isCollected(item);
  const data = await api(collected ? "/api/assets/uncollect" : "/api/assets/collect", {
    method: "POST",
    body: JSON.stringify(inspirationPayload(item, { liked: item.liked || false })),
  });
  showToast(collected ? "已取消收藏" : "已收藏到资产库");
  await loadAssets();
  currentPreviewItem = { ...item, asset_id: data.asset.asset_id };
  openPreview(currentPreviewItem);
}

async function likePreview() {
  if (!currentPreviewItem) return;
  const item = currentPreviewItem;
  const liked = !item.liked;
  const data = await api("/api/assets/like", {
    method: "POST",
    body: JSON.stringify(inspirationPayload(item, { liked, collected: isCollected(item) })),
  });
  currentPreviewItem = { ...item, liked, asset_id: data.asset.asset_id };
  await loadAssets();
  els.likePreviewBtn.textContent = liked ? "已喜欢" : "喜欢";
}

function inspirationPayload(item, overrides = {}) {
  return {
    source_id: item.id || item.asset_id,
    project_id: "default",
    title: item.title,
    prompt: item.prompt,
    final_content: item.final_content || "",
    goal: item.type,
    category: item.category || "discover",
    skills: item.skills || [],
    platforms: item.platforms || [],
    ...overrides,
  };
}

function applyPreview() {
  if (!currentPreviewItem) return;
  els.request.value = currentPreviewItem.prompt || "";
  closePreview();
  showScreen("generate");
  history.pushState({}, "", "/#generate");
  els.request.focus();
}

function renderProfile() {
  if (!els.profileGrid) return;
  if (!["published", "liked", "collected"].includes(activeProfileTab)) activeProfileTab = "published";
  const works = assetsCache.filter((asset) => asset.source !== "inspiration");
  const liked = assetsCache.filter((asset) => asset.liked);
  const collected = assetsCache.filter((asset) => asset.source === "inspiration" && asset.collected);
  const source = activeProfileTab === "liked" ? liked : activeProfileTab === "collected" ? collected : works;
  els.profileWorksCount.textContent = `${works.length} 作品`;
  els.profileLikesCount.textContent = `${liked.length} 喜欢`;
  els.profileCollectsCount.textContent = `${collected.length} 收藏`;
  els.profileGrid.innerHTML = "";
  if (!source.length) {
    els.profileGrid.innerHTML = '<div class="empty-state">暂无内容。</div>';
    return;
  }
  for (const asset of source) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "asset-card profile-work-card";
    card.innerHTML = `
      <span>${escapeHtml(assetLabel(asset))}</span>
      <strong>${escapeHtml(asset.title || "未命名资产")}</strong>
      <small>${escapeHtml(truncate(normalizeCreativeText(asset.prompt || ""), 70))}</small>`;
    card.addEventListener("click", () => openAsset(asset.asset_id));
    els.profileGrid.appendChild(card);
  }
}

function renderAssetsPage() {
  const query = (els.assetSearch?.value || "").trim();
  const visibleAssets = assetsCache.filter((asset) => asset.source !== "inspiration" || asset.collected);
  const filteredAssets = visibleAssets.filter((asset) => {
    if (activeAssetFilter === "created") return asset.source !== "inspiration";
    if (activeAssetFilter === "collected") return asset.source === "inspiration" && asset.collected;
    return true;
  });
  const assets = filteredAssets.filter((asset) => !query || `${asset.title}${asset.prompt}${asset.final_content}${(asset.platforms || []).join("")}`.includes(query));
  els.assetGrid.innerHTML = "";
  if (!assets.length) {
    els.assetGrid.innerHTML = '<div class="empty-state">还没有可展示的资产。完成一次创作后，最终内容会自动进入这里。</div>';
    return;
  }
  for (const asset of assets) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "asset-card";
    card.innerHTML = `
      <span>${escapeHtml(assetLabel(asset))}</span>
      <strong>${escapeHtml(asset.title || "未命名资产")}</strong>
      <small>${escapeHtml(truncate(normalizeCreativeText(asset.prompt || ""), 76))}</small>
      <p>${escapeHtml(truncate(normalizeCreativeText(asset.final_content || "还没有最终内容。"), 120))}</p>`;
    card.addEventListener("click", () => openAsset(asset.asset_id));
    els.assetGrid.appendChild(card);
  }
}

function renderAssetDetail(asset) {
  if (!asset) return;
  els.assetDetailTitle.textContent = asset.title || "未命名资产";
  els.assetWorkType.textContent = assetLabel(asset);
  els.assetFinalContent.textContent = normalizeCreativeText(asset.final_content || "这条资产还没有最终内容。");
  els.assetPrompt.textContent = normalizeCreativeText(asset.prompt || "无");
  const meta = [];
  if (asset.updated_at) meta.push(asset.updated_at.slice(0, 10));
  if (asset.platforms?.length) meta.push(asset.platforms.join(" / "));
  if (asset.skills?.length) meta.push(asset.skills.join(" / "));
  els.assetMeta.textContent = meta.join("  |  ") || "内容创作资产";
}

function assetLabel(asset) {
  if (asset.platforms?.length) return asset.platforms.slice(0, 2).join(" / ");
  if (asset.goal) return asset.goal;
  return "内容资产";
}

function renderEvolution(manifest) {
  if (!els.evolutionList) return;
  els.evolutionList.innerHTML = "";
  const proposals = manifest?.proposals || [];
  if (!(currentSessionId || currentAsset?.session_id) || !proposals.length) {
    els.evolutionList.innerHTML = '<div class="published-item">这里会显示可审阅的工作规则改进。</div>';
    return;
  }
  for (const proposal of proposals.slice(0, 4)) {
    const card = document.createElement("article");
    card.className = "evolution-card";
    card.innerHTML = `
      <div class="evolution-target">${escapeHtml(proposal.target_component || "harness")}</div>
      <strong>${escapeHtml(proposal.targeted_fix || "收集更多证据后再调整。")}</strong>
      <small>${escapeHtml(proposal.expected_improvement || "")}</small>
      <button type="button" data-proposal-id="${escapeHtml(proposal.proposal_id)}">应用到工作规则</button>`;
    els.evolutionList.appendChild(card);
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" })[char]);
}

function openSkillMenu(anchor) {
  const rect = anchor.getBoundingClientRect();
  const willOpen = !els.skillMenu.classList.contains("open");
  if (!willOpen) return closeSkillMenu();
  els.skillMenu.classList.add("open");
  syncSkillMenuSelection();
  els.skillMenu.style.left = "12px";
  els.skillMenu.style.top = "12px";
  const width = els.skillMenu.offsetWidth || 520;
  const height = Math.min(els.skillMenu.scrollHeight, Math.floor(window.innerHeight * 0.72));
  const left = Math.max(12, Math.min(rect.left, window.innerWidth - width - 12));
  const preferredTop = rect.bottom + 8;
  const top = preferredTop + height > window.innerHeight - 12 ? Math.max(12, rect.top - height - 8) : preferredTop;
  els.skillMenu.style.left = `${left}px`;
  els.skillMenu.style.top = `${top}px`;
}

function closeSkillMenu() {
  els.skillMenu.classList.remove("open");
}

function syncSkillMenuSelection() {
  els.skillMenu.querySelectorAll("button[data-skill-id]").forEach((button) => {
    button.classList.toggle("selected", Boolean(selectedSkill && selectedSkill.id === button.dataset.skillId));
  });
}

function setSkillLabels(text = "使用技能") {
  els.selectedSkillLabel.textContent = text;
  els.inspirationSkillLabel.textContent = text;
  els.chatSkillLabel.textContent = text;
}

function selectSkill(skillId, name, prompt = "", input = activeComposerInput()) {
  if (selectedSkill?.id === skillId) {
    clearSelectedSkill({ input, removePrompt: true });
    closeSkillMenu();
    return;
  }
  selectedSkill = { id: skillId, name, prompt };
  setSkillLabels(name);
  applySkillPrompt(input, prompt);
  syncSkillMenuSelection();
  closeSkillMenu();
}

function clearSelectedSkill({ input = activeComposerInput(), removePrompt = false } = {}) {
  if (removePrompt) removeSkillPrompt(input);
  selectedSkill = null;
  setSkillLabels();
  syncSkillMenuSelection();
}

function activeComposerInput() {
  if (els.chatScreen.classList.contains("active")) return els.feedbackNote;
  if (els.generateScreen.classList.contains("active")) return els.request;
  return els.inspirationRequest;
}

function applySkillPrompt(input, prompt) {
  if (!prompt) return;
  const previous = input.dataset.skillPrompt || "";
  const value = input.value;
  if (!value || value === previous) {
    input.value = prompt;
  } else if (previous && input.value.includes(previous)) {
    input.value = input.value.replace(previous, prompt);
  } else if (previous && value.trim() === previous.trim()) {
    input.value = prompt;
  }
  input.dataset.skillPrompt = prompt;
}

function removeSkillPrompt(input) {
  if (!input) return;
  const previous = input.dataset.skillPrompt || selectedSkill?.prompt || "";
  if (previous && input.value.includes(previous)) {
    input.value = input.value.replace(previous, "").replace(/\n{3,}/g, "\n\n").trimStart();
  }
  input.dataset.skillPrompt = "";
}

function startNewChat() {
  stopPendingTyping();
  currentSessionId = null;
  currentManifest = null;
  currentAsset = null;
  currentPreviewItem = null;
  els.request.value = "";
  els.feedbackNote.value = "";
  els.request.dataset.skillPrompt = "";
  els.feedbackNote.dataset.skillPrompt = "";
  clearSelectedSkill({ removePrompt: false });
  renderLearning([], { completed: false });
  showScreen("generate");
  history.pushState({}, "", "/#generate");
  requestAnimationFrame(() => els.request.focus());
}

async function loadSettings() {
  const data = await api("/api/settings");
  Object.assign(providerDefaults, data.providers || {});
  const llm = data.llm || {};
  els.llmProvider.value = llm.provider || "";
  els.llmModel.value = llm.model || "";
  els.llmBaseUrl.value = llm.base_url || "";
  els.llmApiKey.placeholder = llm.has_api_key ? "已保存 key，留空不修改" : "输入 API key";
  const memory = data.memory_policy || {};
  els.memoryCandidateLimit.value = memory.candidate_limit ?? 3;
  els.memoryMinConfidence.value = memory.min_confidence ?? 0.35;
  els.memoryCompleteOnly.checked = memory.complete_only !== false;
  const profile = data.profile || {};
  els.profilePageNickname.value = profile.nickname || "创作者";
  els.profilePageBio.value = profile.bio || "";
  setAvatarPreview(profile.avatar_data || "");
  await loadPreferences();
}

function setSettingsSection(section, push = true) {
  const target = document.querySelector(`[data-settings-panel="${section || "model"}"]`);
  activeSettingsSection = target ? target.dataset.settingsPanel : "model";
  els.settingsNavItems.forEach((item) => item.classList.toggle("active", item.dataset.settingsSection === activeSettingsSection));
  els.settingsPanels.forEach((panel) => panel.classList.toggle("active", panel.dataset.settingsPanel === activeSettingsSection));
  if (push && els.settingsScreen.classList.contains("active")) history.pushState({}, "", `/settings/${activeSettingsSection}`);
}

async function loadPreferences() {
  if (!els.preferenceList) return;
  const data = await api("/api/preferences");
  renderPreferences(data.preferences || []);
}

function renderPreferences(preferences = []) {
  if (!els.preferenceList) return;
  els.preferenceList.innerHTML = "";
  if (!preferences.length) {
    els.preferenceList.innerHTML = '<div class="empty-row">还没有保存的偏好。</div>';
    return;
  }
  for (const preference of preferences) {
    const row = document.createElement("div");
    row.className = "preference-row";
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(normalizeCreativeText(preference.display_content || preference.content || ""))}</strong>
        <small>${escapeHtml((preference.tags || []).filter((item) => item !== "confirmed" && item !== "scope:global").slice(0, 2).join(" / ") || "偏好")}</small>
      </div>
      <button type="button" data-preference-id="${escapeHtml(preference.record_id)}">删除</button>`;
    els.preferenceList.appendChild(row);
  }
}

async function deletePreference(recordId) {
  if (!recordId) return;
  await api("/api/preferences/delete", { method: "POST", body: JSON.stringify({ record_id: recordId }) });
  await loadPreferences();
  showToast("偏好已删除");
}

function openDrawer(id) {
  document.querySelector(`#${id}`).classList.add("open");
}

function closeDrawer(id) {
  document.querySelector(`#${id}`).classList.remove("open");
}

async function saveSettings(event) {
  event.preventDefault();
  const data = await api("/api/settings", {
    method: "POST",
    body: JSON.stringify({ llm: { provider: els.llmProvider.value, model: els.llmModel.value, base_url: els.llmBaseUrl.value, api_key: els.llmApiKey.value } }),
  });
  els.llmApiKey.value = "";
  els.llmApiKey.placeholder = data.llm?.has_api_key ? "已保存 key，留空不修改" : "输入 API key";
  showToast("设置已保存");
}

async function saveMemoryPolicy(event) {
  event.preventDefault();
  await api("/api/settings", {
    method: "POST",
    body: JSON.stringify({
      memory_policy: {
        candidate_limit: Number(els.memoryCandidateLimit.value || 3),
        min_confidence: Number(els.memoryMinConfidence.value || 0.35),
        complete_only: els.memoryCompleteOnly.checked,
      },
    }),
  });
  showToast("记忆策略已保存");
}

async function saveProfile() {
  const nickname = els.profilePageNickname.value;
  const bio = els.profilePageBio.value;
  await api("/api/settings", { method: "POST", body: JSON.stringify({ profile: { nickname, bio } }) });
  els.profilePageNickname.value = nickname;
  els.profilePageBio.value = bio;
  showToast("个人资料已保存");
}

function setAvatarPreview(dataUrl) {
  if (!els.profileAvatarImage) return;
  if (dataUrl) {
    els.profileAvatarImage.src = dataUrl;
    els.profileAvatarBtn.classList.add("has-image");
  } else {
    els.profileAvatarImage.removeAttribute("src");
    els.profileAvatarBtn.classList.remove("has-image");
  }
}

function openAvatarPicker() {
  els.avatarFileInput.click();
}

function loadAvatarFile(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    const image = new Image();
    image.onload = () => {
      avatarState.image = image;
      resetAvatarTransform();
      els.avatarModal.classList.add("open");
      drawAvatar();
    };
    image.src = String(reader.result || "");
  };
  reader.readAsDataURL(file);
}

function resetAvatarTransform() {
  const canvas = els.avatarCanvas;
  const image = avatarState.image;
  if (!canvas || !image) return;
  avatarState.minScale = Math.max(canvas.width / image.width, canvas.height / image.height);
  avatarState.scale = avatarState.minScale;
  avatarState.offsetX = 0;
  avatarState.offsetY = 0;
  els.avatarZoom.min = String(avatarState.minScale);
  els.avatarZoom.max = String(Math.max(avatarState.minScale * 3, 3));
  els.avatarZoom.value = String(avatarState.scale);
}

function drawAvatar() {
  const canvas = els.avatarCanvas;
  if (!canvas || !avatarState.image) return;
  drawAvatarFrame(canvas, canvas.width, { showOverlay: true });
}

function drawAvatarFrame(canvas, size, { showOverlay = false } = {}) {
  const image = avatarState.image;
  const ctx = canvas.getContext("2d");
  const scaleRatio = size / els.avatarCanvas.width;
  const radius = size / 2;
  const imageWidth = image.width * avatarState.scale * scaleRatio;
  const imageHeight = image.height * avatarState.scale * scaleRatio;
  const centerX = size / 2 + avatarState.offsetX * scaleRatio;
  const centerY = size / 2 + avatarState.offsetY * scaleRatio;
  ctx.clearRect(0, 0, size, size);
  ctx.fillStyle = "#10131a";
  ctx.fillRect(0, 0, size, size);
  ctx.save();
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, radius, 0, Math.PI * 2);
  ctx.clip();
  ctx.drawImage(image, centerX - imageWidth / 2, centerY - imageHeight / 2, imageWidth, imageHeight);
  ctx.restore();
  if (showOverlay) {
    ctx.strokeStyle = "rgba(255,255,255,0.92)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, radius - 1, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function clampAvatarOffset() {
  const canvas = els.avatarCanvas;
  const image = avatarState.image;
  if (!canvas || !image) return;
  const width = image.width * avatarState.scale;
  const height = image.height * avatarState.scale;
  avatarState.offsetX = clamp(avatarState.offsetX, (canvas.width - width) / 2, (width - canvas.width) / 2);
  avatarState.offsetY = clamp(avatarState.offsetY, (canvas.height - height) / 2, (height - canvas.height) / 2);
}

function saveAvatar() {
  const canvas = els.avatarCanvas;
  const image = avatarState.image;
  if (!canvas || !image) return;
  const size = 512;
  const output = document.createElement("canvas");
  output.width = size;
  output.height = size;
  drawAvatarFrame(output, size);
  const dataUrl = output.toDataURL("image/png");
  setAvatarPreview(dataUrl);
  els.avatarModal.classList.remove("open");
  api("/api/settings", { method: "POST", body: JSON.stringify({ profile: { avatar_data: dataUrl } }) }).then(() => showToast("头像已保存")).catch((error) => showToast(error.message));
}

function avatarPoint(event) {
  const rect = els.avatarCanvas.getBoundingClientRect();
  const point = event.touches?.[0] || event;
  return { x: (point.clientX - rect.left) * (els.avatarCanvas.width / rect.width), y: (point.clientY - rect.top) * (els.avatarCanvas.height / rect.height) };
}

function clamp(value, min, max) {
  if (min > max) return 0;
  return Math.max(min, Math.min(max, value));
}

function setProviderDefaults() {
  const defaults = providerDefaults[els.llmProvider.value];
  if (!defaults) return;
  if (!els.llmModel.value.trim()) els.llmModel.value = defaults.model || "";
  if (!els.llmBaseUrl.value.trim()) els.llmBaseUrl.value = defaults.base_url || "";
}

async function createSessionFrom(textarea) {
  const request = textarea.value.trim();
  if (!request) {
    showToast("先写一点想法");
    textarea.focus();
    return;
  }
  setBusy(true, "正在创作");
  const activeSkill = selectedSkill;
  const preferences = activeSkill ? `使用技能：${activeSkill.id}` : "";
  const preview = await getWorkflowPreview(request, preferences);
  renderPendingChat(request, preview);
  try {
    const data = await api("/api/session", { method: "POST", body: JSON.stringify({ request, preferences, project_id: "default" }) });
    textarea.value = "";
    textarea.dataset.skillPrompt = "";
    clearSelectedSkill({ input: textarea, removePrompt: false });
    currentSessionId = data.state.session_id;
    await loadSessions();
    await loadAssets();
    await renderChat(data, { streamLastDraft: true });
    showScreen("chat", false);
    history.pushState({ sessionId: currentSessionId }, "", `/chat/${currentSessionId}`);
  } catch (error) {
    stopPendingTyping();
    appendMessage("assistant", `这次没有生成成功：${error.message}`, "EcRoom");
    showToast(error.message);
  } finally {
    setBusy(false);
  }
}

async function sendFeedback(event) {
  event.preventDefault();
  if (!currentSessionId) return showToast("先开启一个对话");
  const note = els.feedbackNote.value.trim();
  if (!note) return showToast("写一点反馈或补充要求");
  setBusy(true, "根据反馈生成");
  appendMessage("user", note, "反馈");
  const activeSkill = selectedSkill;
  const skillLine = activeSkill ? `使用技能：${activeSkill.id}\n` : "";
  const preview = await getWorkflowPreview(skillLine + note, skillLine);
  appendInlineTyping("正在继续打磨", preview);
  try {
    const data = await api(`/api/session/${currentSessionId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ signal: "edit", note: skillLine + note, edited_text: "" }),
    });
    els.feedbackNote.value = "";
    els.feedbackNote.dataset.skillPrompt = "";
    clearSelectedSkill({ input: els.feedbackNote, removePrompt: false });
    await loadSessions();
    await loadAssets();
    await renderChat(data, { streamLastDraft: true });
  } catch (error) {
    stopPendingTyping();
    appendMessage("assistant", `这次没有改稿成功：${error.message}`, "EcRoom");
    showToast(error.message);
  } finally {
    setBusy(false);
  }
}

async function togglePin(sessionId) {
  const session = sessionsCache.find((item) => item.session_id === sessionId);
  await api(`/api/session/${sessionId}`, { method: "PATCH", body: JSON.stringify({ pinned: !session?.pinned }) });
  await loadSessions();
}

function showRename(sessionId) {
  pendingRenameId = sessionId;
  const session = sessionsCache.find((item) => item.session_id === sessionId);
  els.renameInput.value = session?.title || "";
  els.renameModal.classList.add("open");
  els.renameInput.focus();
}

async function confirmRename() {
  const title = els.renameInput.value.trim();
  if (!pendingRenameId || !title) return;
  await api(`/api/session/${pendingRenameId}`, { method: "PATCH", body: JSON.stringify({ title }) });
  closeModal("renameModal");
  await loadSessions();
  if (pendingRenameId === currentSessionId) els.chatTitle.textContent = title;
  pendingRenameId = "";
}

async function editCurrentTitle() {
  if (!currentSessionId) return showToast("先打开一条对话");
  const current = els.chatTitle.textContent.trim();
  const title = window.prompt("修改对话标题", current);
  if (title === null) return;
  const nextTitle = title.trim();
  if (!nextTitle) return showToast("标题不能为空");
  await api(`/api/session/${currentSessionId}`, { method: "PATCH", body: JSON.stringify({ title: nextTitle }) });
  els.chatTitle.textContent = nextTitle;
  await loadSessions();
  showToast("标题已更新");
}

function showDelete(sessionId) {
  pendingDeleteId = sessionId;
  const defaultMode = document.querySelector('input[name="deleteMode"][value="history"]');
  if (defaultMode) defaultMode.checked = true;
  els.deleteModal.classList.add("open");
}

function showApplyEvolution(proposalId) {
  pendingEvolutionProposalId = proposalId;
  els.applyEvolutionNote.value = "";
  els.applyEvolutionModal.classList.add("open");
  els.applyEvolutionNote.focus();
}

async function confirmApplyEvolution() {
  const sessionId = currentSessionId || currentAsset?.session_id;
  if (!sessionId || !pendingEvolutionProposalId) return;
  const proposalId = pendingEvolutionProposalId;
  pendingEvolutionProposalId = "";
  setBusy(true, "应用改进");
  try {
    await api(`/api/session/${sessionId}/evolution/apply`, {
      method: "POST",
      body: JSON.stringify({ proposal_id: proposalId, reviewer_note: els.applyEvolutionNote.value }),
    });
    closeModal("applyEvolutionModal");
    showToast("改进已写入本地工作规则");
  } finally {
    setBusy(false);
  }
}

async function confirmDelete() {
  if (!pendingDeleteId) return;
  const mode = document.querySelector('input[name="deleteMode"]:checked')?.value || "revoke_memory";
  const result = await api(`/api/session/${pendingDeleteId}`, { method: "DELETE", body: JSON.stringify({ mode }) });
  const deletedCurrent = pendingDeleteId === currentSessionId;
  pendingDeleteId = "";
  closeModal("deleteModal");
  await loadSessions();
  await loadAssets();
  const revoked = Number(result.revoked_memory_count || 0);
  showToast(mode === "history" ? "已从历史移除，已保存偏好仍会保留" : `已删除，并清理 ${revoked} 条相关证据`);
  if (deletedCurrent) {
    currentSessionId = null;
    showScreen("generate");
  }
}

function closeModal(id) {
  document.querySelector(`#${id}`).classList.remove("open");
}

function bindEvents() {
  els.createForm.addEventListener("submit", (event) => { event.preventDefault(); createSessionFrom(els.request); });
  els.inspirationCreateForm.addEventListener("submit", (event) => { event.preventDefault(); createSessionFrom(els.inspirationRequest); });
  els.feedbackForm.addEventListener("submit", sendFeedback);
  els.newChatBtn.addEventListener("click", startNewChat);
  els.brandHomeBtn.addEventListener("click", () => showScreen("inspiration"));
  els.inspirationNavBtn.addEventListener("click", () => showScreen("inspiration"));
  els.generateNavBtn.addEventListener("click", () => showScreen("generate"));
  els.assetButton.addEventListener("click", () => openAssets());
  els.themeToggleBtn.addEventListener("click", toggleTheme);
  els.chatTitleEditBtn.addEventListener("click", editCurrentTitle);
  els.assetNewButton.addEventListener("click", () => showScreen("generate"));
  els.assetBackButton.addEventListener("click", () => openAssets());
  els.assetSearch.addEventListener("input", renderAssetsPage);
  els.assetFilterButtons.forEach((button) => button.addEventListener("click", () => {
    activeAssetFilter = button.dataset.assetFilter || "all";
    els.assetFilterButtons.forEach((item) => item.classList.toggle("active", item === button));
    renderAssetsPage();
  }));
  els.feedTabs.forEach((button) => button.addEventListener("click", () => {
    activeFeedCategory = button.dataset.category || "discover";
    els.feedTabs.forEach((item) => item.classList.toggle("active", item === button));
    renderInspirationGrid();
  }));
  els.remixAssetButton.addEventListener("click", () => {
    if (!currentAsset) return;
    els.request.value = currentAsset.prompt || "";
    showScreen("generate");
    history.pushState({}, "", "/#generate");
    els.request.focus();
  });
  els.openAssetSessionButton.addEventListener("click", () => {
    if (currentAsset?.session_id) openSession(currentAsset.session_id);
  });
  els.skillButton.addEventListener("click", () => openSkillMenu(els.skillButton));
  els.inspirationSkillButton.addEventListener("click", () => openSkillMenu(els.inspirationSkillButton));
  els.chatSkillButton.addEventListener("click", () => openSkillMenu(els.chatSkillButton));
  els.settingsBtn.addEventListener("click", () => openSettings());
  els.profileBtn.addEventListener("click", () => openProfile());
  els.settingsForm.addEventListener("submit", saveSettings);
  els.memoryPolicyForm.addEventListener("submit", saveMemoryPolicy);
  els.settingsNavItems.forEach((button) => button.addEventListener("click", () => setSettingsSection(button.dataset.settingsSection)));
  els.profilePageSaveBtn.addEventListener("click", saveProfile);
  els.profileAvatarBtn.addEventListener("click", openAvatarPicker);
  els.avatarFileInput.addEventListener("change", (event) => {
    loadAvatarFile(event.target.files?.[0]);
    event.target.value = "";
  });
  els.profileShareBtn.addEventListener("click", async () => {
    const url = `${location.origin}/profile`;
    try {
      await navigator.clipboard.writeText(url);
      showToast("主页链接已复制");
    } catch {
      showToast(url);
    }
  });
  els.cancelAvatarBtn.addEventListener("click", () => els.avatarModal.classList.remove("open"));
  els.chooseAvatarBtn.addEventListener("click", openAvatarPicker);
  els.saveAvatarBtn.addEventListener("click", saveAvatar);
  els.avatarZoom.addEventListener("input", () => {
    avatarState.scale = Number(els.avatarZoom.value);
    clampAvatarOffset();
    drawAvatar();
  });
  els.avatarCanvas.addEventListener("pointerdown", (event) => {
    avatarState.dragging = true;
    const point = avatarPoint(event);
    avatarState.lastX = point.x;
    avatarState.lastY = point.y;
    els.avatarCanvas.setPointerCapture(event.pointerId);
  });
  els.avatarCanvas.addEventListener("pointermove", (event) => {
    if (!avatarState.dragging) return;
    const point = avatarPoint(event);
    avatarState.offsetX += point.x - avatarState.lastX;
    avatarState.offsetY += point.y - avatarState.lastY;
    avatarState.lastX = point.x;
    avatarState.lastY = point.y;
    clampAvatarOffset();
    drawAvatar();
  });
  els.avatarCanvas.addEventListener("pointerup", () => { avatarState.dragging = false; });
  els.avatarCanvas.addEventListener("pointercancel", () => { avatarState.dragging = false; });
  els.profileTabs.forEach((button) => button.addEventListener("click", () => {
    activeProfileTab = button.dataset.profileTab || "published";
    els.profileTabs.forEach((item) => item.classList.toggle("active", item === button));
    renderProfile();
  }));
  els.llmProvider.addEventListener("change", setProviderDefaults);
  els.feedSearch.addEventListener("input", renderInspirationGrid);
  els.collapseSidebarBtn.addEventListener("click", () => els.appFrame.classList.add("history-collapsed"));
  els.expandSidebarBtn.addEventListener("click", () => els.appFrame.classList.remove("history-collapsed"));
  els.testLlmBtn.addEventListener("click", async () => {
    const result = await api("/api/llm/test", { method: "POST", body: "{}" });
    showToast(result.ok ? `${result.provider} 连接成功` : result.message);
  });
  els.learningToggleBtn.addEventListener("click", toggleLearningPanel);
  els.learningList.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-learning-id]");
    if (!button) return;
    setBusy(true, "更新偏好");
    try {
      await applyLearningItem(button.dataset.learningId, button.dataset.learningAction);
    } catch (error) {
      showToast(error.message);
    } finally {
      setBusy(false);
    }
  });
  els.messageList.addEventListener("click", async (event) => {
    if (event.target.closest(".draft-complete-button")) await toggleSessionCompleted();
  });
  els.refreshPreferencesBtn.addEventListener("click", loadPreferences);
  els.preferenceList.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-preference-id]");
    if (button) await deletePreference(button.dataset.preferenceId);
  });
  document.querySelectorAll(".close-drawer").forEach((button) => button.addEventListener("click", () => closeDrawer(button.dataset.close)));
  els.skillMenu.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-skill-id]");
    if (!button) return;
    const activeInput = activeComposerInput();
    selectSkill(button.dataset.skillId, button.dataset.skill, button.dataset.prompt || "", activeInput);
    activeInput.focus();
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest("#skillMenu") && !event.target.closest(".tool-button")) closeSkillMenu();
    if (!event.target.closest(".session-row")) document.querySelectorAll(".session-menu.open").forEach((menu) => menu.classList.remove("open"));
  });
  els.sessionList.addEventListener("click", async (event) => {
    const row = event.target.closest(".session-row");
    if (!row) return;
    const sessionId = row.dataset.sessionId;
    const actionButton = event.target.closest("[data-action]");
    if (event.target.closest(".session-menu-button")) {
      event.stopPropagation();
      const menu = row.querySelector(".session-menu");
      document.querySelectorAll(".session-menu.open").forEach((item) => { if (item !== menu) item.classList.remove("open"); });
      menu.classList.toggle("open");
      return;
    }
    if (actionButton) {
      event.stopPropagation();
      if (actionButton.dataset.action === "pin") await togglePin(sessionId);
      if (actionButton.dataset.action === "rename") showRename(sessionId);
      if (actionButton.dataset.action === "delete") showDelete(sessionId);
      return;
    }
    openSession(sessionId);
  });
  els.cancelRenameBtn.addEventListener("click", () => closeModal("renameModal"));
  els.confirmRenameBtn.addEventListener("click", confirmRename);
  els.cancelDeleteBtn.addEventListener("click", () => closeModal("deleteModal"));
  els.confirmDeleteBtn.addEventListener("click", confirmDelete);
  els.cancelApplyEvolutionBtn.addEventListener("click", () => closeModal("applyEvolutionModal"));
  els.confirmApplyEvolutionBtn.addEventListener("click", confirmApplyEvolution);
  if (els.evolutionList) {
    els.evolutionList.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-proposal-id]");
      if (button) showApplyEvolution(button.dataset.proposalId);
    });
  }
  els.closePreviewBtn.addEventListener("click", closePreview);
  els.likePreviewBtn.addEventListener("click", likePreview);
  els.collectPreviewBtn.addEventListener("click", collectPreview);
  els.applyPreviewBtn.addEventListener("click", applyPreview);
  els.previewModal.addEventListener("click", (event) => {
    if (event.target === els.previewModal) closePreview();
  });
  window.addEventListener("popstate", () => bootFromRoute(false));
}

async function bootFromRoute(push = false) {
  const assetMatch = location.pathname.match(/^\/asset\/([^/]+)$/);
  if (assetMatch) return openAsset(assetMatch[1], push);
  const match = location.pathname.match(/^\/chat\/([^/]+)$/);
  if (match) return openSession(match[1], push);
  if (location.pathname === "/assets") return openAssets(push);
  if (location.pathname === "/profile") return openProfile(push);
  const settingsMatch = location.pathname.match(/^\/settings\/?([^/]*)$/);
  if (settingsMatch) return openSettings(settingsMatch[1] || "model", push);
  showScreen(location.hash === "#generate" ? "generate" : "inspiration", push);
}

async function boot() {
  bindEvents();
  try {
    await loadSettings();
    await loadSessions();
    await loadAssets();
    await bootFromRoute(false);
  } catch (error) {
    showToast(error.message);
  }
}

boot();
