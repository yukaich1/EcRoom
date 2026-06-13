let currentSessionId = null;
let selectedSkill = null;
let pendingRenameId = "";
let pendingDeleteId = "";
let pendingReviewItemId = "";
let sessionsCache = [];
let assetsCache = [];
let postsCache = [];
let currentManifest = null;
let currentSessionCompleted = false;
let currentAsset = null;
let currentPublishPost = null;
let publishTags = [];
let publishDefaultTags = [];
let publishCoverDataUrl = "";
let currentPreviewItem = null;
let currentPreviewMode = "inspiration";
let currentProfile = { nickname: "创作者", bio: "", avatar_data: "" };
let activeFeedCategory = "discover";
let inspirationRotation = 0;
let inspirationWheelLock = 0;
let inspirationVisibleItems = [];
let inspirationBatchIndex = 0;
let inspirationRenderedKey = "";
let activeProfileTab = "published";
let activeAssetFilter = "all";
let activeSettingsSection = "model";
let currentScreenName = "inspiration";
let pendingTypingTimer = null;
let pendingWorkflowStartedAt = 0;
let pullRefreshState = { dragging: false, startY: 0, offset: 0, pointerId: null };
let sessionReviewQueue = [];
let sessionReviewIndex = 0;
let avatarState = { image: null, offsetX: 0, offsetY: 0, scale: 1, minScale: 1, dragging: false, lastX: 0, lastY: 0 };
let previousAssetScreen = "assets";
let previousPublishScreen = "chat";

const els = {
  appFrame: document.querySelector("#appFrame"),
  bootScreen: document.querySelector("#bootScreen"),
  bootMark: document.querySelector("#bootMark"),
  inspirationScreen: document.querySelector("#inspirationScreen"),
  generateScreen: document.querySelector("#generateScreen"),
  chatScreen: document.querySelector("#chatScreen"),
  assetsScreen: document.querySelector("#assetsScreen"),
  assetDetailScreen: document.querySelector("#assetDetailScreen"),
  publishScreen: document.querySelector("#publishScreen"),
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
  selectedSkillLabel: document.querySelector("#selectedSkillLabel"),
  inspirationSkillLabel: document.querySelector("#inspirationSkillLabel"),
  skillMenu: document.querySelector("#skillMenu"),
  feedTabs: document.querySelectorAll(".feed-tab"),
  inspirationGrid: document.querySelector("#inspirationGrid"),
  feedSearch: document.querySelector("#feedSearch"),
  refreshFeedBtn: document.querySelector("#refreshFeedBtn"),
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
  assetAuthorName: document.querySelector("#assetAuthorName"),
  assetAuthorAvatar: document.querySelector("#assetAuthorAvatar"),
  remixAssetButton: document.querySelector("#remixAssetButton"),
  openAssetSessionButton: document.querySelector("#openAssetSessionButton"),
  publishBackBtn: document.querySelector("#publishBackBtn"),
  publishTitle: document.querySelector("#publishTitle"),
  publishBody: document.querySelector("#publishBody"),
  publishTagChoices: document.querySelector("#publishTagChoices"),
  publishTagInput: document.querySelector("#publishTagInput"),
  publishTagList: document.querySelector("#publishTagList"),
  publishCoverBtn: document.querySelector("#publishCoverBtn"),
  publishCoverInput: document.querySelector("#publishCoverInput"),
  publishCoverImage: document.querySelector("#publishCoverImage"),
  publishCoverPlaceholder: document.querySelector("#publishCoverPlaceholder"),
  publishPreviewCover: document.querySelector("#publishPreviewCover"),
  publishPreviewTitle: document.querySelector("#publishPreviewTitle"),
  publishPreviewBody: document.querySelector("#publishPreviewBody"),
  publishPreviewTags: document.querySelector("#publishPreviewTags"),
  publishPreviewAuthorName: document.querySelector("#publishPreviewAuthorName"),
  publishPreviewAuthorAvatar: document.querySelector("#publishPreviewAuthorAvatar"),
  publishDeleteBtn: document.querySelector("#publishDeleteBtn"),
  publishSaveDraftBtn: document.querySelector("#publishSaveDraftBtn"),
  publishSubmitBtn: document.querySelector("#publishSubmitBtn"),
  chatTitle: document.querySelector("#chatTitle"),
  chatUpdatedAt: document.querySelector("#chatUpdatedAt"),
  chatTitleEditBtn: document.querySelector("#chatTitleEditBtn"),
  themeToggleBtn: document.querySelector("#themeToggleBtn"),
  messageList: document.querySelector("#messageList"),
  feedbackForm: document.querySelector("#feedbackForm"),
  feedbackNote: document.querySelector("#feedbackNote"),
  settingsBtn: document.querySelector("#settingsBtn"),
  settingsModal: document.querySelector("#settingsModal"),
  historyManageModal: document.querySelector("#historyManageModal"),
  historyManageList: document.querySelector("#historyManageList"),
  closeHistoryManageBtn: document.querySelector("#closeHistoryManageBtn"),
  closeSettingsBtn: document.querySelector("#closeSettingsBtn"),
  profileBtn: document.querySelector("#profileBtn"),
  settingsForm: document.querySelector("#settingsForm"),
  memoryPolicyForm: document.querySelector("#memoryPolicyForm"),
  harnessSettingsForm: document.querySelector("#harnessSettingsForm"),
  settingsNavItems: document.querySelectorAll(".settings-nav-item"),
  settingsPanels: document.querySelectorAll(".settings-panel"),
  llmProvider: document.querySelector("#llmProvider"),
  llmModel: document.querySelector("#llmModel"),
  llmBaseUrl: document.querySelector("#llmBaseUrl"),
  llmApiKey: document.querySelector("#llmApiKey"),
  modelRuntimeStatus: document.querySelector("#modelRuntimeStatus"),
  testLlmBtn: document.querySelector("#testLlmBtn"),
  preferenceList: document.querySelector("#preferenceList"),
  refreshPreferencesBtn: document.querySelector("#refreshPreferencesBtn"),
  learnedList: document.querySelector("#learnedList"),
  refreshLearnedBtn: document.querySelector("#refreshLearnedBtn"),
  memoryCandidateLimit: document.querySelector("#memoryCandidateLimit"),
  memoryMinConfidence: document.querySelector("#memoryMinConfidence"),
  memoryCompleteOnly: document.querySelector("#memoryCompleteOnly"),
  dataDoctorStatus: document.querySelector("#dataDoctorStatus"),
  runDataDoctorBtn: document.querySelector("#runDataDoctorBtn"),
  rebuildIndexBtn: document.querySelector("#rebuildIndexBtn"),
  harnessAutoPropose: document.querySelector("#harnessAutoPropose"),
  harnessRecordSkillRuns: document.querySelector("#harnessRecordSkillRuns"),
  harnessMinEvalCases: document.querySelector("#harnessMinEvalCases"),
  profilePageNickname: document.querySelector("#profilePageNickname"),
  profilePageBio: document.querySelector("#profilePageBio"),
  profileAvatarDisplay: document.querySelector("#profileAvatarDisplay"),
  profileEditBtn: document.querySelector("#profileEditBtn"),
  profileEditModal: document.querySelector("#profileEditModal"),
  profileEditNickname: document.querySelector("#profileEditNickname"),
  profileEditBio: document.querySelector("#profileEditBio"),
  cancelProfileEditBtn: document.querySelector("#cancelProfileEditBtn"),
  cancelProfileEditTextBtn: document.querySelector("#cancelProfileEditTextBtn"),
  profilePageSaveBtn: document.querySelector("#profilePageSaveBtn"),
  profileAvatarBtn: document.querySelector("#profileAvatarBtn"),
  profileAvatarImage: document.querySelector("#profileAvatarImage"),
  profileEditAvatarImage: document.querySelector("#profileEditAvatarImage"),
  avatarFileInput: document.querySelector("#avatarFileInput"),
  profileShareBtn: document.querySelector("#profileShareBtn"),
  profileWorksCount: document.querySelector("#profileWorksCount"),
  profileLikesCount: document.querySelector("#profileLikesCount"),
  profileCollectsCount: document.querySelector("#profileCollectsCount"),
  profileTabs: document.querySelectorAll(".profile-tab"),
  profileGrid: document.querySelector("#profileGrid"),
  evolutionList: document.querySelector("#evolutionList"),
  evolutionReviewBtn: document.querySelector("#evolutionReviewBtn"),
  evolutionReviewCount: document.querySelector("#evolutionReviewCount"),
  evolutionReviewCounter: document.querySelector("#evolutionReviewCounter"),
  evolutionReviewTitle: document.querySelector("#evolutionReviewTitle"),
  evolutionReviewBody: document.querySelector("#evolutionReviewBody"),
  evolutionReviewScope: document.querySelector("#evolutionReviewScope"),
  evolutionReviewImpact: document.querySelector("#evolutionReviewImpact"),
  evolutionReviewTech: document.querySelector("#evolutionReviewTech"),
  ignoreEvolutionBtn: document.querySelector("#ignoreEvolutionBtn"),
  renameModal: document.querySelector("#renameModal"),
  renameInput: document.querySelector("#renameInput"),
  cancelRenameBtn: document.querySelector("#cancelRenameBtn"),
  confirmRenameBtn: document.querySelector("#confirmRenameBtn"),
  deleteModal: document.querySelector("#deleteModal"),
  cancelDeleteBtn: document.querySelector("#cancelDeleteBtn"),
  confirmDeleteBtn: document.querySelector("#confirmDeleteBtn"),
  applyEvolutionModal: document.querySelector("#applyEvolutionModal"),
  cancelApplyEvolutionBtn: document.querySelector("#cancelApplyEvolutionBtn"),
  confirmApplyEvolutionBtn: document.querySelector("#confirmApplyEvolutionBtn"),
  publishPromptModal: document.querySelector("#publishPromptModal"),
  goPublishBtn: document.querySelector("#goPublishBtn"),
  saveWorkOnlyBtn: document.querySelector("#saveWorkOnlyBtn"),
  continueWorkBtn: document.querySelector("#continueWorkBtn"),
  reopenWorkModal: document.querySelector("#reopenWorkModal"),
  reopenAndClearLearningBtn: document.querySelector("#reopenAndClearLearningBtn"),
  reopenKeepLearningBtn: document.querySelector("#reopenKeepLearningBtn"),
  cancelReopenWorkBtn: document.querySelector("#cancelReopenWorkBtn"),
  avatarModal: document.querySelector("#avatarModal"),
  avatarCanvas: document.querySelector("#avatarCanvas"),
  avatarZoom: document.querySelector("#avatarZoom"),
  cancelAvatarBtn: document.querySelector("#cancelAvatarBtn"),
  chooseAvatarBtn: document.querySelector("#chooseAvatarBtn"),
  saveAvatarBtn: document.querySelector("#saveAvatarBtn"),
  previewModal: document.querySelector("#previewModal"),
  closePreviewBtn: document.querySelector("#closePreviewBtn"),
  previewType: document.querySelector("#previewType"),
  previewImage: document.querySelector("#previewImage"),
  previewTitle: document.querySelector("#previewTitle"),
  previewAuthorName: document.querySelector("#previewAuthorName"),
  previewAuthorAvatar: document.querySelector("#previewAuthorAvatar"),
  previewPromptSection: document.querySelector("#previewPromptSection"),
  previewPromptLabel: document.querySelector("#previewPromptLabel"),
  previewPrompt: document.querySelector("#previewPrompt"),
  previewOutputLabel: document.querySelector("#previewOutputLabel"),
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
  { id: "seed_character_cold", category: "story", title: "冷面新角色登场", type: "故事设定", image: "/assets/inspiration/character.jpg", prompt: "写一个冷感新角色登场文案，适合后续改成微博宣发。要求：角色有压迫感，但不要中二；正文保留一个可继续扩展的世界观暗线。", final_content: "他走进来时，房间里先安静了一秒。\n\n没人知道他的名字，只看见那枚旧徽章被放在桌面中央。它来自早已消失的北境军团，也来自一场没人愿意再提起的失败。\n\n这不是英雄登场，更像一段旧账终于找到了债主。", tone: "cyan", skills: ["narrative_canon"], platforms: ["微博"] },
  { id: "seed_xhs_campaign", category: "post", title: "体验笔记", type: "帖子", image: "/assets/inspiration/campaign.jpg", prompt: "把游戏版本活动包装成小红书体验笔记，不要太硬广。需要包含：一句自然标题、体验感开头、三个玩家会在意的亮点，以及避免夸张承诺的表达。", final_content: "标题：这个版本最打动我的，反而是那些很小的细节\n\n本来只是想上线看看新活动，结果被几个不太起眼的地方留住了。比如任务节奏没有催着你跑，角色对话里也藏了不少后续伏笔。它不是那种一眼很炸的更新，但玩下来会觉得世界真的往前走了一点。", tone: "amber", skills: ["publish_ready"], platforms: ["小红书"] },
  { id: "seed_tide_city", category: "story", title: "潮汐钟城市", type: "故事设定", image: "/assets/inspiration/city.jpg", prompt: "写一段被潮汐钟控制的城市设定，带一点阴谋感。请输出：城市简介、核心冲突、三个可继续扩写的剧情钩子。", final_content: "这座城市每天只准在潮汐钟响起后醒来。\n\n钟声决定开市、审判、婚礼和葬礼，也决定一个人是否还能拥有明天。没人知道钟是谁造的，只知道每当它慢一拍，城里就会少掉一条街。\n\n剧情钩子：\n1. 守钟人发现自己的名字从城市档案里消失。\n2. 叛逃的修表师声称潮汐并不存在。\n3. 主角听见钟声里传来未来自己的求救。", tone: "violet", skills: ["narrative_canon"], platforms: [] },
  { id: "seed_polish_human", category: "post", title: "去掉 AI 味", type: "帖子改稿", image: "/assets/inspiration/writing.jpg", prompt: "请把一段明显像 AI 的文案改得更像真人写作。保留核心信息，减少套路连接词，让语气更具体、更自然。", final_content: "改法不是简单把句子写短，而是先删掉那些看起来很正确、但没人真的会这么说的话。保留信息点，再把它们放回一个具体场景里。读起来像有人真的经历过，这篇稿子才会站得住。", tone: "green", skills: ["revision_studio"], platforms: [] },
  { id: "seed_release_titles", category: "post", title: "发布节奏三连", type: "帖子", image: "/assets/inspiration/release.jpg", prompt: "给我一组预热、上线当天、反馈转发的微博文案。要求每条都短，避免模板化感叹句，保留一点故事感。", final_content: "预热：有些门不是被打开的，是终于撑不住了。\n\n上线当天：新版本已开。先别急着做任务，去听听城门口那段对话。\n\n反馈转发：看到有人猜到了徽章的来历。只能说，你们离真相很近，也很危险。", tone: "red", skills: ["variant_lab"], platforms: ["微博"] },
  { id: "seed_norm_boundary", category: "knowledge", title: "平台规范边界", type: "知识整理", image: "/assets/inspiration/norm.jpg", prompt: "生成内容时自动检查小红书和微博的表达边界。请给出一版发布前检查清单，并写一段更稳妥的活动说明。", final_content: "发布前先看四件事：有没有夸张承诺，是否像硬广，是否暗示未证实效果，是否把平台规则写进正文里。\n\n稳妥版本：这次活动更适合慢慢体验。它的重点不是奖励堆得多，而是把角色关系和地图细节往前推了一步。感兴趣的话，可以从支线任务开始看。", tone: "blue", skills: ["source_grounded"], platforms: ["小红书", "微博"] },
  { id: "seed_dialogue_spark", category: "story", title: "一句台词定人设", type: "故事设定", image: "/assets/inspiration/character.jpg", prompt: "围绕一个新角色写三句台词，每句都要暴露不同层面的性格：表面态度、隐藏动机、与主线的关系。", final_content: "1. “我不是来帮你的，我只是讨厌有人把局面弄得这么难看。”\n2. “名字可以换，旧账不会。”\n3. “你以为门后是答案，其实只是另一个人替你选好的问题。”", tone: "cyan", skills: ["narrative_canon"], platforms: [] },
  { id: "seed_world_faction", category: "story", title: "阵营冲突卡", type: "故事设定", image: "/assets/inspiration/city.jpg", prompt: "设计两个互相误解但都不完全错误的阵营，输出各自信念、冲突来源和一个可写成剧情的公共事件。", final_content: "旧钟会相信秩序来自稳定，哪怕稳定需要牺牲一部分真相。新潮派相信自由必须打破旧制度，哪怕打破之后没人知道明天怎么过。\n\n公共事件：一场停钟事故让两派第一次发现，自己守护的东西可能来自同一个谎言。", tone: "violet", skills: ["narrative_canon"], platforms: [] },
  { id: "seed_brand_soft_launch", category: "post", title: "新品软启动", type: "帖子", image: "/assets/inspiration/campaign.jpg", prompt: "帮我把一个功能更新写成不硬广的新品软启动文案，适合公众号和小红书都能继续改。", final_content: "这次更新没有把所有变化都摆在第一眼。\n\n我们更想让你在使用过程中慢慢发现：有些步骤少了，有些选择更清楚了，有些原本需要绕路的地方终于顺了。它不是一次吵闹的发布，更像把桌面重新整理了一遍。", tone: "amber", skills: ["publish_ready"], platforms: ["小红书", "公众号"] },
  { id: "seed_title_variants", category: "post", title: "标题五连发", type: "帖子", image: "/assets/inspiration/release.jpg", prompt: "同一篇内容给我五个标题方向：冷感、生活化、悬念、观点、平台友好。不要使用夸张标点。", final_content: "冷感：那座城市终于慢了一拍\n生活化：我在一个会按钟声醒来的城市里住了一天\n悬念：钟停之后，第一条消失的是街道\n观点：好的设定，不一定要先解释世界\n平台友好：这个城市设定有点适合写成长篇", tone: "red", skills: ["variant_lab"], platforms: [] },
  { id: "seed_revision_before_after", category: "post", title: "改稿前后对照", type: "帖子改稿", image: "/assets/inspiration/writing.jpg", prompt: "把一段模板感很强的内容做前后对照式改稿，保留核心信息，但让读者感觉更像真人表达。", final_content: "原句的问题不是信息错，而是每个词都太用力。\n\n改稿时先删掉“重磅、全面、极致”这类空泛词，再把变化放进一个可感知的动作里。比如不要说体验全面升级，可以说：这次打开页面时，最先感觉到的是少等了两秒。", tone: "green", skills: ["revision_studio"], platforms: [] },
  { id: "seed_event_brief", category: "professional", title: "活动页 brief", type: "职业文本", image: "/assets/inspiration/norm.jpg", prompt: "把一个活动想法整理成活动页 brief，包含目标用户、主卖点、内容结构和需要避免的表达风险。", final_content: "目标用户：已经了解产品，但还没有形成稳定使用习惯的人。\n主卖点：这次活动不是送福利，而是让用户用一个轻任务体验完整流程。\n结构：场景问题、活动机制、参与方式、结果展示、风险提示。\n避免：过度承诺、暗示收益、制造焦虑。", tone: "blue", skills: ["creative_brief"], platforms: [] },
  { id: "seed_scene_hook", category: "story", title: "场景钩子", type: "故事设定", image: "/assets/inspiration/city.jpg", prompt: "写三个可以接入游戏主线的场景钩子，每个都要有地点、异常和角色选择。", final_content: "1. 地点：废弃观测塔。异常：每到整点，塔顶会亮起不存在的星图。选择：上报，还是独自解读。\n2. 地点：地下车站。异常：末班车总会多停一站。选择：跟上去，还是拦住别人。\n3. 地点：旧档案室。异常：新档案比旧档案更先发黄。选择：相信记录，还是相信记忆。", tone: "violet", skills: ["narrative_canon"], platforms: [] },
  { id: "seed_platform_dual", category: "post", title: "双平台改写", type: "帖子", image: "/assets/inspiration/campaign.jpg", prompt: "同一个内容核心，分别改成微博和小红书两版。微博更短，小红书更像体验笔记，同时提醒表达差异。", final_content: "微博版：新版本今天开。建议先去城门口听一段对话，再决定从哪条支线开始。\n\n小红书版：这次更新我最喜欢的不是奖励，而是几个很细的场景变化。尤其是城门口那段对话，像是悄悄把后面的剧情先透了一点影子。", tone: "amber", skills: ["publish_ready"], platforms: ["微博", "小红书"] },
  { id: "seed_video_script", category: "video", title: "短视频分镜脚本", type: "视频脚本", image: "/assets/inspiration/release.jpg", prompt: "把一个产品功能写成 45 秒短视频脚本，包含开场钩子、镜头段落、旁白、屏幕字幕和结尾行动。既能给真人拍摄，也能给 AI 视频工具继续拆分。", final_content: "0-3 秒：画面从杂乱桌面切到干净的创作界面。字幕：想法太多，写不成稿？\n4-18 秒：快速展示输入需求、整理结构、生成第一版。旁白：先别急着追求完美，把方向、素材和约束放进同一个房间。\n19-35 秒：切到改稿对话和版本对比。旁白：真正有用的是后续修改，它会记住你确认过的偏好。\n36-45 秒：作品卡片落到主页。字幕：把想法打磨成可发布的作品。", tone: "red", skills: ["video_script"], platforms: ["视频"] },
  { id: "seed_longform_outline", category: "longform", title: "长文结构搭建", type: "长文", image: "/assets/inspiration/writing.jpg", prompt: "把一个松散观点写成长文提纲，包含论点、段落顺序、例子位置和收束方式。", final_content: "标题方向：为什么创作工具不该只追求一次生成\n\n结构：先写用户卡住的瞬间，再解释草稿、反馈、协作复盘之间的关系。中段用一个真实改稿场景展示“越聊越贴合”的过程。结尾收束到观点：好的创作系统不是替用户决定，而是让用户更容易表达自己的判断。", tone: "green", skills: ["longform_builder"], platforms: [] },
  { id: "seed_knowledge_explain", category: "knowledge", title: "资料变成解释稿", type: "知识整理", image: "/assets/inspiration/norm.jpg", prompt: "把一组资料整理成普通读者看得懂的解释稿，保留事实边界，不把推测写成结论。", final_content: "写法可以分三层：先说这件事是什么，再说目前能确认什么，最后说哪些部分还只是推测。不要急着给观点，先把读者需要判断的信息摆清楚。", tone: "blue", skills: ["knowledge_grounded"], platforms: [] },
  { id: "seed_professional_update", category: "professional", title: "项目进展同步", type: "职业文本", image: "/assets/inspiration/campaign.jpg", prompt: "写一段项目进展同步，适合发给合作方。语气礼貌、明确，不绕弯。", final_content: "本周我们完成了首页信息架构和创作完成后的系统自检流程调整。下一步会集中验证历史管理、作品状态和会话隔离逻辑。需要你确认的部分只有两项：是否保留当前首页视觉方向，以及删除模式的文案是否足够清楚。", tone: "amber", skills: ["professional_writer"], platforms: [] },
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
  memory_curator: "上下文整理",
  context_builder: "上下文召回",
  canon_keeper: "设定",
};

initTheme();
initBootScreen();

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

function initBootScreen() {
  if (!els.bootScreen) return;
  const startedAt = performance.now();
  const visibleDuration = 2850;
  let progress = 0;
  const finish = () => {
    updateBootProgress(100);
    window.setTimeout(() => {
      els.bootScreen.classList.add("signal-lock");
      window.setTimeout(() => {
        els.bootScreen?.classList.add("reveal");
        els.appFrame?.classList.add("app-revealed");
        window.setTimeout(() => els.bootScreen?.remove(), 1480);
      }, 360);
    }, 120);
  };
  const timer = window.setInterval(() => {
    const elapsed = performance.now() - startedAt;
    const t = Math.min(elapsed / visibleDuration, 1);
    progress = t >= 1 ? 100 : Math.min(99, Math.floor((1 - Math.pow(1 - t, 2.4)) * 100));
    updateBootProgress(progress);
    if (progress >= 100) {
      window.clearInterval(timer);
      finish();
    }
  }, 70);
  window.setTimeout(() => {
    if (progress < 100) {
      window.clearInterval(timer);
      finish();
    }
  }, visibleDuration + 180);
}

function updateBootProgress(value) {
  const pct = `${Math.round(value)}%`;
  els.bootMark?.style.setProperty("--boot-progress", pct);
  els.bootScreen?.style.setProperty("--boot-progress", pct);
}

function brandMarkMarkup(className = "") {
  return `
    <span class="brand-loader ${className}" aria-hidden="true">
      <img src="/assets/ecroom-dania-character.webp" alt="" />
    </span>`;
}

function toggleTheme() {
  const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("ecroom-theme", next);
  showToast(next === "light" ? "已切换到白天" : "已切换到黑夜");
}

function setBusy(isBusy) {
  document.body.classList.toggle("is-busy", isBusy);
}

function showScreen(name, push = true) {
  const previousScreen = currentScreenName;
  currentSessionId = name === "chat" || name === "publish" ? currentSessionId : null;
  if (name !== "assetDetail") currentAsset = null;
  for (const screen of [els.inspirationScreen, els.generateScreen, els.chatScreen, els.assetsScreen, els.assetDetailScreen, els.publishScreen, els.profileScreen, els.settingsScreen]) {
    screen.classList.remove("active", "screen-enter");
  }
  const target = name === "generate" ? els.generateScreen : name === "chat" ? els.chatScreen : name === "assets" ? els.assetsScreen : name === "assetDetail" ? els.assetDetailScreen : name === "publish" ? els.publishScreen : name === "profile" ? els.profileScreen : name === "settings" ? els.settingsScreen : els.inspirationScreen;
  target.classList.add("active");
  target.dataset.motion = motionDirection(previousScreen, name);
  window.requestAnimationFrame(() => target.classList.add("screen-enter"));
  window.setTimeout(() => target.classList.remove("screen-enter"), 620);
  document.body.dataset.screen = name;
  currentScreenName = name;
  els.inspirationNavBtn.classList.toggle("active", name === "inspiration");
  els.generateNavBtn.classList.toggle("active", name === "generate" || name === "chat");
  els.assetButton.classList.toggle("active", name === "assets" || name === "assetDetail");
  els.profileBtn.classList.toggle("active", name === "profile" || name === "publish");
  els.settingsBtn.classList.toggle("active", name === "settings");
  const historyVisible = name === "generate" || name === "chat";
  els.appFrame.classList.toggle("history-hidden", !historyVisible);
  updateSessionReviewButton();
  if (push) {
    const path = name === "generate" ? "/#generate" : name === "assets" ? "/assets" : name === "profile" ? "/profile" : name === "settings" ? `/settings/${activeSettingsSection}` : name === "publish" && currentPublishPost ? `/publish/${currentPublishPost.post_id}` : "/";
    history.pushState({}, "", path);
  }
}

function motionDirection(previous, next) {
  const order = ["inspiration", "generate", "chat", "assets", "assetDetail", "publish", "profile", "settings"];
  if (next === "assetDetail" || next === "publish") return "depth";
  if (previous === "assetDetail" && next === "assets") return "back";
  return order.indexOf(next) >= order.indexOf(previous) ? "forward" : "back";
}

function pulseElement(element, className = "motion-pulse", duration = 520) {
  if (!element) return;
  element.classList.remove(className);
  void element.offsetWidth;
  element.classList.add(className);
  window.setTimeout(() => element.classList.remove(className), duration);
}

async function openSession(sessionId, push = true) {
  clearSelectedSkill({ removePrompt: false });
  setBusy(true);
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
  await loadPosts();
  renderProfile();
  showScreen("profile", false);
  if (push) history.pushState({}, "", "/profile");
}

async function openSettings(section = activeSettingsSection, push = true) {
  await loadSettings();
  const requestedSection = section || "model";
  setSettingsSection(requestedSection, false);
  els.settingsModal.classList.add("open");
  els.settingsModal.setAttribute("aria-hidden", "false");
  if (push) history.pushState({}, "", `/settings/${activeSettingsSection}`);
  else if (location.pathname.startsWith("/settings") && requestedSection !== activeSettingsSection) history.replaceState({}, "", `/settings/${activeSettingsSection}`);
}

function closeSettingsModal() {
  els.settingsModal.classList.remove("open");
  els.settingsModal.setAttribute("aria-hidden", "true");
  if (location.pathname.startsWith("/settings")) history.pushState({}, "", currentSessionId ? `/chat/${currentSessionId}` : "/");
}

async function openAsset(assetId, push = true) {
  setBusy(true);
  try {
    previousAssetScreen = currentScreenName === "assetDetail" ? previousAssetScreen : currentScreenName;
    const data = await api(`/api/asset/${assetId}`);
    currentAsset = data.asset || null;
    currentManifest = data.manifest || null;
    renderAssetDetail(currentAsset);
    renderSessionReview([]);
    showScreen("assetDetail", false);
    if (push) history.pushState({ assetId }, "", `/asset/${assetId}`);
  } finally {
    setBusy(false);
  }
}

function backFromAsset() {
  if (history.state?.assetId) {
    history.back();
    return;
  }
  if (previousAssetScreen === "profile") openProfile(false);
  else openAssets(false);
}

async function renderChat(data, options = {}) {
  stopPendingTyping();
  const state = data.state || {};
  const session = data.session || {};
  currentManifest = data.manifest || null;
  const isCompleted = Boolean(session.completed);
  currentSessionCompleted = isCompleted;
  renderSessionReview(isCompleted ? data.review?.items || [] : []);
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

function scopeLabel(scope) {
  const labels = {
    session: "仅当前会话",
    project: "项目内生效",
    global: "全局工作方式",
    platform: "对应平台任务",
  };
  return labels[scope] || "待确认作用域";
}

function formatScore(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return `${Math.round(number * 100)}%`;
}

async function getWorkflowPreview(request, preferences = "", capabilityId = "") {
  try {
    return await api("/api/workflow/preview", { method: "POST", body: JSON.stringify({ request, preferences, capability_id: capabilityId, project_id: "default" }) });
  } catch (error) {
    return { stages: defaultWorkflowStages(request) };
  }
}

function defaultWorkflowStages(request = "") {
  const platforms = [];
  if (request.includes("微博")) platforms.push("微博");
  if (request.includes("小红书")) platforms.push("小红书");
  const hasNarrative = /角色|世界观|剧情|设定|城市|魔女/.test(request);
  return [
    { role: "intent_interpreter", name: "需求理解", detail: "提取目标、载体、约束和本次要求。" },
    { role: "researcher", name: "资料检索", detail: platforms.length ? `召回 ${platforms.join("、")} 的表达语境和资料库。` : hasNarrative ? "召回当前会话设定和资料库。" : "召回当前会话资料。" },
    { role: "strategist", name: "创作策略", detail: "把需求、资料和规则转成创作策略。" },
    { role: "draft_writer", name: "初稿写作", detail: "生成第一版可继续讨论的草稿。" },
    { role: "editor", name: "改稿整理", detail: "整理表达，减少模板感。" },
    { role: "critic", name: "质量评审", detail: "检查清晰度和风格贴合度。" },
    ...(platforms.length || hasNarrative ? [{ role: "norm_steward", name: hasNarrative ? "设定检查" : "规范检查", detail: hasNarrative ? "检查角色、世界观和剧情状态是否一致。" : "检查平台规则和发布边界。" }] : []),
  ];
}

function renderPendingChat(request, preview = {}, status = "正在打磨第一版") {
  stopPendingTyping();
  currentSessionId = null;
  currentManifest = null;
  renderSessionReview([]);
  els.chatTitle.textContent = truncate(request, 22);
  els.chatUpdatedAt.textContent = "正在生成";
  els.messageList.innerHTML = "";
  appendMessage("user", request, "你");
  const stages = preview.stages?.length ? preview.stages : defaultWorkflowStages(request);
  const initialStage = stages[0] || {};
  const initialStatus = `正在${initialStage.name || agentNames[initialStage.role] || "处理请求"}`;
  const item = document.createElement("article");
  item.className = "message assistant typing-message";
  item.id = "pendingTypingMessage";
  item.innerHTML = `
    <div class="message-label">EcRoom</div>
    <div class="typing-card">
      <div class="typing-title">${brandMarkMarkup("brand-loader-mini")}<strong id="typingStatusTitle">${escapeHtml(initialStatus)}</strong></div>
      <div class="typing-line" id="typingLine"></div>
      <div class="workflow-steps" id="workflowSteps"></div>
    </div>`;
  els.messageList.appendChild(item);
  startWorkflowProgress(stages);
  showScreen("chat", false);
  history.pushState({}, "", "/#working");
}

function renderWorkflowSteps(stages = [], activeIndex = 0, done = false, options = {}) {
  const line = document.querySelector("#typingLine");
  const title = document.querySelector("#typingStatusTitle");
  const box = document.querySelector("#workflowSteps");
  const safeIndex = Math.max(0, Math.min(activeIndex, Math.max(stages.length - 1, 0)));
  const active = stages[safeIndex] || {};
  const activeName = active.name || agentNames[active.role] || "处理中";
  const pending = Boolean(options.pending);
  if (title) title.textContent = options.title || (done ? "已完成打磨" : pending ? "正在处理请求" : `正在${activeName}`);
  if (line) {
    if (options.detail) {
      line.textContent = options.detail;
    } else if (done) {
      line.textContent = "创作流程已完成，正在整理最终版本。";
    } else if (pending) {
      line.textContent = "EcRoom 正在执行本次创作流程；当前版本暂不伪造中间 Agent 进度。";
    } else {
      line.textContent = `${activeName}：${active.detail || "正在处理当前阶段。"}`;
    }
  }
  if (!box) return;
  box.innerHTML = "";
  stages.forEach((stage, index) => {
    const step = document.createElement("div");
    step.className = `workflow-step ${index < activeIndex || done ? "done" : ""} ${index === safeIndex && !done && !pending ? "active" : ""} ${pending ? "pending" : ""}`;
    step.style.setProperty("--step-index", index);
    step.textContent = stage.name || agentNames[stage.role] || stage.role || "阶段";
    box.appendChild(step);
  });
}

function startWorkflowProgress(stages = [], options = {}) {
  const normalizedStages = stages.length ? stages : [{ role: "orchestrator", name: "处理请求", detail: "正在组织本次创作流程。" }];
  if (pendingTypingTimer) window.clearInterval(pendingTypingTimer);
  pendingWorkflowStartedAt = performance.now();
  let activeIndex = 0;
  let nextAt = pendingWorkflowStartedAt + workflowStageDwell(0);
  renderWorkflowSteps(normalizedStages, 0, false, {
    title: options.title,
    detail: options.detail,
  });
  pendingTypingTimer = window.setInterval(() => {
    if (!document.querySelector("#pendingTypingMessage")) {
      window.clearInterval(pendingTypingTimer);
      pendingTypingTimer = null;
      return;
    }
    const now = performance.now();
    if (now < nextAt || activeIndex >= normalizedStages.length - 1) return;
    activeIndex += 1;
    renderWorkflowSteps(normalizedStages, activeIndex, false);
    nextAt = now + workflowStageDwell(activeIndex);
  }, 180);
}

function workflowStageDwell(index) {
  return [620, 760, 820, 980, 760, 680, 800][index] || 760;
}

async function waitForWorkflowMinimum(stages = []) {
  if (!pendingWorkflowStartedAt) return;
  const minVisible = Math.min(5200, Math.max(2600, (stages.length || 4) * 680));
  const remaining = minVisible - (performance.now() - pendingWorkflowStartedAt);
  if (remaining > 0) await wait(remaining);
}

function wait(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function workflowPreviewFromEvents(events = []) {
  const stages = [];
  for (const item of events) {
    const role = item.role || "";
    const key = role || item.stage_label || item.name || "";
    if (!key || stages.some((stage) => (stage.role || stage.name) === key)) continue;
    stages.push({
      role,
      name: item.stage_label || item.name || agentNames[role] || role,
      detail: item.detail || "已完成当前阶段。",
    });
  }
  return stages;
}

async function finishPendingWorkflow(data = {}, fallbackStages = []) {
  const pending = document.querySelector("#pendingTypingMessage");
  if (!pending) return;
  if (pendingTypingTimer) {
    window.clearInterval(pendingTypingTimer);
    pendingTypingTimer = null;
  }
  pendingWorkflowStartedAt = 0;
  const eventStages = workflowPreviewFromEvents(data.agent_events || data.state?.agent_events || []);
  const traceStages = workflowPreviewFromTrace(data.workflow_trace || data.workflow?.trace || []);
  const stages = eventStages.length ? eventStages : traceStages.length ? traceStages : fallbackStages;
  if (!stages.length) return;
  renderWorkflowSteps(stages, stages.length - 1, true);
  await wait(80);
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

function feedbackWorkflowStages() {
  return [
    { role: "intent_interpreter", name: "反馈定位", detail: "识别你要改的对象、语气和新增约束。" },
    { role: "researcher", name: "上下文对齐", detail: "对齐当前草稿、项目设定和已确认要求。" },
    { role: "editor", name: "改稿整理", detail: "按反馈生成新的可用版本。" },
    { role: "critic", name: "质量复核", detail: "检查新版本是否回应了这次反馈。" },
    { role: "editor", name: "版本收束", detail: "把修改整理成可以继续使用的版本。" },
  ];
}

function inferFeedbackSignal(note = "") {
  const text = note.trim();
  if (/^(请)?(继续|接着|往下|续写|继续输出|接着输出|补完|补全)(写|输出|生成|下去|后面|剩下的|未完成部分)?[。！!,.，\s]*$/i.test(text)) {
    return "continue";
  }
  if (/^(continue|go on|keep going|finish it)$/i.test(text)) return "continue";
  return "edit";
}

function appendInlineTyping(status = "正在继续打磨", stages = feedbackWorkflowStages()) {
  stopPendingTyping();
  const initialStage = stages[0] || {};
  const initialStatus = `正在${initialStage.name || agentNames[initialStage.role] || "处理反馈"}`;
  const item = document.createElement("article");
  item.className = "message assistant typing-message";
  item.id = "pendingTypingMessage";
  item.innerHTML = `
    <div class="message-label">EcRoom</div>
    <div class="typing-card compact">
      <div class="typing-title">${brandMarkMarkup("brand-loader-mini")}<strong id="typingStatusTitle">${escapeHtml(initialStatus)}</strong></div>
      <div class="typing-line" id="typingLine"></div>
      <div class="workflow-steps" id="workflowSteps"></div>
    </div>`;
  els.messageList.appendChild(item);
  els.messageList.scrollTop = els.messageList.scrollHeight;
  startWorkflowProgress(stages);
}

function stopPendingTyping() {
  if (pendingTypingTimer) {
    window.clearInterval(pendingTypingTimer);
    pendingTypingTimer = null;
  }
  pendingWorkflowStartedAt = 0;
  document.querySelector("#pendingTypingMessage")?.remove();
}

function appendMessage(role, content, label) {
  const item = document.createElement("article");
  item.className = `message ${role} message-enter`;
  item.innerHTML = `<div class="message-label">${escapeHtml(label)}</div><div class="message-bubble"></div>`;
  item.querySelector(".message-bubble").textContent = normalizeCreativeText(content || "空内容");
  els.messageList.appendChild(item);
}

async function appendDraft(draft, comments, label = "创作版本", options = {}) {
  const item = document.createElement("article");
  item.className = "message assistant";
  const card = document.createElement("div");
  card.className = "draft-card draft-enter";
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
    button.title = options.completed ? "回到继续创作状态。" : "确认这轮话题已经完成。";
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
  if (!completed) return openReopenWorkModal();
  currentButton?.closest(".draft-card")?.classList.add(completed ? "is-archiving" : "is-returning");
  setBusy(true);
  try {
    await api(`/api/session/${currentSessionId}/complete`, { method: "POST", body: JSON.stringify({ completed }) });
    const data = await api(`/api/session/${currentSessionId}`);
    await renderChat(data);
    if (completed) openPublishPrompt();
    if (sessionReviewQueue.length) showToast(`本次有 ${sessionReviewQueue.length} 条工作方式建议`);
  } finally {
    setBusy(false);
  }
}

function openPublishPrompt() {
  if (!currentSessionId) return;
  els.publishPromptModal.classList.add("open");
}

function closePublishPrompt() {
  els.publishPromptModal.classList.remove("open");
}

function openReopenWorkModal() {
  if (!els.reopenWorkModal) return continueCurrentWork({ revokeLearning: true });
  closePublishPrompt();
  els.reopenWorkModal.classList.add("open");
  els.reopenWorkModal.setAttribute("aria-hidden", "false");
}

function closeReopenWorkModal() {
  if (!els.reopenWorkModal) return;
  els.reopenWorkModal.classList.remove("open");
  els.reopenWorkModal.setAttribute("aria-hidden", "true");
}

async function publishCurrentWork() {
  if (!currentSessionId) return;
  setBusy(true);
  try {
    const data = await api("/api/publish/draft", { method: "POST", body: JSON.stringify({ work_id: currentSessionId }) });
    closePublishPrompt();
    await openPublish(data.post.post_id);
    maybeOpenCompletionReview();
  } finally {
    setBusy(false);
  }
}

function saveWorkOnly() {
  closePublishPrompt();
  maybeOpenCompletionReview();
}

function maybeOpenCompletionReview() {
  if (sessionReviewQueue.length) window.setTimeout(() => openSessionReview(), 160);
}

async function continueCurrentWork({ revokeLearning = true } = {}) {
  if (!currentSessionId) return closePublishPrompt();
  closePublishPrompt();
  closeReopenWorkModal();
  const result = await api(`/api/session/${currentSessionId}/complete`, {
    method: "POST",
    body: JSON.stringify({ completed: false, revoke_learning: revokeLearning }),
  });
  const data = await api(`/api/session/${currentSessionId}`);
  await renderChat(data);
  await loadSessions();
  const revoked = Number(result.revoked_learning_count || 0) + Number(result.revoked_confirmed_learning_count || 0);
  showToast(revokeLearning && revoked ? `已清理 ${revoked} 条旧学习记录` : "已回到继续创作状态");
}

async function openPublish(postId, push = true) {
  setBusy(true);
  try {
    previousPublishScreen = currentScreenName === "publish" ? previousPublishScreen : currentScreenName;
    const data = await api(`/api/post/${postId}`);
    if (data.post?.status === "published") {
      await openPostDetail(data.post, push);
      return;
    }
    renderPublish(data);
    showScreen("publish", false);
    if (push) history.pushState({ postId }, "", `/publish/${postId}`);
  } finally {
    setBusy(false);
  }
}

function renderPublish(data) {
  const post = data.post || {};
  currentPublishPost = post;
  currentSessionId = post.session_id || currentSessionId;
  publishTags = Array.isArray(post.tags) ? post.tags.flatMap((tag) => normalizeTagValues(tag)).slice(0, 12) : [];
  publishDefaultTags = [];
  publishCoverDataUrl = "";
  els.publishTitle.value = post.title || "";
  els.publishBody.value = normalizeCreativeText(post.body || "");
  autoResizeTextarea(els.publishBody);
  setPublishCover(post.cover_url || "");
  if (els.publishDeleteBtn) els.publishDeleteBtn.hidden = !post.post_id;
  renderPublishTags();
  updatePublishPreview();
}

function setPublishCover(src) {
  if (!src) {
    els.publishCoverImage.removeAttribute("src");
    els.publishPreviewCover.removeAttribute("src");
    els.publishCoverBtn.classList.remove("has-image");
    return;
  }
  els.publishCoverImage.src = src;
  els.publishPreviewCover.src = src;
  els.publishCoverBtn.classList.add("has-image");
}

function renderPublishTags() {
  els.publishTagChoices.innerHTML = "";
  els.publishTagList.innerHTML = "";
  for (const tag of publishTags) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "publish-tag-pill";
    item.textContent = `${tag} ×`;
    item.addEventListener("click", () => removePublishTag(tag));
    els.publishTagList.appendChild(item);
  }
  updatePublishPreview();
}

function normalizeTagValue(value) {
  return String(value || "").replace(/[#＃\s]/g, "").slice(0, 16);
}

function normalizeTagValues(value) {
  return String(value || "")
    .split(/[\/／|｜,，、;；\s]+/g)
    .map((item) => normalizeTagValue(item))
    .filter(Boolean);
}

function addPublishTag(value) {
  const tags = normalizeTagValues(value);
  for (const tag of tags) {
    if (!tag || publishTags.includes(tag) || publishTags.length >= 12) continue;
    publishTags.push(tag);
  }
  renderPublishTags();
}

function removePublishTag(tag) {
  publishTags = publishTags.filter((item) => item !== tag);
  renderPublishTags();
}

function updatePublishPreview() {
  if (!els.publishPreviewTitle) return;
  els.publishPreviewTitle.textContent = els.publishTitle.value.trim() || "未命名作品";
  els.publishPreviewBody.textContent = normalizeCreativeText(els.publishBody.value || "正文预览会显示在这里。");
  els.publishPreviewTags.innerHTML = "";
  for (const tag of publishTags) {
    const span = document.createElement("span");
    span.textContent = tag;
    els.publishPreviewTags.appendChild(span);
  }
}

function readPublishCover(file) {
  if (!file) return;
  if (!/^image\/(png|jpeg|webp)$/.test(file.type)) {
    showToast("只支持 png、jpg、webp 图片");
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    publishCoverDataUrl = String(reader.result || "");
    setPublishCover(publishCoverDataUrl);
  };
  reader.readAsDataURL(file);
}

async function savePublish(status = "draft") {
  if (!currentPublishPost?.post_id) return;
  const payload = {
    title: els.publishTitle.value,
    body: els.publishBody.value,
    tags: publishTags,
    status,
    cover_data_url: publishCoverDataUrl,
  };
  setBusy(true);
  try {
    const data = await api(`/api/post/${currentPublishPost.post_id}`, { method: "POST", body: JSON.stringify(payload) });
    renderPublish(data);
    await loadPosts();
    showToast(status === "published" ? "已发布到个人主页" : "发布草稿已保存");
    if (status === "published") await openPostDetail(data.post || data, true);
  } finally {
    setBusy(false);
  }
}

async function deleteCurrentPost() {
  if (!currentPublishPost?.post_id) return;
  const confirmed = window.confirm("删除后，这篇作品会从个人主页和资产库移除。确定删除吗？");
  if (!confirmed) return;
  setBusy(true);
  try {
    await api(`/api/post/${currentPublishPost.post_id}`, { method: "DELETE" });
    currentPublishPost = null;
    await loadPosts();
    await loadAssets();
    showToast("作品已删除");
    if (previousPublishScreen === "assets") openAssets(false);
    else openProfile(false);
    history.pushState({}, "", previousPublishScreen === "assets" ? "/assets" : "/profile");
  } finally {
    setBusy(false);
  }
}

function backFromPublish() {
  if (history.state?.postId) {
    history.back();
    return;
  }
  if (previousPublishScreen === "profile") openProfile(false);
  else if (currentSessionId) openSession(currentSessionId, false);
  else showScreen("generate", false);
}

function typeText(element, text) {
  return new Promise((resolve) => {
    const value = String(text || "");
    let index = 0;
    const chunkSize = value.length > 900 ? 5 : 3;
    const timer = window.setInterval(() => {
      const shouldFollow = isNearScrollBottom(els.messageList);
      index = Math.min(value.length, index + chunkSize);
      element.textContent = value.slice(0, index);
      if (shouldFollow) scrollMessageListToBottom({ smooth: true });
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

function sessionTimeGroup(session) {
  const raw = session.updated_at || session.created_at || "";
  const time = raw ? new Date(raw) : null;
  if (!time || Number.isNaN(time.getTime())) return "更早";
  const today = new Date();
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  const startOfSession = new Date(time.getFullYear(), time.getMonth(), time.getDate()).getTime();
  const days = Math.floor((startOfToday - startOfSession) / 86400000);
  if (days <= 0) return "今天";
  if (days <= 7) return "最近 7 天";
  if (days <= 30) return "最近 30 天";
  return "更早";
}

function statusLabelForAsset(asset = {}, context = "asset") {
  if (context === "published" || asset.source === "published" || asset.status === "published") return "已发布";
  if (asset.source === "inspiration" && asset.collected) return "已收藏";
  if (asset.liked) return "已喜欢";
  if (asset.source === "inspiration") return "灵感";
  return "私有保存";
}

function isNearScrollBottom(element, threshold = 96) {
  if (!element) return true;
  return element.scrollHeight - element.clientHeight <= element.scrollTop + threshold;
}

function scrollMessageListToBottom({ smooth = false } = {}) {
  if (!els.messageList) return;
  els.messageList.scrollTo({
    top: els.messageList.scrollHeight,
    behavior: smooth ? "smooth" : "auto",
  });
}

function autoResizeTextarea(textarea) {
  if (!textarea) return;
  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, 300)}px`;
}

function bindComposerTextarea(textarea) {
  if (!textarea) return;
  autoResizeTextarea(textarea);
  textarea.addEventListener("input", () => autoResizeTextarea(textarea));
}

async function loadSessions() {
  const data = await api("/api/sessions");
  sessionsCache = data.sessions || [];
  renderSessions(sessionsCache);
  renderHistoryManager();
  renderInspirationGrid();
  updateSessionReviewButton();
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

async function loadPosts() {
  const data = await api("/api/posts?project_id=default");
  postsCache = data.posts || [];
  publishDefaultTags = [];
  renderProfile();
  renderInspirationGrid();
  return postsCache;
}

function renderSessions(sessions) {
  els.sessionList.innerHTML = "";
  if (!sessions.length) {
    els.sessionList.innerHTML = '<div class="empty-row">还没有对话。</div>';
    return;
  }
  let currentGroup = "";
  for (const session of sessions) {
    const group = sessionTimeGroup(session);
    if (group !== currentGroup) {
      currentGroup = group;
      const label = document.createElement("div");
      label.className = "session-group-label";
      label.textContent = group;
      els.sessionList.appendChild(label);
    }
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

function closeSessionMenus() {
  document.querySelectorAll(".session-menu.open").forEach((menu) => {
    menu.classList.remove("open");
    menu.setAttribute("aria-hidden", "true");
  });
  document.querySelectorAll(".session-row.menu-open").forEach((row) => row.classList.remove("menu-open"));
}

function openHistoryManager() {
  closeSettingsModal();
  renderHistoryManager();
  els.historyManageModal.classList.add("open");
  els.historyManageModal.setAttribute("aria-hidden", "false");
}

function closeHistoryManager() {
  els.historyManageModal.classList.remove("open");
  els.historyManageModal.setAttribute("aria-hidden", "true");
}

function renderHistoryManager() {
  if (!els.historyManageList) return;
  if (!sessionsCache.length) {
    els.historyManageList.innerHTML = '<div class="empty-row">还没有可管理的对话。</div>';
    return;
  }
  els.historyManageList.innerHTML = "";
  sessionsCache.forEach((session) => {
    const row = document.createElement("article");
    row.className = "history-manage-row";
    row.innerHTML = `
      <button class="history-manage-main" type="button" data-open-session="${escapeHtml(session.session_id)}">
        <strong>${escapeHtml(session.title || session.raw_request || "未命名对话")}</strong>
        <span>${escapeHtml(session.completed ? "已完成作品" : "创作对话")} · ${escapeHtml(formatSessionDate(session.updated_at))}</span>
      </button>
      <button class="danger-button history-delete-button" type="button" data-delete-session="${escapeHtml(session.session_id)}">删除</button>`;
    els.historyManageList.appendChild(row);
  });
}

function formatSessionDate(value) {
  if (!value) return "未知时间";
  if (typeof value === "number") return new Date(value * 1000).toLocaleDateString();
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value).slice(0, 10) : date.toLocaleDateString();
}

function renderInspirationGrid() {
  const searchQuery = (els.feedSearch?.value || "").trim();
  if (searchQuery) {
    renderSiteSearchResults(searchQuery);
    return;
  }
  const items = currentInspirationPool();
  const isDiscover = activeFeedCategory === "discover";
  els.inspirationGrid.classList.toggle("space-carousel", isDiscover);
  els.inspirationGrid.classList.toggle("board-grid", !isDiscover);
  els.inspirationGrid.classList.remove("site-search-grid");
  if (!isDiscover) {
    renderBoardInspirationGrid(items);
    return;
  }
  const batchCount = Math.max(1, Math.ceil(items.length / 8));
  inspirationBatchIndex = ((inspirationBatchIndex % batchCount) + batchCount) % batchCount;
  const start = inspirationBatchIndex * 8;
  const batchSize = Math.min(8, items.length);
  inspirationVisibleItems = Array.from({ length: batchSize }, (_, index) => items[(start + index) % items.length]).filter(Boolean);
  inspirationRotation = ((inspirationRotation % Math.max(inspirationVisibleItems.length, 1)) + Math.max(inspirationVisibleItems.length, 1)) % Math.max(inspirationVisibleItems.length, 1);
  const key = inspirationVisibleItems.map((item) => item.id || item.asset_id).join("|");
  if (els.refreshFeedBtn) {
    els.refreshFeedBtn.hidden = items.length <= 8;
    renderPullRefreshButton();
  }
  if (key === inspirationRenderedKey) {
    updateInspirationLayout();
    return;
  }
  inspirationRenderedKey = key;
  els.inspirationGrid.innerHTML = "";
  inspirationVisibleItems.forEach((item, index) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = `inspire-card tone-${item.tone || "cyan"} space-0`;
    card.dataset.itemId = item.id || item.asset_id || "";
    card.style.setProperty("--tile-index", index);
    card.style.setProperty("--tile-delay", `${index * 34}ms`);
    card.innerHTML = `
      <img src="${escapeHtml(imageForCard(item, index))}" alt="${escapeHtml(item.title)}" loading="lazy" />
      <span>${escapeHtml(item.type)}</span>
      <strong>${escapeHtml(item.title)}</strong>
      <small>${escapeHtml(truncate(item.prompt, 72))}</small>`;
    card.addEventListener("click", () => openPreview(item));
    els.inspirationGrid.appendChild(card);
  });
  updateInspirationLayout();
}

function renderBoardInspirationGrid(items) {
  inspirationVisibleItems = items;
  inspirationRotation = 0;
  if (els.refreshFeedBtn) els.refreshFeedBtn.hidden = true;
  const key = `${activeFeedCategory}|board|${items.map((item) => item.id || item.asset_id).join("|")}`;
  if (key === inspirationRenderedKey) return;
  inspirationRenderedKey = key;
  els.inspirationGrid.innerHTML = "";
  if (!items.length) {
    els.inspirationGrid.innerHTML = '<div class="empty-state">没有找到对应灵感。</div>';
    return;
  }
  items.forEach((item, index) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = `inspire-card board-card tone-${item.tone || "cyan"}`;
    card.dataset.itemId = item.id || item.asset_id || "";
    card.style.setProperty("--tile-index", index);
    card.style.setProperty("--tile-delay", `${(index % 12) * 28}ms`);
    card.innerHTML = `
      <img src="${escapeHtml(imageForCard(item, index))}" alt="${escapeHtml(item.title)}" loading="lazy" />
      <span>${escapeHtml(item.type)}</span>
      <strong>${escapeHtml(item.title)}</strong>
      <small>${escapeHtml(truncate(item.prompt, 72))}</small>`;
    card.addEventListener("click", () => openPreview(item));
    els.inspirationGrid.appendChild(card);
  });
}

function renderSiteSearchResults(query) {
  const items = siteSearchResults(query);
  inspirationVisibleItems = [];
  inspirationRotation = 0;
  if (els.refreshFeedBtn) els.refreshFeedBtn.hidden = true;
  els.inspirationGrid.classList.remove("space-carousel", "board-grid");
  els.inspirationGrid.classList.add("site-search-grid");
  const key = `site-search|${query}|${items.map((item) => item.id).join("|")}`;
  if (key === inspirationRenderedKey) return;
  inspirationRenderedKey = key;
  els.inspirationGrid.innerHTML = "";
  if (!items.length) {
    els.inspirationGrid.innerHTML = '<div class="empty-state search-empty">没有找到已上传或已发布的作品。</div>';
    return;
  }
  const head = document.createElement("div");
  head.className = "search-result-head";
  head.innerHTML = `<span>全站作品搜索</span><strong>${items.length} 个结果</strong>`;
  els.inspirationGrid.appendChild(head);
  items.forEach((item, index) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "search-result-card";
    card.style.setProperty("--tile-delay", `${(index % 10) * 24}ms`);
    card.innerHTML = `
      <img src="${escapeHtml(item.image)}" alt="${escapeHtml(item.title)}" loading="lazy" />
      <span>${escapeHtml(item.kindLabel)}</span>
      <strong>${escapeHtml(item.title)}</strong>
      <small>${escapeHtml(truncate(item.summary, 118))}</small>
      <em>${escapeHtml(item.meta)}</em>`;
    card.addEventListener("click", () => openSearchResult(item));
    els.inspirationGrid.appendChild(card);
  });
}

function siteSearchResults(query) {
  const normalized = query.toLowerCase();
  const results = [];
  postsCache.forEach((post, index) => {
    const searchable = `${post.title || ""}${post.body || ""}${(post.tags || []).join("")}`.toLowerCase();
    if (!searchable.includes(normalized)) return;
    results.push({
      id: `post:${post.post_id}`,
      kind: "post",
      kindLabel: post.status === "published" ? "已发布作品" : "发布草稿",
      title: post.title || "未命名作品",
      summary: post.body || "",
      meta: post.tags?.length ? post.tags.join(" / ") : "个人主页作品",
      image: post.cover_data || post.cover || imageForCard(post, index),
      payload: post,
    });
  });
  assetsCache
    .filter((asset) => asset.source !== "inspiration")
    .forEach((asset, index) => {
      const searchable = `${asset.title || ""}${asset.prompt || ""}${asset.final_content || ""}${asset.goal || ""}${(asset.tags || []).join("")}`.toLowerCase();
      if (!searchable.includes(normalized)) return;
      results.push({
        id: `asset:${asset.asset_id}`,
        kind: "asset",
        kindLabel: asset.status === "published" ? "作品" : "私有作品",
        title: asset.title || asset.prompt || "未命名作品",
        summary: asset.final_content || asset.prompt || "",
        meta: asset.status === "published" ? "已发布" : "仅自己可见",
        image: imageForCard(asset, index),
        payload: asset,
      });
    });
  return results.slice(0, 36);
}

function openSearchResult(item) {
  if (item.kind === "post") {
    openPostDetail(item.payload);
    return;
  }
  openAssetFromCard(item.payload);
}

function currentInspirationPool() {
  const reusableAssets = assetsCache.filter((item) => item.source !== "inspiration" || item.collected || item.liked);
  const fromAssets = activeFeedCategory === "discover" ? reusableAssets.map((item, index) => ({
    id: item.asset_id,
    category: "discover",
    title: item.title || item.prompt,
    type: "你的创作",
    prompt: item.prompt,
    final_content: item.final_content,
    asset_id: item.asset_id,
    skills: item.skills || [],
    platforms: item.platforms || [],
    image: imageForCard(item, index),
    tone: ["cyan", "amber", "violet", "green", "red", "blue"][index % 6],
  })) : [];
  const sourceItems = activeFeedCategory === "discover" ? feedItems : feedItems.filter((item) => item.category === activeFeedCategory);
  return [...sourceItems, ...fromAssets];
}

function inspirationSource(sourceId) {
  return feedItems.find((item) => item.id === sourceId);
}

function normalizeAssetForDisplay(asset = {}, index = 0) {
  const source = inspirationSource(asset.source_id);
  if (!source) {
    return { ...asset, image: imageForCard(asset, index), final_content: asset.final_content || "", prompt: asset.prompt || "" };
  }
  return {
    ...source,
    ...asset,
    title: asset.title || source.title,
    type: asset.goal || source.type,
    prompt: asset.prompt || source.prompt,
    final_content: asset.final_content || source.final_content,
    image: source.image || asset.image || imageForCard(asset, index),
    skills: asset.skills?.length ? asset.skills : source.skills || [],
    platforms: asset.platforms?.length ? asset.platforms : source.platforms || [],
    category: asset.category || source.category,
  };
}

function updateInspirationLayout() {
  const total = Math.max(inspirationVisibleItems.length, 1);
  els.inspirationGrid.querySelectorAll(".inspire-card").forEach((card, index) => {
    const slot = ((index - inspirationRotation) % total + total) % total;
    for (let i = 0; i < 8; i += 1) card.classList.remove(`space-${i}`);
    card.classList.add(`space-${slot}`);
    card.dataset.slot = String(slot);
    card.style.zIndex = String(slotZIndex(slot));
  });
}

function rotateInspiration(delta) {
  if (!inspirationVisibleItems.length) return;
  const now = Date.now();
  if (now - inspirationWheelLock < 170) return;
  inspirationWheelLock = now;
  inspirationRotation += delta > 0 ? 1 : -1;
  updateInspirationLayout();
}

function slotZIndex(slot) {
  return [8, 7, 5, 3, 2, 3, 5, 7][slot] || 1;
}

function refreshInspirationBatch() {
  if (els.refreshFeedBtn) {
    els.refreshFeedBtn.classList.remove("is-pulled");
    void els.refreshFeedBtn.offsetWidth;
    els.refreshFeedBtn.classList.add("is-pulled");
    window.setTimeout(() => els.refreshFeedBtn?.classList.remove("is-pulled"), 620);
  }
  inspirationBatchIndex += 1;
  inspirationRotation = 0;
  inspirationRenderedKey = "";
  renderInspirationGrid();
}

function setPullRefreshOffset(offset) {
  if (!els.refreshFeedBtn) return;
  const safeOffset = Math.max(0, Math.min(offset, 54));
  pullRefreshState.offset = safeOffset;
  els.refreshFeedBtn.style.setProperty("--pull-offset", `${safeOffset}px`);
  els.refreshFeedBtn.classList.toggle("is-ready", safeOffset >= 38);
}

function resetPullRefreshControl() {
  pullRefreshState.dragging = false;
  pullRefreshState.pointerId = null;
  els.refreshFeedBtn?.classList.remove("is-dragging", "is-ready");
  window.setTimeout(() => setPullRefreshOffset(0), 20);
}

function beginPullRefresh(event) {
  if (!els.refreshFeedBtn || els.refreshFeedBtn.hidden) return;
  pullRefreshState = { dragging: true, startY: event.clientY, offset: 0, pointerId: event.pointerId };
  els.refreshFeedBtn.classList.add("is-dragging");
  els.refreshFeedBtn.setPointerCapture?.(event.pointerId);
  setPullRefreshOffset(0);
}

function movePullRefresh(event) {
  if (!pullRefreshState.dragging || pullRefreshState.pointerId !== event.pointerId) return;
  event.preventDefault();
  const delta = Math.max(0, event.clientY - pullRefreshState.startY);
  setPullRefreshOffset(delta);
}

function endPullRefresh(event) {
  if (!pullRefreshState.dragging || pullRefreshState.pointerId !== event.pointerId) return;
  const shouldRefresh = pullRefreshState.offset >= 38;
  els.refreshFeedBtn?.releasePointerCapture?.(event.pointerId);
  resetPullRefreshControl();
  if (shouldRefresh) refreshInspirationBatch();
}

function handleInspirationWheel(event) {
  if (window.matchMedia("(max-width: 760px)").matches) return;
  if (activeFeedCategory !== "discover") return;
  event.preventDefault();
  rotateInspiration(event.deltaY || event.deltaX || 0);
}

function updateInspirationParallax(event) {
  if (!els.inspirationGrid) return;
  const rect = els.inspirationGrid.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const mx = ((event.clientX - rect.left) / rect.width - 0.5).toFixed(3);
  const my = ((event.clientY - rect.top) / rect.height - 0.5).toFixed(3);
  els.inspirationGrid.style.setProperty("--mx", mx);
  els.inspirationGrid.style.setProperty("--my", my);
}

function resetInspirationParallax() {
  if (!els.inspirationGrid) return;
  els.inspirationGrid.style.setProperty("--mx", "0");
  els.inspirationGrid.style.setProperty("--my", "0");
}

function openPreview(item) {
  currentPreviewMode = "inspiration";
  els.previewModal.classList.remove("post-preview-mode");
  setEcRoomAuthor(els.previewAuthorName, els.previewAuthorAvatar);
  const related = relatedAsset(item);
  const collectedAssetId = related?.collected ? related.asset_id : "";
  currentPreviewItem = { ...item, liked: Boolean(item.liked || related?.liked), asset_id: item.asset_id || collectedAssetId };
  if (els.previewImage) {
    els.previewImage.src = imageForCard(currentPreviewItem);
    els.previewImage.alt = currentPreviewItem.title || "灵感封面";
  }
  els.previewTitle.textContent = currentPreviewItem.title || "灵感详情";
  els.previewType.textContent = currentPreviewItem.type || assetLabel(currentPreviewItem);
  if (els.previewPromptSection) els.previewPromptSection.hidden = false;
  if (els.previewPromptLabel) els.previewPromptLabel.textContent = "完整提示词";
  if (els.previewOutputLabel) els.previewOutputLabel.textContent = "最后版本";
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
  els.applyPreviewBtn.textContent = "应用";
  els.previewModal.classList.add("open");
}

function closePreview() {
  els.previewModal.classList.remove("open");
  if (currentPreviewMode === "post" && location.pathname.startsWith("/publish/")) {
    history.pushState({}, "", currentScreenName === "assets" ? "/assets" : "/profile");
  }
  currentPreviewMode = "inspiration";
}

async function openPostDetail(post, push = true) {
  currentPreviewMode = "post";
  currentPublishPost = post;
  currentSessionId = post.session_id || currentSessionId;
  currentPreviewItem = { ...post, source: "published_post" };
  if (currentScreenName !== "profile" && currentScreenName !== "assets") {
    await openProfile(false);
  }
  const cover = post.cover_url || "/assets/inspiration/writing.jpg";
  if (els.previewImage) {
    els.previewImage.src = cover;
    els.previewImage.alt = post.title || "帖子封面";
  }
  els.previewTitle.textContent = post.title || "未命名帖子";
  els.previewType.textContent = post.status === "published" ? "已发布作品" : "发布草稿";
  setAuthorNode(els.previewAuthorName, els.previewAuthorAvatar);
  if (els.previewPromptSection) els.previewPromptSection.hidden = true;
  if (els.previewOutputLabel) els.previewOutputLabel.textContent = "正文";
  els.previewOutput.textContent = normalizeCreativeText(post.body || "这篇帖子还没有正文。");
  const meta = [];
  if (post.published_at) meta.push(`发布于 ${post.published_at.slice(0, 10)}`);
  els.previewMeta.textContent = meta.join("  |  ") || "个人主页帖子";
  els.likePreviewBtn.textContent = post.session_id ? "打开原会话" : "返回主页";
  els.collectPreviewBtn.textContent = "删除帖子";
  els.applyPreviewBtn.textContent = "编辑帖子";
  els.previewModal.classList.add("post-preview-mode");
  els.previewModal.classList.add("open");
  if (push) history.pushState({ postId: post.post_id, mode: "post" }, "", `/publish/${post.post_id}`);
}

function categoryName(category) {
  return { discover: "推荐", post: "帖子", video: "视频", longform: "长文", story: "故事", knowledge: "知识", professional: "职场" }[category] || "推荐";
}

function isCollected(item) {
  return Boolean(relatedAsset(item)?.collected);
}

function relatedAsset(item) {
  const sourceId = item.source_id || item.id || "";
  return assetsCache.find((asset) => (sourceId && asset.source_id === sourceId) || asset.asset_id === item.asset_id);
}

function isInspirationAsset(item = {}) {
  return item.source === "inspiration" || Boolean(item.source_id && inspirationSource(item.source_id));
}

function refreshVisibleCollections() {
  renderInspirationGrid();
  if (currentScreenName === "assets") renderAssetsPage();
  if (currentScreenName === "profile") renderProfile();
}

async function collectPreview() {
  if (!currentPreviewItem) return;
  if (currentPreviewMode === "post") {
    await deletePostFromPreview();
    return;
  }
  const item = currentPreviewItem;
  const collected = isCollected(item);
  const data = await api(collected ? "/api/assets/uncollect" : "/api/assets/collect", {
    method: "POST",
    body: JSON.stringify(inspirationPayload(item, { liked: item.liked || false })),
  });
  showToast(collected ? "已取消收藏" : "已收藏到资产库");
  await loadAssets();
  refreshVisibleCollections();
  currentPreviewItem = { ...item, asset_id: data.asset.asset_id };
  openPreview(currentPreviewItem);
}

async function likePreview() {
  if (!currentPreviewItem) return;
  if (currentPreviewMode === "post") {
    closePreview();
    if (currentPreviewItem.session_id) await openSession(currentPreviewItem.session_id);
    else await openProfile();
    return;
  }
  const item = currentPreviewItem;
  const liked = !item.liked;
  const data = await api("/api/assets/like", {
    method: "POST",
    body: JSON.stringify(inspirationPayload(item, { liked, collected: isCollected(item) })),
  });
  currentPreviewItem = { ...item, liked, asset_id: data.asset.asset_id };
  await loadAssets();
  refreshVisibleCollections();
  openPreview(currentPreviewItem);
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
    image: imageForCard(item),
    ...overrides,
  };
}

function imageForCard(item = {}, index = 0) {
  const fallback = [
    "/assets/inspiration/writing.jpg",
    "/assets/inspiration/character.jpg",
    "/assets/inspiration/city.jpg",
    "/assets/inspiration/campaign.jpg",
    "/assets/inspiration/release.jpg",
    "/assets/inspiration/norm.jpg",
  ];
  return item.image || item.cover_url || item.media_url || fallback[index % fallback.length];
}

function applyPreview() {
  if (currentPreviewMode === "post") {
    const postId = currentPreviewItem?.post_id;
    if (!postId) return;
    closePreview();
    openPublishEditor(postId);
    return;
  }
  if (!currentPreviewItem) return;
  clearSelectedSkill({ input: els.request, removePrompt: false });
  els.request.value = currentPreviewItem.prompt || "";
  autoResizeTextarea(els.request);
  closePreview();
  showScreen("generate");
  history.pushState({}, "", "/#generate");
  pulseElement(els.createForm, "composer-arrive", 680);
  els.request.focus();
}

async function openPublishEditor(postId, push = true) {
  setBusy(true);
  try {
    previousPublishScreen = currentScreenName === "publish" ? previousPublishScreen : currentScreenName;
    const data = await api(`/api/post/${postId}`);
    renderPublish(data);
    showScreen("publish", false);
    if (push) history.pushState({ postId, mode: "edit" }, "", `/publish/${postId}`);
  } finally {
    setBusy(false);
  }
}

async function deletePostFromPreview() {
  if (!currentPreviewItem?.post_id) return;
  const confirmed = window.confirm("删除后，这篇帖子会从个人主页和资产库移除。确定删除吗？");
  if (!confirmed) return;
  setBusy(true);
  try {
    await api(`/api/post/${currentPreviewItem.post_id}`, { method: "DELETE" });
    closePreview();
    await loadPosts();
    await loadAssets();
    renderProfile();
    showToast("帖子已删除");
  } finally {
    setBusy(false);
  }
}

function renderProfile() {
  if (!els.profileGrid) return;
  if (!["published", "liked", "collected"].includes(activeProfileTab)) activeProfileTab = "published";
  const works = postsCache.filter((post) => post.status === "published");
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
  source.forEach((asset, index) => {
    const displayAsset = normalizeAssetForDisplay(asset, index);
    const card = document.createElement("button");
    card.type = "button";
    card.className = "asset-card profile-work-card";
    card.style.setProperty("--tile-index", index);
    card.style.setProperty("--tile-delay", `${(index % 9) * 28}ms`);
    const image = imageForCard(displayAsset, index);
    card.classList.add("has-card-image");
    const status = statusLabelForAsset(displayAsset, activeProfileTab === "published" ? "published" : activeProfileTab);
    card.innerHTML = `
      <img class="asset-card-image" src="${escapeHtml(image)}" alt="${escapeHtml(displayAsset.title || "内容封面")}" />
      <span class="asset-card-kicker">${escapeHtml(assetLabel(displayAsset))}</span>
      <span class="asset-card-status">${escapeHtml(status)}</span>
      <strong>${escapeHtml(displayAsset.title || "未命名资产")}</strong>
      <small>${escapeHtml(truncate(normalizeCreativeText(activeProfileTab === "published" ? displayAsset.body || displayAsset.final_content || "" : displayAsset.prompt || ""), 70))}</small>`;
    card.addEventListener("click", () => {
      if (activeProfileTab === "published" || displayAsset.source === "published") openPublish(displayAsset.post_id);
      else if (isInspirationAsset(displayAsset)) openPreview(displayAsset);
      else openAsset(displayAsset.asset_id);
    });
    els.profileGrid.appendChild(card);
  });
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
  assets.forEach((rawAsset, index) => {
    const asset = normalizeAssetForDisplay(rawAsset, index);
    const card = document.createElement("article");
    card.tabIndex = 0;
    card.setAttribute("role", "button");
    card.setAttribute("aria-label", `打开资产：${asset.title || "未命名资产"}`);
    card.className = "asset-card";
    card.style.setProperty("--tile-index", index);
    card.style.setProperty("--tile-delay", `${(index % 9) * 28}ms`);
    const image = imageForCard(asset, index);
    card.classList.add("has-card-image");
    const canDelete = canDeleteAsset(asset);
    const status = statusLabelForAsset(asset);
    card.innerHTML = `
      <img class="asset-card-image" src="${escapeHtml(image)}" alt="${escapeHtml(asset.title || "资产封面")}" />
      ${canDelete ? `
        <span class="asset-card-menu-wrap">
          <button class="asset-card-menu-button" type="button" aria-label="资产操作" title="资产操作">
            <svg aria-hidden="true"><use href="#i-more"></use></svg>
          </button>
          <span class="asset-card-menu" aria-hidden="true">
            <button type="button" data-action="delete-asset" data-asset-id="${escapeHtml(asset.asset_id)}">
              <svg aria-hidden="true"><use href="#i-trash"></use></svg>删除资产
            </button>
          </span>
        </span>` : ""}
      <span class="asset-card-kicker">${escapeHtml(assetLabel(asset))}</span>
      <span class="asset-card-status">${escapeHtml(status)}</span>
      <strong>${escapeHtml(asset.title || "未命名资产")}</strong>
      <small>${escapeHtml(truncate(normalizeCreativeText(asset.prompt || ""), 76))}</small>
      <p>${escapeHtml(truncate(normalizeCreativeText(asset.final_content || "还没有最终内容。"), 120))}</p>`;
    card.addEventListener("click", (event) => {
      if (event.target.closest(".asset-card-menu-wrap")) return;
      openAssetFromCard(asset);
    });
    card.addEventListener("keydown", (event) => {
      if (event.target.closest(".asset-card-menu-wrap")) return;
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      openAssetFromCard(asset);
    });
    const menuButton = card.querySelector(".asset-card-menu-button");
    menuButton?.addEventListener("click", (event) => {
      event.stopPropagation();
      const menu = card.querySelector(".asset-card-menu");
      const nextOpen = !menu?.classList.contains("open");
      closeAssetCardMenus();
      menu?.classList.toggle("open", nextOpen);
      menu?.setAttribute("aria-hidden", nextOpen ? "false" : "true");
    });
    const deleteButton = card.querySelector('[data-action="delete-asset"]');
    deleteButton?.addEventListener("click", async (event) => {
      event.stopPropagation();
      await deleteAssetFromCard(asset);
    });
    els.assetGrid.appendChild(card);
  });
}

function canDeleteAsset(asset) {
  return Boolean(asset?.asset_id && !isInspirationAsset(asset));
}

function openAssetFromCard(asset) {
  if (asset.source === "published") openPublish(asset.post_id);
  else if (isInspirationAsset(asset)) openPreview(asset);
  else openAsset(asset.asset_id);
}

function closeAssetCardMenus() {
  document.querySelectorAll(".asset-card-menu.open").forEach((menu) => {
    menu.classList.remove("open");
    menu.setAttribute("aria-hidden", "true");
  });
}

async function deleteAssetFromCard(asset) {
  if (!canDeleteAsset(asset)) return;
  closeAssetCardMenus();
  const confirmed = window.confirm("删除这个资产？这只会移除作品库里的这条资产。");
  if (!confirmed) return;
  setBusy(true);
  try {
    await api(`/api/asset/${asset.asset_id}`, { method: "DELETE" });
    const deletedAssetId = asset.asset_id || "";
    const deletedPostId = asset.post_id || "";
    assetsCache = assetsCache.filter((item) => {
      if (deletedAssetId && item.asset_id === deletedAssetId) return false;
      if (deletedPostId && item.post_id === deletedPostId) return false;
      return true;
    });
    postsCache = postsCache.filter((post) => {
      if (deletedPostId && post.post_id === deletedPostId) return false;
      if (deletedAssetId && post.post_id === deletedAssetId) return false;
      return true;
    });
    renderAssetsPage();
    if (currentScreenName === "profile") renderProfile();
    showToast("资产已删除");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(false);
  }
}

function renderAssetDetail(asset) {
  if (!asset) return;
  const displayAsset = normalizeAssetForDisplay(asset);
  els.assetDetailTitle.textContent = displayAsset.title || "未命名资产";
  els.assetWorkType.textContent = assetLabel(displayAsset);
  setAuthorNode(els.assetAuthorName, els.assetAuthorAvatar);
  els.assetFinalContent.textContent = normalizeCreativeText(displayAsset.final_content || "这条资产还没有最终内容。");
  els.assetPrompt.textContent = normalizeCreativeText(displayAsset.prompt || "无");
  const meta = [];
  if (displayAsset.updated_at) meta.push(displayAsset.updated_at.slice(0, 10));
  if (displayAsset.platforms?.length) meta.push(displayAsset.platforms.join(" / "));
  if (displayAsset.skills?.length) meta.push(displayAsset.skills.join(" / "));
  els.assetMeta.textContent = meta.join("  |  ") || "内容创作资产";
}

function assetLabel(asset) {
  if (asset.tags?.length) return asset.tags.slice(0, 2).join(" / ");
  if (asset.platforms?.length) return asset.platforms.slice(0, 2).join(" / ");
  if (asset.goal) return asset.goal;
  return "内容资产";
}

function renderSessionReview(items = []) {
  sessionReviewQueue = (items || []).filter((item) => item.status === "pending");
  sessionReviewIndex = Math.min(sessionReviewIndex, Math.max(sessionReviewQueue.length - 1, 0));
  updateSessionReviewButton();
}

function updateSessionReviewButton() {
  if (!els.evolutionReviewBtn || !els.evolutionReviewCount) return;
  const count = sessionReviewQueue.length;
  els.evolutionReviewBtn.hidden = count === 0 || currentScreenName !== "chat";
  els.evolutionReviewCount.textContent = String(count);
  els.evolutionReviewBtn.title = count ? `工作方式建议：${count} 条可确认` : "本次没有待确认的工作方式建议";
}

function renderPullRefreshButton() {
  if (!els.refreshFeedBtn) return;
  if (els.refreshFeedBtn.querySelector(".pull-cord")) return;
  els.refreshFeedBtn.classList.add("pull-refresh-button");
  els.refreshFeedBtn.setAttribute("aria-label", "按住下拉换一批灵感");
  els.refreshFeedBtn.title = "按住下拉换一批";
  els.refreshFeedBtn.innerHTML = `
    <span class="pull-cord" aria-hidden="true"><span class="pull-knot"></span></span>
    <span class="pull-label">换一批</span>`;
}

function openSessionReview(index = 0) {
  if (!sessionReviewQueue.length) return showToast("本次没有待确认的工作方式建议");
  sessionReviewIndex = Math.max(0, Math.min(index, sessionReviewQueue.length - 1));
  renderSessionReviewModal();
  els.applyEvolutionModal.classList.add("open");
  els.applyEvolutionModal.setAttribute("aria-hidden", "false");
}

function renderSessionReviewModal() {
  const item = sessionReviewQueue[sessionReviewIndex];
  if (!item) return closeModal("applyEvolutionModal");
  pendingReviewItemId = item.item_id || "";
  els.evolutionReviewCounter.textContent = `${sessionReviewIndex + 1} / ${sessionReviewQueue.length}`;
  els.evolutionReviewTitle.textContent = item.title || reviewTypeLabel(item.source_type);
  els.evolutionReviewBody.textContent = item.suggestion || "这次创作里有一条值得复盘的协作方式问题。";
  els.evolutionReviewScope.textContent = `作用范围：${scopeLabel(item.suggested_scope || "project")}`;
  els.evolutionReviewImpact.textContent = `可能影响：${item.impact || "只用于改进 EcRoom 的协作方式，不保存为你的个人偏好。"}`;
  els.evolutionReviewTech.textContent = reviewTechnicalText(item);
  els.ignoreEvolutionBtn.textContent = item.skip_label || "跳过";
  els.confirmApplyEvolutionBtn.textContent = item.accept_label || "允许这样调整";
}

function reviewTypeLabel(sourceType) {
  const labels = {
    memory: "旧版偏好记录",
    project_rule: "旧版项目规则",
    assistant_workflow: "调整助理工作方式",
  };
  return labels[sourceType] || "工作方式复盘";
}

function reviewTechnicalText(item) {
  const sourceLabel = reviewTypeLabel(item.source_type);
  const lines = [
    `我会把它作为「${sourceLabel}」处理。`,
    `建议来源：${userFacingReviewReason(item)}`,
    `判断依据：${item.evidence_summary || "来自本次创作过程中的检查结果。"}`,
  ];
  if (item.source_type === "assistant_workflow") {
    lines.push(
      item.needs_validation ? "处理方式：先保留为待验证改进点，不会立刻改变所有创作。" : "处理方式：已有验证记录，确认后进入对应工作规则。",
      "你可以跳过；跳过不会删除这次创作，也不会影响作品保存。",
    );
  } else {
    lines.push(
      "处理方式：旧版偏好/规则自动记录已停用，不会再作为新的确认项出现。",
      "你可以跳过；跳过不会影响当前作品。",
    );
  }
  return lines.join("\n");
}

function userFacingReviewReason(item) {
  const reason = String(item.reason || "");
  if (reason.includes("用户给出的约束")) return "这次创作里出现了需要系统更谨慎处理的约束。";
  if (reason.includes("用户在需求") || reason.includes("写作偏好")) return "这次创作里出现了可用于评估协作方式的反馈。";
  if (item.source_type === "assistant_workflow") return "这次创作检查里出现了可改进的协作方式。";
  return reason || "来自这次创作过程中的系统自检信号。";
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" })[char]);
}

function openSkillMenu(anchor) {
  if (currentScreenName === "chat" || !anchor || anchor.hidden) {
    closeSkillMenu();
    return;
  }
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

function setSkillLabels(text = "开始方式") {
  if (els.selectedSkillLabel) els.selectedSkillLabel.textContent = text;
  if (els.inspirationSkillLabel) els.inspirationSkillLabel.textContent = text;
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
  autoResizeTextarea(input);
}

function removeSkillPrompt(input) {
  if (!input) return;
  const previous = input.dataset.skillPrompt || selectedSkill?.prompt || "";
  if (previous && input.value.includes(previous)) {
    input.value = input.value.replace(previous, "").replace(/\n{3,}/g, "\n\n").trimStart();
  }
  input.dataset.skillPrompt = "";
  autoResizeTextarea(input);
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
  renderSessionReview([]);
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
  const runtime = data.runtime_llm || {};
  if (els.modelRuntimeStatus) {
    els.modelRuntimeStatus.textContent = runtime.enabled
      ? `${runtime.provider || llm.provider || "已连接"} / ${runtime.model || llm.model || "默认模型"}`
      : `本地兜底模式${runtime.error ? `：${runtime.error}` : ""}`;
  }
  const memory = data.memory_policy || {};
  if (els.memoryCandidateLimit) els.memoryCandidateLimit.value = memory.candidate_limit ?? 3;
  if (els.memoryMinConfidence) els.memoryMinConfidence.value = memory.min_confidence ?? 0.35;
  if (els.memoryCompleteOnly) els.memoryCompleteOnly.checked = memory.complete_only !== false;
  const harness = data.harness || {};
  if (els.harnessAutoPropose) els.harnessAutoPropose.checked = harness.auto_propose !== false;
  if (els.harnessRecordSkillRuns) els.harnessRecordSkillRuns.checked = harness.record_skill_runs !== false;
  if (els.harnessMinEvalCases) els.harnessMinEvalCases.value = harness.min_eval_cases ?? 3;
  const profile = data.profile || {};
  currentProfile = {
    nickname: String(profile.nickname || "创作者").trim() || "创作者",
    bio: String(profile.bio || "").trim(),
    avatar_data: String(profile.avatar_data || ""),
  };
  setProfileText(profile.nickname || "创作者", profile.bio || "");
  setAvatarPreview(profile.avatar_data || "");
  await Promise.all([loadPreferences(), loadLearnedItems()]);
}

function setProfileText(nickname, bio) {
  const cleanName = String(nickname || "创作者").trim() || "创作者";
  const cleanBio = String(bio || "").trim();
  currentProfile.nickname = cleanName;
  currentProfile.bio = cleanBio;
  els.profilePageNickname.textContent = cleanName;
  els.profilePageBio.textContent = cleanBio || "添加个人简介";
  els.profilePageBio.classList.toggle("is-empty", !cleanBio);
  if (els.profileEditNickname) els.profileEditNickname.value = cleanName;
  if (els.profileEditBio) els.profileEditBio.value = cleanBio;
  updateAuthorDisplays();
}

function authorAvatarSrc() {
  return currentProfile.avatar_data || "/assets/ecroom-icon-64.png";
}

function setAuthorNode(nameNode, avatarNode, label = currentProfile.nickname) {
  if (nameNode) nameNode.textContent = label || "创作者";
  if (avatarNode) avatarNode.src = authorAvatarSrc();
}

function setEcRoomAuthor(nameNode, avatarNode) {
  if (nameNode) nameNode.textContent = "EcRoom";
  if (avatarNode) avatarNode.src = "/assets/ecroom-icon-64.png";
}

function updateAuthorDisplays() {
  setAuthorNode(els.publishPreviewAuthorName, els.publishPreviewAuthorAvatar);
  setAuthorNode(els.assetAuthorName, els.assetAuthorAvatar);
}

function openProfileEdit() {
  els.profileEditNickname.value = els.profilePageNickname.textContent.trim() || "创作者";
  els.profileEditBio.value = els.profilePageBio.classList.contains("is-empty") ? "" : els.profilePageBio.textContent.trim();
  els.profileEditModal.classList.add("open");
  requestAnimationFrame(() => els.profileEditNickname.focus());
}

function closeProfileEdit() {
  els.profileEditModal.classList.remove("open");
}

function setSettingsSection(section, push = true) {
  const normalizedSection = section === "memory" ? "data" : (section || "model");
  const target = document.querySelector(`[data-settings-panel="${normalizedSection}"]`);
  activeSettingsSection = target ? target.dataset.settingsPanel : "model";
  els.settingsNavItems.forEach((item) => item.classList.toggle("active", item.dataset.settingsSection === activeSettingsSection));
  els.settingsPanels.forEach((panel) => panel.classList.toggle("active", panel.dataset.settingsPanel === activeSettingsSection));
  if (push && els.settingsModal.classList.contains("open")) history.pushState({}, "", `/settings/${activeSettingsSection}`);
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
  if (activeSettingsSection === "memory") await loadPreferences();
  showToast("偏好已删除");
}

async function loadLearnedItems() {
  if (!els.learnedList) return;
  const data = await api("/api/learned");
  renderLearnedItems(data.items || []);
}

function renderLearnedItems(items = []) {
  if (!els.learnedList) return;
  els.learnedList.innerHTML = "";
  if (!items.length) {
    els.learnedList.innerHTML = '<div class="empty-row">还没有确认过的系统学习条目。</div>';
    return;
  }
  for (const item of items) {
    const row = document.createElement("article");
    row.className = "learned-row";
    row.innerHTML = `
      <div>
        <span>${escapeHtml(learnedKindLabel(item.kind))}</span>
        <strong>${escapeHtml(item.title || "已学习条目")}</strong>
        <p>${escapeHtml(normalizeCreativeText(item.content || ""))}</p>
        <small>${escapeHtml(item.effect || "这条记录会影响后续 EcRoom 的协作方式。")}</small>
      </div>
      <button class="ghost-button danger-outline-button" type="button" data-learned-id="${escapeHtml(item.item_id || "")}">删除</button>`;
    els.learnedList.appendChild(row);
  }
}

function learnedKindLabel(kind) {
  const labels = {
    evolution: "系统自进化",
    memory_rule: "兼容规则",
  };
  return labels[kind] || "已学习";
}

async function deleteLearnedItem(itemId) {
  if (!itemId) return;
  await api(`/api/learned/${encodeURIComponent(itemId)}`, { method: "DELETE", body: "{}" });
  await loadLearnedItems();
  showToast("已删除学习条目");
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
  if (!els.memoryCandidateLimit || !els.memoryMinConfidence || !els.memoryCompleteOnly) return;
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

async function saveHarnessSettings(event) {
  event.preventDefault();
  if (!els.harnessAutoPropose || !els.harnessRecordSkillRuns || !els.harnessMinEvalCases) return;
  await api("/api/settings", {
    method: "POST",
    body: JSON.stringify({
      harness: {
        auto_propose: els.harnessAutoPropose.checked,
        record_skill_runs: els.harnessRecordSkillRuns.checked,
        min_eval_cases: Number(els.harnessMinEvalCases.value || 3),
      },
    }),
  });
  showToast("工作规则设置已保存");
}

async function saveProfile() {
  const nickname = els.profileEditNickname.value;
  const bio = els.profileEditBio.value;
  await api("/api/settings", { method: "POST", body: JSON.stringify({ profile: { nickname, bio } }) });
  setProfileText(nickname, bio);
  closeProfileEdit();
  showToast("个人资料已保存");
}

function setAvatarPreview(dataUrl) {
  if (!els.profileAvatarImage) return;
  currentProfile.avatar_data = String(dataUrl || "");
  const images = [els.profileAvatarImage, els.profileEditAvatarImage].filter(Boolean);
  const shells = [els.profileAvatarDisplay, els.profileAvatarBtn].filter(Boolean);
  for (const image of images) {
    if (dataUrl) image.src = dataUrl;
    else image.removeAttribute("src");
  }
  for (const shell of shells) shell.classList.toggle("has-image", Boolean(dataUrl));
  updateAuthorDisplays();
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

async function runDataDoctor() {
  try {
    const result = await api("/api/data/doctor");
    const statusText = result.status === "pass" ? "工作区状态正常" : result.status === "warn" ? "有几项需要留意" : "有项目需要处理";
    if (els.dataDoctorStatus) {
      els.dataDoctorStatus.textContent = workspaceDoctorCopy(result);
    }
    showToast(statusText);
  } catch (error) {
    showToast(error.message);
  }
}

async function rebuildIndexes() {
  setBusy(true);
  try {
    await api("/api/data/rebuild-index", { method: "POST", body: "{}" });
    if (els.dataDoctorStatus) {
      els.dataDoctorStatus.textContent = "搜索已重新整理。你的作品正文、偏好和资料内容没有被修改。";
    }
    showToast("搜索已重新整理");
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(false);
  }
}

function workspaceDoctorCopy(result) {
  const issues = Array.isArray(result.issues) ? result.issues : [];
  if (result.status === "pass" || !issues.length) {
    return "没有发现异常。对话、作品、资料和封面引用都可以正常使用。";
  }
  const priority = issues.find((item) => item.severity === "error") || issues[0];
  const code = priority?.code || "";
  const copy = {
    invalid_session_json: "有一条对话记录无法读取，可能需要从历史中删除或恢复备份。",
    missing_session_ref: "有一条历史记录找不到对应对话文件，建议在历史列表中核对。",
    missing_post_media: "有作品封面文件缺失，作品正文仍在，可以重新选择封面。",
    invalid_posts_json: "作品列表文件无法读取，建议先不要继续发布，检查本地数据文件。",
    invalid_memory_jsonl: "偏好记录里有无法读取的内容，建议先导出数据再处理。",
    invalid_knowledge_jsonl: "资料库里有无法读取的内容，建议重新导入相关资料。",
    stale_temp_file: "上次保存可能被中断，已发现临时文件；通常不影响作品正文。",
  };
  return copy[code] || "发现一项需要留意的数据状态。你的作品正文不会被自动修改，可以先导出数据再处理。";
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
  pulseElement(textarea.closest(".composer"), "composer-launch", 620);
  setBusy(true);
  const activeSkill = selectedSkill;
  const capabilityId = activeSkill?.id || "";
  const preferences = "";
  const preview = await getWorkflowPreview(request, preferences, capabilityId);
  const stages = preview.stages?.length ? preview.stages : defaultWorkflowStages(request);
  renderPendingChat(request, { ...preview, stages });
  try {
    const data = await api("/api/session", { method: "POST", body: JSON.stringify({ request, preferences, capability_id: capabilityId, project_id: "default" }) });
    textarea.value = "";
    textarea.dataset.skillPrompt = "";
    autoResizeTextarea(textarea);
    clearSelectedSkill({ input: textarea, removePrompt: false });
    currentSessionId = data.state.session_id;
    await loadSessions();
    await loadAssets();
    await waitForWorkflowMinimum(stages);
    await finishPendingWorkflow(data, stages);
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
  pulseElement(els.feedbackForm, "composer-launch", 520);
  setBusy(true);
  clearSelectedSkill({ removePrompt: false });
  appendMessage("user", note, "反馈");
  const stages = feedbackWorkflowStages();
  appendInlineTyping("正在继续打磨", stages);
  try {
    if (currentSessionCompleted) {
      await api(`/api/session/${currentSessionId}/complete`, {
        method: "POST",
        body: JSON.stringify({ completed: false, revoke_learning: false }),
      });
      currentSessionCompleted = false;
    }
    const data = await api(`/api/session/${currentSessionId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ signal: inferFeedbackSignal(note), note, edited_text: "" }),
    });
    els.feedbackNote.value = "";
    els.feedbackNote.dataset.skillPrompt = "";
    autoResizeTextarea(els.feedbackNote);
    clearSelectedSkill({ input: els.feedbackNote, removePrompt: false });
    await loadSessions();
    await loadAssets();
    await waitForWorkflowMinimum(stages);
    await finishPendingWorkflow(data, stages);
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
  els.deleteModal.setAttribute("aria-hidden", "false");
}

async function acceptCurrentReviewItem() {
  const sessionId = currentSessionId || currentAsset?.session_id;
  if (!sessionId || !pendingReviewItemId) return;
  const itemId = pendingReviewItemId;
  const item = sessionReviewQueue[sessionReviewIndex] || {};
  setBusy(true);
  try {
    const result = await api(`/api/session/${sessionId}/review/${encodeURIComponent(itemId)}/accept`, {
      method: "POST",
      body: JSON.stringify({ scope: item.suggested_scope || "" }),
    });
    markReviewItemHandled(itemId, result.status || "accepted");
    showToast(result.status === "blocked" ? result.message || "已保留为待验证改进点" : acceptedReviewToast(item));
    showNextReviewItem();
  } finally {
    setBusy(false);
  }
}

async function skipCurrentReviewItem() {
  const sessionId = currentSessionId || currentAsset?.session_id;
  if (!sessionId || !pendingReviewItemId) return;
  const itemId = pendingReviewItemId;
  setBusy(true);
  try {
    await api(`/api/session/${sessionId}/review/${encodeURIComponent(itemId)}/skip`, {
      method: "POST",
      body: JSON.stringify({ reviewer_note: "用户在本次复盘中选择跳过。" }),
    });
    markReviewItemHandled(itemId, "skipped");
    showToast("已跳过这条复盘");
    showNextReviewItem();
  } finally {
    setBusy(false);
  }
}

function acceptedReviewToast(item) {
  if (item.source_type === "assistant_workflow") return "已允许这条工作方式调整";
  return "已处理这条旧版复盘项";
}

function markReviewItemHandled(itemId, status) {
  sessionReviewQueue = sessionReviewQueue.filter((item) => item.item_id !== itemId);
  if (currentManifest?.proposals && itemId.includes(":workflow:")) {
    const proposalId = itemId.split(":").pop();
    for (const proposal of currentManifest.proposals) {
      if (proposal.proposal_id === proposalId) proposal.status = status;
    }
  }
  updateSessionReviewButton();
}

function showNextReviewItem() {
  if (!sessionReviewQueue.length) {
    pendingReviewItemId = "";
    closeModal("applyEvolutionModal");
    showToast("本次复盘已处理完");
    return;
  }
  sessionReviewIndex = Math.min(sessionReviewIndex, sessionReviewQueue.length - 1);
  renderSessionReviewModal();
}

async function confirmDelete() {
  if (!pendingDeleteId) return;
  const mode = document.querySelector('input[name="deleteMode"]:checked')?.value || "history";
  const result = await api(`/api/session/${pendingDeleteId}`, { method: "DELETE", body: JSON.stringify({ mode }) });
  const deletedCurrent = pendingDeleteId === currentSessionId;
  pendingDeleteId = "";
  closeModal("deleteModal");
  await loadSessions();
  await loadAssets();
  await loadPosts();
  const revoked = Number(result.revoked_memory_count || 0);
  showToast(mode === "history" ? "已从历史中移除" : `已彻底删除，并清理 ${revoked} 条相关学习记录`);
  if (deletedCurrent) {
    currentSessionId = null;
    showScreen("generate");
  }
}

function closeModal(id) {
  const modal = document.querySelector(`#${id}`);
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}

function bindEvents() {
  [els.request, els.inspirationRequest, els.feedbackNote, els.publishBody].forEach(bindComposerTextarea);
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
  els.assetBackButton.addEventListener("click", backFromAsset);
  els.assetSearch.addEventListener("input", renderAssetsPage);
  els.assetFilterButtons.forEach((button) => button.addEventListener("click", () => {
    activeAssetFilter = button.dataset.assetFilter || "all";
    els.assetFilterButtons.forEach((item) => item.classList.toggle("active", item === button));
    renderAssetsPage();
  }));
  els.feedTabs.forEach((button) => button.addEventListener("click", () => {
    activeFeedCategory = button.dataset.category || "discover";
    inspirationRotation = 0;
    inspirationBatchIndex = 0;
    inspirationRenderedKey = "";
    els.feedTabs.forEach((item) => item.classList.toggle("active", item === button));
    renderInspirationGrid();
  }));
  els.refreshFeedBtn.addEventListener("click", (event) => event.preventDefault());
  els.refreshFeedBtn.addEventListener("pointerdown", beginPullRefresh);
  els.refreshFeedBtn.addEventListener("pointermove", movePullRefresh);
  els.refreshFeedBtn.addEventListener("pointerup", endPullRefresh);
  els.refreshFeedBtn.addEventListener("pointercancel", resetPullRefreshControl);
  els.refreshFeedBtn.addEventListener("lostpointercapture", resetPullRefreshControl);
  els.refreshFeedBtn.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    refreshInspirationBatch();
  });
  els.inspirationGrid.addEventListener("pointermove", updateInspirationParallax);
  els.inspirationGrid.addEventListener("pointerleave", resetInspirationParallax);
  els.inspirationGrid.addEventListener("wheel", handleInspirationWheel, { passive: false });
  els.remixAssetButton.addEventListener("click", () => {
    if (!currentAsset) return;
    clearSelectedSkill({ input: els.request, removePrompt: false });
    els.request.value = currentAsset.iteration_prompt || currentAsset.prompt || "";
    autoResizeTextarea(els.request);
    showScreen("generate");
    history.pushState({}, "", "/#generate");
    pulseElement(els.createForm, "composer-arrive", 680);
    els.request.focus();
  });
  els.openAssetSessionButton.addEventListener("click", () => {
    if (currentAsset?.session_id) openSession(currentAsset.session_id);
  });
  els.publishBackBtn.addEventListener("click", backFromPublish);
  els.publishTitle.addEventListener("input", updatePublishPreview);
  els.publishBody.addEventListener("input", updatePublishPreview);
  els.publishTagInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    addPublishTag(els.publishTagInput.value);
    els.publishTagInput.value = "";
  });
  els.publishCoverBtn.addEventListener("click", () => els.publishCoverInput.click());
  els.publishCoverInput.addEventListener("change", (event) => {
    readPublishCover(event.target.files?.[0]);
    event.target.value = "";
  });
  els.publishDeleteBtn.addEventListener("click", deleteCurrentPost);
  els.publishSaveDraftBtn.addEventListener("click", () => savePublish("draft"));
  els.publishSubmitBtn.addEventListener("click", () => savePublish("published"));
  els.skillButton.addEventListener("click", () => openSkillMenu(els.skillButton));
  els.inspirationSkillButton.addEventListener("click", () => openSkillMenu(els.inspirationSkillButton));
  els.settingsBtn.addEventListener("click", () => openSettings());
  els.closeSettingsBtn.addEventListener("click", closeSettingsModal);
  els.settingsModal.addEventListener("click", (event) => {
    if (event.target === els.settingsModal) closeSettingsModal();
    const go = event.target.closest("[data-settings-go]");
    if (go) setSettingsSection(go.dataset.settingsGo || "model");
    if (event.target.closest("[data-settings-open-assets]")) {
      closeSettingsModal();
      openAssets();
    }
    if (event.target.closest("[data-settings-open-history]")) {
      openHistoryManager();
    }
    if (event.target.closest("[data-settings-open-profile]")) {
      closeSettingsModal();
      openProfile();
    }
  });
  els.closeHistoryManageBtn?.addEventListener("click", closeHistoryManager);
  els.historyManageModal?.addEventListener("click", (event) => {
    if (event.target === els.historyManageModal) closeHistoryManager();
    const openButton = event.target.closest("[data-open-session]");
    if (openButton) {
      closeHistoryManager();
      openSession(openButton.dataset.openSession);
      return;
    }
    const deleteButton = event.target.closest("[data-delete-session]");
    if (deleteButton) showDelete(deleteButton.dataset.deleteSession);
  });
  els.profileBtn.addEventListener("click", () => openProfile());
  els.settingsForm.addEventListener("submit", saveSettings);
  if (els.memoryPolicyForm) els.memoryPolicyForm.addEventListener("submit", saveMemoryPolicy);
  if (els.harnessSettingsForm) els.harnessSettingsForm.addEventListener("submit", saveHarnessSettings);
  if (els.runDataDoctorBtn) els.runDataDoctorBtn.addEventListener("click", runDataDoctor);
  if (els.rebuildIndexBtn) els.rebuildIndexBtn.addEventListener("click", rebuildIndexes);
  els.settingsNavItems.forEach((button) => button.addEventListener("click", () => setSettingsSection(button.dataset.settingsSection)));
  els.profileEditBtn.addEventListener("click", openProfileEdit);
  els.profilePageSaveBtn.addEventListener("click", saveProfile);
  els.cancelProfileEditBtn.addEventListener("click", closeProfileEdit);
  els.cancelProfileEditTextBtn.addEventListener("click", closeProfileEdit);
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
  els.feedSearch.addEventListener("input", () => {
    inspirationRotation = 0;
    inspirationBatchIndex = 0;
    inspirationRenderedKey = "";
    renderInspirationGrid();
  });
  els.collapseSidebarBtn.addEventListener("click", () => els.appFrame.classList.add("history-collapsed"));
  els.expandSidebarBtn.addEventListener("click", () => els.appFrame.classList.remove("history-collapsed"));
  els.testLlmBtn.addEventListener("click", async () => {
    const result = await api("/api/llm/test", { method: "POST", body: "{}" });
    showToast(result.ok ? `${result.provider} 连接成功` : result.message);
  });
  els.messageList.addEventListener("click", async (event) => {
    if (event.target.closest(".draft-complete-button")) await toggleSessionCompleted();
  });
  els.refreshPreferencesBtn?.addEventListener("click", loadPreferences);
  els.preferenceList?.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-preference-id]");
    if (button) await deletePreference(button.dataset.preferenceId);
  });
  els.refreshLearnedBtn?.addEventListener("click", loadLearnedItems);
  els.learnedList?.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-learned-id]");
    if (button) await deleteLearnedItem(button.dataset.learnedId);
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
    if (!event.target.closest(".session-row")) closeSessionMenus();
    if (!event.target.closest(".asset-card-menu-wrap")) closeAssetCardMenus();
  });
  els.sessionList.addEventListener("click", async (event) => {
    const row = event.target.closest(".session-row");
    if (!row) return;
    const sessionId = row.dataset.sessionId;
    const actionButton = event.target.closest("[data-action]");
    if (event.target.closest(".session-menu-button")) {
      event.preventDefault();
      event.stopPropagation();
      const menu = row.querySelector(".session-menu");
      const shouldOpen = !menu.classList.contains("open");
      closeSessionMenus();
      if (shouldOpen) {
        row.classList.add("menu-open");
        menu.classList.add("open");
        menu.setAttribute("aria-hidden", "false");
      }
      return;
    }
    if (actionButton) {
      event.preventDefault();
      event.stopPropagation();
      closeSessionMenus();
      if (actionButton.dataset.action === "pin") await togglePin(sessionId);
      if (actionButton.dataset.action === "rename") showRename(sessionId);
      if (actionButton.dataset.action === "delete") showDelete(sessionId);
      return;
    }
    const openMenu = document.querySelector(".session-menu.open");
    if (openMenu && !row.contains(openMenu)) {
      closeSessionMenus();
      return;
    }
    openSession(sessionId);
  });
  els.cancelRenameBtn.addEventListener("click", () => closeModal("renameModal"));
  els.confirmRenameBtn.addEventListener("click", confirmRename);
  els.cancelDeleteBtn.addEventListener("click", () => closeModal("deleteModal"));
  els.confirmDeleteBtn.addEventListener("click", confirmDelete);
  els.cancelApplyEvolutionBtn.addEventListener("click", () => closeModal("applyEvolutionModal"));
  els.confirmApplyEvolutionBtn.addEventListener("click", acceptCurrentReviewItem);
  els.ignoreEvolutionBtn.addEventListener("click", skipCurrentReviewItem);
  els.evolutionReviewBtn.addEventListener("click", () => openSessionReview());
  els.goPublishBtn.addEventListener("click", publishCurrentWork);
  els.saveWorkOnlyBtn.addEventListener("click", saveWorkOnly);
  els.continueWorkBtn.addEventListener("click", openReopenWorkModal);
  if (els.reopenAndClearLearningBtn) els.reopenAndClearLearningBtn.addEventListener("click", () => continueCurrentWork({ revokeLearning: true }));
  if (els.reopenKeepLearningBtn) els.reopenKeepLearningBtn.addEventListener("click", () => continueCurrentWork({ revokeLearning: false }));
  if (els.cancelReopenWorkBtn) els.cancelReopenWorkBtn.addEventListener("click", closeReopenWorkModal);
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
  const publishMatch = location.pathname.match(/^\/publish\/([^/]+)$/);
  if (publishMatch) return openPublish(publishMatch[1], push);
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
    await loadPosts();
    await bootFromRoute(false);
  } catch (error) {
    showToast(error.message);
  }
}

boot();
