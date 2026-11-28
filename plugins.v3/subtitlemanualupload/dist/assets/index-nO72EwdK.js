import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-pcqpp-6-.js';

true&&(function polyfill() {
  const relList = document.createElement("link").relList;
  if (relList && relList.supports && relList.supports("modulepreload")) {
    return;
  }
  for (const link of document.querySelectorAll('link[rel="modulepreload"]')) {
    processPreload(link);
  }
  new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type !== "childList") {
        continue;
      }
      for (const node of mutation.addedNodes) {
        if (node.tagName === "LINK" && node.rel === "modulepreload")
          processPreload(node);
      }
    }
  }).observe(document, { childList: true, subtree: true });
  function getFetchOpts(link) {
    const fetchOpts = {};
    if (link.integrity) fetchOpts.integrity = link.integrity;
    if (link.referrerPolicy) fetchOpts.referrerPolicy = link.referrerPolicy;
    if (link.crossOrigin === "use-credentials")
      fetchOpts.credentials = "include";
    else if (link.crossOrigin === "anonymous") fetchOpts.credentials = "omit";
    else fetchOpts.credentials = "same-origin";
    return fetchOpts;
  }
  function processPreload(link) {
    if (link.ep)
      return;
    link.ep = true;
    const fetchOpts = getFetchOpts(link);
    fetch(link.href, fetchOpts);
  }
}());

const {createTextVNode:_createTextVNode$1,resolveComponent:_resolveComponent$1,withCtx:_withCtx$1,createVNode:_createVNode$1,toDisplayString:_toDisplayString$1,createElementVNode:_createElementVNode$1,openBlock:_openBlock$2,createElementBlock:_createElementBlock$1,createCommentVNode:_createCommentVNode$1,Fragment:_Fragment$1,renderList:_renderList$1,vModelSelect:_vModelSelect$1,withDirectives:_withDirectives$1,withModifiers:_withModifiers,vModelText:_vModelText$1,createBlock:_createBlock$2} = await importShared('vue');


const _hoisted_1$1 = {
  key: 0,
  role: "status"
};
const _hoisted_2$1 = {
  key: 1,
  class: "error-text",
  role: "alert"
};
const _hoisted_3$1 = {
  key: 2,
  role: "status"
};
const _hoisted_4$1 = { key: 3 };
const _hoisted_5$1 = ["href"];
const _hoisted_6$1 = { key: 0 };
const _hoisted_7$1 = { key: 0 };
const _hoisted_8$1 = ["value", "disabled"];
const _hoisted_9$1 = {
  key: 1,
  class: "upload-tools"
};
const _hoisted_10$1 = ["onUpdate:modelValue"];

const {onMounted: onMounted$1,ref: ref$1} = await importShared('vue');



const _sfc_main$2 = {
  __name: 'MediaDialog',
  props: { row: Object, call: Function },
  emits: ['close', 'changed'],
  setup(__props, { emit: __emit }) {

const props = __props;
const emit = __emit;
const target = ref$1(null), busy = ref$1(false), message = ref$1(''), error = ref$1('');
const file = ref$1(null), member = ref$1(''), members = ref$1([]), role = ref$1('zh-Hans');
const fileInput = ref$1(null), glossary = ref$1(null), metadata = ref$1(null);
const roles = { 'zh-Hans': '简中成品', 'zh-Hant': '繁中成品', 'zh-en': '中英成品', eng: '英文原稿，供 AI 翻译' };

async function act(fn) {
  if (busy.value) return
  busy.value = true;
  error.value = message.value = '';
  try {
    await fn();
  } catch (reason) {
    error.value = reason?.response?.data?.detail || reason?.message || '操作失败';
  } finally {
    busy.value = false;
  }
}

onMounted$1(() => act(async () => {
  target.value = await props.call('post', 'library_target', { id: props.row.id });
}));

function selectFile(event) {
  file.value = event.target.files[0] || null;
  members.value = [];
  member.value = '';
}

function upload() {
  return act(async () => {
    const form = new FormData();
    form.append('target', target.value.target);
    form.append('role', role.value);
    form.append('member', member.value);
    form.append('file', file.value);
    const res = await props.call('post', 'upload', form);
    if (res.members) {
      members.value = res.members;
      message.value = '请选择和当前片源对应的字幕';
    } else {
      message.value = `已上传 ${res.file}（${res.cues} 轴）`;
      file.value = null;
      members.value = [];
      member.value = '';
      if (fileInput.value) fileInput.value.value = '';
      emit('changed');
    }
  })
}

function editMeta() {
  return act(async () => {
    const res = await props.call('get', 'target?id=' + encodeURIComponent(target.value.target));
    metadata.value = { ...res.meta };
  })
}

function saveMeta() {
  return act(async () => {
    await props.call('post', 'metadata', { ...metadata.value, target: target.value.target });
    metadata.value = null;
    message.value = '作品资料已保存';
    emit('changed');
  })
}

function editGlossary() {
  return act(async () => {
    const res = await props.call('get', 'glossary?target=' + encodeURIComponent(target.value.target));
    glossary.value = JSON.stringify(res.glossary, null, 2);
  })
}

function saveGlossary() {
  return act(async () => {
    await props.call('post', 'glossary', { glossary: JSON.parse(glossary.value), target: target.value.target });
    glossary.value = null;
    message.value = '译名表已保存';
  })
}

return (_ctx, _cache) => {
  const _component_VCardTitle = _resolveComponent$1("VCardTitle");
  const _component_VBtn = _resolveComponent$1("VBtn");
  const _component_VCardText = _resolveComponent$1("VCardText");
  const _component_VSpacer = _resolveComponent$1("VSpacer");
  const _component_VCardActions = _resolveComponent$1("VCardActions");
  const _component_VCard = _resolveComponent$1("VCard");
  const _component_VDialog = _resolveComponent$1("VDialog");

  return (_openBlock$2(), _createBlock$2(_component_VDialog, {
    "model-value": true,
    "max-width": "650",
    persistent: busy.value,
    "aria-labelledby": "hyrule-upload",
    "onUpdate:modelValue": _cache[5] || (_cache[5] = open => { if (!open) emit('close'); })
  }, {
    default: _withCtx$1(() => [
      _createVNode$1(_component_VCard, null, {
        default: _withCtx$1(() => [
          _createVNode$1(_component_VCardTitle, { id: "hyrule-upload" }, {
            default: _withCtx$1(() => [...(_cache[6] || (_cache[6] = [
              _createTextVNode$1("上传字幕", -1)
            ]))]),
            _: 1
          }),
          _createVNode$1(_component_VCardText, { class: "upload-body" }, {
            default: _withCtx$1(() => [
              _createElementVNode$1("strong", null, _toDisplayString$1(__props.row.title), 1),
              (busy.value && !target.value)
                ? (_openBlock$2(), _createElementBlock$1("p", _hoisted_1$1, "正在核对影片目录…"))
                : _createCommentVNode$1("", true),
              (error.value)
                ? (_openBlock$2(), _createElementBlock$1("p", _hoisted_2$1, _toDisplayString$1(error.value), 1))
                : _createCommentVNode$1("", true),
              (message.value)
                ? (_openBlock$2(), _createElementBlock$1("p", _hoisted_3$1, _toDisplayString$1(message.value), 1))
                : _createCommentVNode$1("", true),
              (__props.row.directory)
                ? (_openBlock$2(), _createElementBlock$1("p", _hoisted_4$1, [
                    _cache[7] || (_cache[7] = _createElementVNode$1("span", null, "影片目录", -1)),
                    _createElementVNode$1("code", null, _toDisplayString$1(target.value?.directory || __props.row.directory), 1)
                  ]))
                : _createCommentVNode$1("", true),
              _createElementVNode$1("a", {
                href: __props.row.search_url,
                target: "_blank",
                rel: "noopener noreferrer"
              }, "前往 SubHD ↗", 8, _hoisted_5$1),
              (target.value)
                ? (_openBlock$2(), _createElementBlock$1(_Fragment$1, { key: 4 }, [
                    (__props.row.original)
                      ? (_openBlock$2(), _createElementBlock$1("p", _hoisted_6$1, [
                          _createElementVNode$1("span", null, _toDisplayString$1(target.value.folder ? '原盘目录内的外挂，可在播放器手动加载' : '字幕保存到主片旁'), 1),
                          _createElementVNode$1("code", null, [
                            _createTextVNode$1(_toDisplayString$1(target.value.destination), 1),
                            (!target.value.folder)
                              ? (_openBlock$2(), _createElementBlock$1(_Fragment$1, { key: 0 }, [
                                  _createTextVNode$1(" · " + _toDisplayString$1(target.value.file), 1)
                                ], 64))
                              : _createCommentVNode$1("", true)
                          ])
                        ]))
                      : _createCommentVNode$1("", true),
                    _createElementVNode$1("form", {
                      class: "upload-form",
                      onSubmit: _withModifiers(upload, ["prevent"])
                    }, [
                      _createElementVNode$1("label", null, [
                        _cache[8] || (_cache[8] = _createTextVNode$1("字幕文件", -1)),
                        _createElementVNode$1("input", {
                          ref_key: "fileInput",
                          ref: fileInput,
                          type: "file",
                          accept: ".srt,.ass,.ssa,.zip",
                          onChange: selectFile
                        }, null, 544)
                      ]),
                      (members.value.length)
                        ? (_openBlock$2(), _createElementBlock$1("label", _hoisted_7$1, [
                            _cache[10] || (_cache[10] = _createTextVNode$1("压缩包成员 ", -1)),
                            _withDirectives$1(_createElementVNode$1("select", {
                              "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((member).value = $event))
                            }, [
                              _cache[9] || (_cache[9] = _createElementVNode$1("option", {
                                disabled: "",
                                value: ""
                              }, "选择当前片源的字幕", -1)),
                              (_openBlock$2(true), _createElementBlock$1(_Fragment$1, null, _renderList$1(members.value, (name) => {
                                return (_openBlock$2(), _createElementBlock$1("option", { key: name }, _toDisplayString$1(name), 1))
                              }), 128))
                            ], 512), [
                              [_vModelSelect$1, member.value]
                            ])
                          ]))
                        : _createCommentVNode$1("", true),
                      _createElementVNode$1("label", null, [
                        _cache[11] || (_cache[11] = _createTextVNode$1("用途", -1)),
                        _withDirectives$1(_createElementVNode$1("select", {
                          "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((role).value = $event))
                        }, [
                          (_openBlock$2(), _createElementBlock$1(_Fragment$1, null, _renderList$1(roles, (label, value) => {
                            return _createElementVNode$1("option", {
                              key: value,
                              value: value,
                              disabled: __props.row.original && value === 'eng'
                            }, _toDisplayString$1(label), 9, _hoisted_8$1)
                          }), 64))
                        ], 512), [
                          [_vModelSelect$1, role.value]
                        ])
                      ]),
                      _createVNode$1(_component_VBtn, {
                        type: "submit",
                        color: "primary",
                        disabled: busy.value || !file.value || (members.value.length && !member.value)
                      }, {
                        default: _withCtx$1(() => [...(_cache[12] || (_cache[12] = [
                          _createTextVNode$1("上传字幕", -1)
                        ]))]),
                        _: 1
                      }, 8, ["disabled"])
                    ], 32),
                    (!__props.row.original)
                      ? (_openBlock$2(), _createElementBlock$1("div", _hoisted_9$1, [
                          _createVNode$1(_component_VBtn, {
                            size: "small",
                            variant: "text",
                            disabled: busy.value,
                            onClick: editMeta
                          }, {
                            default: _withCtx$1(() => [...(_cache[13] || (_cache[13] = [
                              _createTextVNode$1("作品资料", -1)
                            ]))]),
                            _: 1
                          }, 8, ["disabled"]),
                          _createVNode$1(_component_VBtn, {
                            size: "small",
                            variant: "text",
                            disabled: busy.value,
                            onClick: editGlossary
                          }, {
                            default: _withCtx$1(() => [...(_cache[14] || (_cache[14] = [
                              _createTextVNode$1("本剧译名表", -1)
                            ]))]),
                            _: 1
                          }, 8, ["disabled"])
                        ]))
                      : _createCommentVNode$1("", true),
                    (metadata.value)
                      ? (_openBlock$2(), _createElementBlock$1("form", {
                          key: 2,
                          class: "upload-form",
                          onSubmit: _withModifiers(saveMeta, ["prevent"])
                        }, [
                          (_openBlock$2(), _createElementBlock$1(_Fragment$1, null, _renderList$1({title:'片名',year:'年份',season:'季',episode:'集'}, (label, key) => {
                            return _createElementVNode$1("label", { key: key }, [
                              _createTextVNode$1(_toDisplayString$1(label), 1),
                              _withDirectives$1(_createElementVNode$1("input", {
                                "onUpdate:modelValue": $event => ((metadata.value[key]) = $event)
                              }, null, 8, _hoisted_10$1), [
                                [_vModelText$1, metadata.value[key]]
                              ])
                            ])
                          }), 64)),
                          _createVNode$1(_component_VBtn, {
                            type: "submit",
                            size: "small",
                            disabled: busy.value
                          }, {
                            default: _withCtx$1(() => [...(_cache[15] || (_cache[15] = [
                              _createTextVNode$1("保存资料", -1)
                            ]))]),
                            _: 1
                          }, 8, ["disabled"])
                        ], 32))
                      : _createCommentVNode$1("", true),
                    (glossary.value !== null)
                      ? (_openBlock$2(), _createElementBlock$1("form", {
                          key: 3,
                          class: "upload-form",
                          onSubmit: _withModifiers(saveGlossary, ["prevent"])
                        }, [
                          _createElementVNode$1("label", null, [
                            _cache[16] || (_cache[16] = _createTextVNode$1("译名表 JSON", -1)),
                            _withDirectives$1(_createElementVNode$1("textarea", {
                              "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((glossary).value = $event)),
                              rows: "8"
                            }, null, 512), [
                              [_vModelText$1, glossary.value]
                            ])
                          ]),
                          _createElementVNode$1("label", null, [
                            _cache[17] || (_cache[17] = _createTextVNode$1("从文件导入", -1)),
                            _createElementVNode$1("input", {
                              type: "file",
                              accept: ".json",
                              onChange: _cache[3] || (_cache[3] = e => act(async () => {
              if (e.target.files[0]) glossary.value = await e.target.files[0].text();
            }))
                            }, null, 32)
                          ]),
                          _createVNode$1(_component_VBtn, {
                            type: "submit",
                            size: "small",
                            disabled: busy.value
                          }, {
                            default: _withCtx$1(() => [...(_cache[18] || (_cache[18] = [
                              _createTextVNode$1("保存译名表", -1)
                            ]))]),
                            _: 1
                          }, 8, ["disabled"])
                        ], 32))
                      : _createCommentVNode$1("", true)
                  ], 64))
                : _createCommentVNode$1("", true)
            ]),
            _: 1
          }),
          _createVNode$1(_component_VCardActions, null, {
            default: _withCtx$1(() => [
              _createVNode$1(_component_VSpacer),
              _createVNode$1(_component_VBtn, {
                variant: "text",
                disabled: busy.value,
                onClick: _cache[4] || (_cache[4] = $event => (emit('close')))
              }, {
                default: _withCtx$1(() => [...(_cache[19] || (_cache[19] = [
                  _createTextVNode$1("关闭", -1)
                ]))]),
                _: 1
              }, 8, ["disabled"])
            ]),
            _: 1
          })
        ]),
        _: 1
      })
    ]),
    _: 1
  }, 8, ["persistent"]))
}
}

};
const MediaDialog = /*#__PURE__*/_export_sfc(_sfc_main$2, [['__scopeId',"data-v-8bc99dfc"]]);

const {createElementVNode:_createElementVNode,createTextVNode:_createTextVNode,resolveComponent:_resolveComponent,withCtx:_withCtx,createVNode:_createVNode,openBlock:_openBlock$1,createElementBlock:_createElementBlock,createCommentVNode:_createCommentVNode,toDisplayString:_toDisplayString,vModelText:_vModelText,withDirectives:_withDirectives,vModelSelect:_vModelSelect,createBlock:_createBlock$1,renderList:_renderList,Fragment:_Fragment,vModelCheckbox:_vModelCheckbox,normalizeClass:_normalizeClass,resolveDynamicComponent:_resolveDynamicComponent,vModelRadio:_vModelRadio} = await importShared('vue');


const _hoisted_1 = {
  key: 0,
  class: "dashboard-head"
};
const _hoisted_2 = {
  key: 1,
  class: "toolbar"
};
const _hoisted_3 = { class: "heading" };
const _hoisted_4 = { key: 0 };
const _hoisted_5 = { class: "search" };
const _hoisted_6 = { class: "tools" };
const _hoisted_7 = { class: "tool-label" };
const _hoisted_8 = {
  key: 0,
  class: "filters",
  "aria-label": "筛选片源和任务"
};
const _hoisted_9 = {
  key: 1,
  class: "batch",
  role: "group",
  "aria-label": "批量管理任务"
};
const _hoisted_10 = {
  key: 2,
  class: "feedback",
  role: "status"
};
const _hoisted_11 = {
  key: 3,
  class: "feedback error-text",
  role: "alert"
};
const _hoisted_12 = {
  key: 4,
  class: "feedback",
  role: "status"
};
const _hoisted_13 = {
  key: 5,
  class: "empty"
};
const _hoisted_14 = { class: "cards" };
const _hoisted_15 = {
  key: 0,
  class: "pick"
};
const _hoisted_16 = ["value", "aria-label"];
const _hoisted_17 = { class: "body" };
const _hoisted_18 = { class: "title" };
const _hoisted_19 = ["title"];
const _hoisted_20 = {
  key: 0,
  class: "badges"
};
const _hoisted_21 = {
  key: 1,
  class: "path"
};
const _hoisted_22 = {
  key: 2,
  class: "path"
};
const _hoisted_23 = { class: "meta" };
const _hoisted_24 = { key: 0 };
const _hoisted_25 = { key: 1 };
const _hoisted_26 = { key: 4 };
const _hoisted_27 = { key: 0 };
const _hoisted_28 = { key: 1 };
const _hoisted_29 = { key: 2 };
const _hoisted_30 = ["href"];
const _hoisted_31 = { class: "actions" };
const _hoisted_32 = {
  key: 6,
  class: "pages",
  "aria-label": "片源分页"
};
const _hoisted_33 = { class: "path" };
const _hoisted_34 = {
  key: 0,
  class: "error-text",
  role: "alert"
};
const _hoisted_35 = {
  role: "radiogroup",
  "aria-label": "Emby 英文字幕候选"
};
const _hoisted_36 = ["value", "disabled"];

const {computed,onBeforeUnmount,onMounted,ref,watch} = await importShared('vue');


const _sfc_main$1 = {
  __name: 'Page',
  props: {
  api: Object,
  pluginId: { type: String, default: 'SubtitleManualUpload' },
  show_switch: { type: Boolean, default: true },
  show_close: { type: Boolean, default: true },
  compact: Boolean,
  allowRefresh: { type: Boolean, default: true },
},
  emits: ['close', 'switch'],
  setup(__props, { emit: __emit }) {

const props = __props;
const emit = __emit;
const filters = {
  all: ['全部', 'primary'], recent: ['最近入库', 'primary'], present: ['已有中文', 'success'], missing: ['缺中文', 'warning'],
  unknown: ['待确认', 'default'], disc: ['原盘', 'secondary'],
  queued: ['等待', 'info'], running: ['处理中', 'warning'], done: ['已完成', 'success'],
  failed: ['失败', 'error'], cancelled: ['已取消', 'default'], skipped: ['已跳过', 'default'],
};
const actions = {
  cancel: { label: '取消', color: 'warning', result: '已提交取消请求' },
  restart: { label: '重新生成', color: 'primary', result: '已提交重新生成' },
  delete: { label: '删除', color: 'error', result: '已删除任务记录' },
};
const data = ref({ rows: [], counts: {}, matches: 0, page_size: 50 });
const query = ref(''), filter = ref(props.compact ? 'recent' : 'all');
const kind = ref(props.compact ? 'Movie' : 'all'), order = ref('desc'), offset = ref(0);
const selected = ref([]), pending = ref(null), upload = ref(null), history = ref(null);
const englishOptions = ref(null), englishIndex = ref(null), aiPending = ref('');
const loading = ref(false), busy = ref(false), loadError = ref(''), actionError = ref(''), notice = ref('');
const selectable = computed(() => data.value.rows.filter(row => row.task).map(row => row.task.id));
const picked = computed(() => data.value.rows.filter(row => row.task && selected.value.includes(row.task.id)));
const allPicked = computed(() => selectable.value.length > 0 && selected.value.length === selectable.value.length);
const visibleRows = computed(() => props.compact ? data.value.rows.slice(0, 3) : data.value.rows);
const searchPage = computed(() => '#/plugin-app/' + encodeURIComponent(props.pluginId) + '/main');
let requestNumber = 0;
let timer, debounce;

async function call(method, endpoint, body) {
  const response = await props.api[method](`plugin/${props.pluginId}/${endpoint}`, body);
  const payload = response?.data ?? response;
  if (response?.success === false || payload?.success === false)
    throw new Error(payload?.message || response?.message || '操作失败')
  return payload?.data ?? payload
}

function errorText(error) {
  return error?.response?.data?.detail || error?.message || '无法访问字幕插件'
}

async function load() {
  const number = ++requestNumber;
  loading.value = true;
  try {
    const params = new URLSearchParams({ q: query.value, state: filter.value, kind: kind.value, order: order.value, offset: offset.value });
    const result = await call('get', 'library_page?' + params);
    if (number !== requestNumber) return
    if (offset.value && !result.rows.length) {
      offset.value = 0;
      return load()
    }
    data.value = result;
    selected.value = selected.value.filter(id => selectable.value.includes(id));
    loadError.value = result.error || result.history_error || '';
  } catch (error) {
    if (number === requestNumber) loadError.value = errorText(error);
  } finally {
    if (number === requestNumber) loading.value = false;
  }
}

function select(state, direction = order.value, from = 0) {
  clearTimeout(debounce);
  filter.value = state;
  order.value = direction;
  offset.value = from;
  selected.value = [];
  load();
}

function active(job) {
  return job?.state === 'queued' || job?.state === 'running'
}

function can(action, row) {
  const job = row.task;
  if (!job) return false
  if (action === 'cancel') return active(job) && !job.cancelling && !job.publishing
  if (action === 'restart') return !row.original && row.available && !active(job)
  return !active(job)
}

async function act(fn) {
  if (busy.value) return
  busy.value = true;
  actionError.value = notice.value = '';
  try {
    await fn();
  } catch (error) {
    actionError.value = errorText(error);
  } finally {
    busy.value = false;
  }
}

function request(action, rows) {
  const ids = rows.filter(row => can(action, row)).map(row => row.task.id);
  if (!ids.length) return
  if (action === 'cancel') return perform({ action, ids })
  pending.value = { action, ids };
}

function perform(operation) {
  pending.value = null;
  return act(async () => {
    const result = await call('post', 'task_actions', operation);
    const skipped = result.skipped.map(item => `#${item.id} ${item.reason}`);
    notice.value = actions[operation.action].result + ` ${result.changed.length} 条`;
    if (skipped.length) notice.value += `，跳过 ${skipped.length} 条（${skipped.slice(0, 3).join('、')}）`;
    selected.value = [];
    await load();
  })
}

function generate(row) {
  if (row.task && (row.task.state !== 'failed' || row.task.legacy)) return request('restart', [row])
  return submitAi(row)
}

function submitAi(row, choice) {
  return act(async () => {
    aiPending.value = row.id;
    try {
      const source = choice ? { english_choice: choice } : { find_english: true };
      const result = await call('post', 'ai_submit', { target_ids: [row.id], ...source });
      if (result.english_options) {
        englishIndex.value = null;
        englishOptions.value = { row, ...result.english_options };
        return
      }
      englishOptions.value = null;
      const id = result.tasks?.[0]?.id;
      notice.value = result.source_notice || (id ? `任务 #${id} 已进入队列` : '已提交 AI 字幕任务');
      await load();
    } finally {
      aiPending.value = '';
    }
  })
}

function translateEnglish() {
  const options = englishOptions.value;
  if (options && englishIndex.value !== null) {
    return submitAi(options.row, { token: options.token, index: englishIndex.value })
  }
}

function refresh() {
  return act(async () => {
    await call('post', 'refresh', {});
    await call('post', 'inventory_scan', {});
    await load();
  })
}

function loadHistory(row, at = 0) {
  return act(async () => {
    const result = await call('get', `task_page?target=${encodeURIComponent(row.target)}&offset=${at}`);
    history.value = { row, at, ...result };
  })
}

function aiLabel(row) {
  if (active(row.task)) return row.task.state === 'queued' ? '已排队' : '生成中'
  if (row.task?.state === 'failed' && !row.task.legacy) return '从断点重试'
  return row.task ? '重新生成' : 'AI 生成'
}

function badges(row) {
  const result = [];
  const job = row.task;
  const source = job?.report?.source || '';
  const files = job?.report?.files || [];
  if (row.original) result.push(['原盘', 'secondary']);
  const scripts = row.chinese_scripts ?? [];
  if (scripts.includes('hans')) result.push(['内嵌简中', 'var(--embedded-chinese-color)']);
  if (scripts.includes('hant')) result.push(['内嵌繁中', 'var(--embedded-chinese-color)']);
  if (!scripts.length && (row.chinese.includes('embedded') || /内封|内嵌/.test(source)))
    result.push(['视频内嵌字幕', 'info']);
  if (row.chinese.includes('external')) result.push(['外挂中文', 'success']);
  if (job?.state === 'done' && (files.some(f => f.endsWith('.zh-en.ai.ass')) && files.some(f => f.endsWith('.zh-en.ai.srt'))
      || /生成双语 ASS 和 SRT/.test(job.detail))) result.push(['已生成双语 ASS 和 SRT', 'success']);
  if (job?.state === 'failed' && /缺少英文字幕|无英文字幕|没有英文字幕|未提取到可用外挂/.test(job.detail))
    result.push(['缺少英文字幕', 'warning']);
  if (row.status === 'missing') result.push(['缺中文字幕', 'warning']);
  if (row.status === 'unknown' && row.emby) result.push(['字幕待确认', 'default']);
  return result
}

function when(value, utc = false) {
  const date = new Date(utc ? value.replace(' ', 'T') + 'Z' : value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

watch(query, () => {
  clearTimeout(debounce);
  debounce = setTimeout(() => select(filter.value), 230);
});
onMounted(() => {
  load();
  timer = setInterval(() => {
    if (props.allowRefresh && !document.hidden && !busy.value && !loading.value && !pending.value && !upload.value && !history.value && !englishOptions.value) load();
  }, props.compact ? 30000 : 7000);
});
onBeforeUnmount(() => { ++requestNumber; clearInterval(timer); clearTimeout(debounce); });

return (_ctx, _cache) => {
  const _component_VBtn = _resolveComponent("VBtn");
  const _component_VIcon = _resolveComponent("VIcon");
  const _component_VChip = _resolveComponent("VChip");
  const _component_VCardTitle = _resolveComponent("VCardTitle");
  const _component_VCardText = _resolveComponent("VCardText");
  const _component_VSpacer = _resolveComponent("VSpacer");
  const _component_VCardActions = _resolveComponent("VCardActions");
  const _component_VCard = _resolveComponent("VCard");
  const _component_VDialog = _resolveComponent("VDialog");

  return (_openBlock$1(), _createElementBlock("div", {
    class: _normalizeClass(["records", { compact: __props.compact }])
  }, [
    (__props.compact)
      ? (_openBlock$1(), _createElementBlock("header", _hoisted_1, [
          _cache[22] || (_cache[22] = _createElementVNode("h2", null, "海拉鲁 AI 字幕", -1)),
          _createVNode(_component_VBtn, {
            size: "small",
            variant: "text",
            color: "primary",
            href: searchPage.value,
            "prepend-icon": "mdi-magnify"
          }, {
            default: _withCtx(() => [...(_cache[21] || (_cache[21] = [
              _createTextVNode("搜索片库", -1)
            ]))]),
            _: 1
          }, 8, ["href"])
        ]))
      : (_openBlock$1(), _createElementBlock("header", _hoisted_2, [
          _createElementVNode("div", _hoisted_3, [
            _cache[23] || (_cache[23] = _createElementVNode("h2", null, "海拉鲁 AI 字幕", -1)),
            (data.value.model)
              ? (_openBlock$1(), _createElementBlock("p", _hoisted_4, _toDisplayString(data.value.model) + " · " + _toDisplayString(data.value.effort), 1))
              : _createCommentVNode("", true)
          ]),
          _createElementVNode("div", _hoisted_5, [
            _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((query).value = $event)),
              type: "search",
              autocomplete: "off",
              "aria-label": "搜索最近入库和 Emby 片库",
              placeholder: "搜索片库"
            }, null, 512), [
              [_vModelText, query.value]
            ]),
            _withDirectives(_createElementVNode("select", {
              "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((kind).value = $event)),
              "aria-label": "筛选媒体类型",
              onChange: _cache[2] || (_cache[2] = $event => (select(filter.value)))
            }, [...(_cache[24] || (_cache[24] = [
              _createElementVNode("option", { value: "all" }, "全部类型", -1),
              _createElementVNode("option", { value: "Movie" }, "电影", -1),
              _createElementVNode("option", { value: "Episode" }, "剧集", -1)
            ]))], 544), [
              [_vModelSelect, kind.value]
            ])
          ]),
          _createElementVNode("div", _hoisted_6, [
            _createVNode(_component_VBtn, {
              class: "toolbar-action",
              size: "small",
              color: "primary",
              variant: "tonal",
              disabled: busy.value,
              "aria-label": order.value === 'desc' ? '最新在前' : '最早在前',
              title: order.value === 'desc' ? '最新在前' : '最早在前',
              onClick: _cache[3] || (_cache[3] = $event => (select(filter.value, order.value === 'desc' ? 'asc' : 'desc')))
            }, {
              default: _withCtx(() => [
                _createVNode(_component_VIcon, {
                  icon: order.value === 'desc' ? 'mdi-sort-calendar-descending' : 'mdi-sort-calendar-ascending'
                }, null, 8, ["icon"]),
                _createElementVNode("span", _hoisted_7, _toDisplayString(order.value === 'desc' ? '最新在前' : '最早在前'), 1)
              ]),
              _: 1
            }, 8, ["disabled", "aria-label", "title"]),
            _createVNode(_component_VBtn, {
              class: "toolbar-action",
              size: "small",
              color: "primary",
              variant: "tonal",
              disabled: busy.value || data.value.scanning,
              "aria-label": "刷新片库",
              title: "刷新片库",
              onClick: refresh
            }, {
              default: _withCtx(() => [
                _createVNode(_component_VIcon, { icon: "mdi-refresh" }),
                _cache[25] || (_cache[25] = _createElementVNode("span", { class: "tool-label" }, "刷新片库", -1))
              ]),
              _: 1
            }, 8, ["disabled"]),
            (__props.show_switch)
              ? (_openBlock$1(), _createBlock$1(_component_VBtn, {
                  key: 0,
                  icon: "mdi-cog-outline",
                  size: "small",
                  variant: "text",
                  "aria-label": "插件设置",
                  onClick: _cache[4] || (_cache[4] = $event => (emit('switch')))
                }))
              : _createCommentVNode("", true),
            (__props.show_close)
              ? (_openBlock$1(), _createBlock$1(_component_VBtn, {
                  key: 1,
                  icon: "mdi-close",
                  size: "small",
                  variant: "text",
                  "aria-label": "关闭",
                  onClick: _cache[5] || (_cache[5] = $event => (emit('close')))
                }))
              : _createCommentVNode("", true)
          ])
        ])),
    (_openBlock$1(), _createBlock$1(_resolveDynamicComponent(__props.compact ? 'div' : 'main'), { class: "content" }, {
      default: _withCtx(() => [
        (!__props.compact)
          ? (_openBlock$1(), _createElementBlock("nav", _hoisted_8, [
              (_openBlock$1(), _createElementBlock(_Fragment, null, _renderList(filters, ([label, color], state) => {
                return _createVNode(_component_VChip, {
                  key: state,
                  tag: "button",
                  type: "button",
                  size: "small",
                  color: color,
                  variant: filter.value === state ? 'flat' : 'tonal',
                  "aria-pressed": filter.value === state,
                  onClick: $event => (select(state))
                }, {
                  default: _withCtx(() => [
                    _createTextVNode(_toDisplayString(label) + " " + _toDisplayString(data.value.counts[state] || 0), 1)
                  ]),
                  _: 2
                }, 1032, ["color", "variant", "aria-pressed", "onClick"])
              }), 64))
            ]))
          : _createCommentVNode("", true),
        (!__props.compact && selectable.value.length)
          ? (_openBlock$1(), _createElementBlock("div", _hoisted_9, [
              _createVNode(_component_VBtn, {
                size: "small",
                variant: "text",
                disabled: busy.value,
                onClick: _cache[6] || (_cache[6] = $event => (selected.value = allPicked.value ? [] : [...selectable.value]))
              }, {
                default: _withCtx(() => [
                  _createTextVNode(_toDisplayString(allPicked.value ? '取消全选' : '全选本页任务'), 1)
                ]),
                _: 1
              }, 8, ["disabled"]),
              (picked.value.length)
                ? (_openBlock$1(), _createElementBlock(_Fragment, { key: 0 }, _renderList(actions, (spec, action) => {
                    return _createVNode(_component_VBtn, {
                      key: action,
                      size: "small",
                      variant: "tonal",
                      color: spec.color,
                      disabled: busy.value || !picked.value.some(row => can(action, row)),
                      onClick: $event => (request(action, picked.value))
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode("批量" + _toDisplayString(spec.label), 1)
                      ]),
                      _: 2
                    }, 1032, ["color", "disabled", "onClick"])
                  }), 64))
                : _createCommentVNode("", true)
            ]))
          : _createCommentVNode("", true),
        (!__props.compact && data.value.scanning)
          ? (_openBlock$1(), _createElementBlock("p", _hoisted_10, _toDisplayString(data.value.progress || '正在读取 Emby 片库…'), 1))
          : _createCommentVNode("", true),
        (loadError.value || actionError.value)
          ? (_openBlock$1(), _createElementBlock("p", _hoisted_11, _toDisplayString(actionError.value || loadError.value), 1))
          : _createCommentVNode("", true),
        (notice.value)
          ? (_openBlock$1(), _createElementBlock("p", _hoisted_12, _toDisplayString(notice.value), 1))
          : _createCommentVNode("", true),
        (!visibleRows.value.length && !loadError.value)
          ? (_openBlock$1(), _createElementBlock("p", _hoisted_13, _toDisplayString(loading.value ? '正在读取…' : __props.compact ? '暂无最近入库电影' : '当前筛选没有片源'), 1))
          : _createCommentVNode("", true),
        _createElementVNode("div", _hoisted_14, [
          (_openBlock$1(true), _createElementBlock(_Fragment, null, _renderList(visibleRows.value, (row) => {
            return (_openBlock$1(), _createElementBlock("article", {
              key: row.id,
              class: _normalizeClass(["task", { marked: selected.value.includes(row.task?.id) }])
            }, [
              (!__props.compact)
                ? (_openBlock$1(), _createElementBlock("label", _hoisted_15, [
                    (row.task)
                      ? _withDirectives((_openBlock$1(), _createElementBlock("input", {
                          key: 0,
                          "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => ((selected).value = $event)),
                          type: "checkbox",
                          value: row.task.id,
                          "aria-label": '选择任务 ' + row.title
                        }, null, 8, _hoisted_16)), [
                          [_vModelCheckbox, selected.value]
                        ])
                      : _createCommentVNode("", true)
                  ]))
                : _createCommentVNode("", true),
              _createElementVNode("div", _hoisted_17, [
                _createElementVNode("div", _hoisted_18, [
                  _createElementVNode("strong", {
                    title: __props.compact ? row.title || row.file : undefined
                  }, _toDisplayString(row.title || row.file), 9, _hoisted_19),
                  (row.task)
                    ? (_openBlock$1(), _createBlock$1(_component_VChip, {
                        key: 0,
                        class: "row-state",
                        size: "x-small",
                        variant: "tonal",
                        color: filters[row.task.state]?.[1]
                      }, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(row.task.cancelling ? '取消中' : filters[row.task.state]?.[0]), 1)
                        ]),
                        _: 2
                      }, 1032, ["color"]))
                    : _createCommentVNode("", true)
                ]),
                (!__props.compact)
                  ? (_openBlock$1(), _createElementBlock(_Fragment, { key: 0 }, [
                      (badges(row).length)
                        ? (_openBlock$1(), _createElementBlock("div", _hoisted_20, [
                            (_openBlock$1(true), _createElementBlock(_Fragment, null, _renderList(badges(row), ([label,color]) => {
                              return (_openBlock$1(), _createBlock$1(_component_VChip, {
                                key: label,
                                size: "small",
                                variant: "tonal",
                                color: color
                              }, {
                                default: _withCtx(() => [
                                  _createTextVNode(_toDisplayString(label), 1)
                                ]),
                                _: 2
                              }, 1032, ["color"]))
                            }), 128))
                          ]))
                        : _createCommentVNode("", true),
                      (row.original && row.directory)
                        ? (_openBlock$1(), _createElementBlock("div", _hoisted_21, "影片目录 " + _toDisplayString(row.directory), 1))
                        : (row.file)
                          ? (_openBlock$1(), _createElementBlock("div", _hoisted_22, _toDisplayString(row.file), 1))
                          : _createCommentVNode("", true),
                      _createElementVNode("div", _hoisted_23, [
                        _createElementVNode("span", null, _toDisplayString(row.recent ? 'MoviePilot 入库' : '') + _toDisplayString(row.recent && row.emby ? ' · ' : '') + _toDisplayString(row.emby ? 'Emby' : ''), 1),
                        (row.added)
                          ? (_openBlock$1(), _createElementBlock("time", _hoisted_24, _toDisplayString(when(row.added)), 1))
                          : _createCommentVNode("", true),
                        (row.task?.origin)
                          ? (_openBlock$1(), _createElementBlock("span", _hoisted_25, _toDisplayString(row.task.origin), 1))
                          : _createCommentVNode("", true)
                      ]),
                      (row.reason || row.task?.detail)
                        ? (_openBlock$1(), _createElementBlock("p", {
                            key: 3,
                            class: _normalizeClass(["detail", { 'error-text': row.task?.state === 'failed' }])
                          }, _toDisplayString(row.task?.detail || row.reason), 3))
                        : _createCommentVNode("", true),
                      (row.task)
                        ? (_openBlock$1(), _createElementBlock("details", _hoisted_26, [
                            _createElementVNode("summary", null, "任务 #" + _toDisplayString(row.task.id) + " · 字幕与审校记录", 1),
                            (row.task.report.source)
                              ? (_openBlock$1(), _createElementBlock("p", _hoisted_27, _toDisplayString(row.task.report.source), 1))
                              : _createCommentVNode("", true),
                            (row.task.report.translation_mode === 'embedded_chinese')
                              ? (_openBlock$1(), _createElementBlock("p", _hoisted_28, " 英文复用 " + _toDisplayString(row.task.report.existing_english || 0) + " 条 · AI 补齐 " + _toDisplayString(row.task.report.generated_english || 0) + " 条 ", 1))
                              : _createCommentVNode("", true),
                            (row.task.created)
                              ? (_openBlock$1(), _createElementBlock("p", _hoisted_29, [
                                  _createTextVNode(_toDisplayString(when(row.task.created, true)), 1),
                                  (row.task.finished)
                                    ? (_openBlock$1(), _createElementBlock(_Fragment, { key: 0 }, [
                                        _createTextVNode(" · 完成 " + _toDisplayString(when(row.task.finished, true)), 1)
                                      ], 64))
                                    : _createCommentVNode("", true)
                                ]))
                              : _createCommentVNode("", true),
                            (_openBlock$1(true), _createElementBlock(_Fragment, null, _renderList(row.task.report.files, (file) => {
                              return (_openBlock$1(), _createElementBlock("p", { key: file }, _toDisplayString(file), 1))
                            }), 128)),
                            (_openBlock$1(true), _createElementBlock(_Fragment, null, _renderList(row.task.report.warnings, (issues, id) => {
                              return (_openBlock$1(), _createElementBlock("p", { key: id }, "第 " + _toDisplayString(id) + " 轴 · " + _toDisplayString(issues.join('、')), 1))
                            }), 128)),
                            (_openBlock$1(true), _createElementBlock(_Fragment, null, _renderList(row.task.report.ambiguities, (item) => {
                              return (_openBlock$1(), _createElementBlock("p", {
                                key: item.id
                              }, "第 " + _toDisplayString(item.id) + " 轴 · " + _toDisplayString(item.options.join(' / ')) + " · " + _toDisplayString(item.reason), 1))
                            }), 128)),
                            (_openBlock$1(true), _createElementBlock(_Fragment, null, _renderList(row.task.report.sources, (url) => {
                              return (_openBlock$1(), _createElementBlock("div", { key: url }, [
                                (/^https?:\/\//i.test(url))
                                  ? (_openBlock$1(), _createElementBlock("a", {
                                      key: 0,
                                      href: url,
                                      target: "_blank",
                                      rel: "noopener noreferrer"
                                    }, _toDisplayString(url), 9, _hoisted_30))
                                  : _createCommentVNode("", true)
                              ]))
                            }), 128)),
                            (row.task_count > 1)
                              ? (_openBlock$1(), _createBlock$1(_component_VBtn, {
                                  key: 3,
                                  size: "small",
                                  variant: "text",
                                  onClick: $event => (loadHistory(row))
                                }, {
                                  default: _withCtx(() => [
                                    _createTextVNode("历史任务 " + _toDisplayString(row.task_count), 1)
                                  ]),
                                  _: 2
                                }, 1032, ["onClick"]))
                              : _createCommentVNode("", true)
                          ]))
                        : _createCommentVNode("", true)
                    ], 64))
                  : _createCommentVNode("", true)
              ]),
              _createElementVNode("div", _hoisted_31, [
                _createVNode(_component_VBtn, {
                  class: "quick-action",
                  size: "small",
                  variant: "tonal",
                  href: row.search_url,
                  target: "_blank",
                  rel: "noopener noreferrer"
                }, {
                  default: _withCtx(() => [
                    _createTextVNode("SubHD" + _toDisplayString(__props.compact ? '' : ' ↗'), 1)
                  ]),
                  _: 1
                }, 8, ["href"]),
                _createVNode(_component_VBtn, {
                  class: "quick-action",
                  size: "small",
                  variant: "tonal",
                  color: "primary",
                  disabled: busy.value,
                  onClick: $event => (upload.value = row)
                }, {
                  default: _withCtx(() => [...(_cache[26] || (_cache[26] = [
                    _createTextVNode("上传", -1)
                  ]))]),
                  _: 1
                }, 8, ["disabled", "onClick"]),
                (!row.original)
                  ? (_openBlock$1(), _createBlock$1(_component_VBtn, {
                      key: 0,
                      class: "quick-action",
                      size: "small",
                      variant: "tonal",
                      color: "primary",
                      "aria-label": aiLabel(row),
                      title: __props.compact ? aiLabel(row) : undefined,
                      loading: aiPending.value === row.id,
                      disabled: busy.value || !data.value.configured || !row.available || active(row.task),
                      onClick: $event => (generate(row))
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString(__props.compact ? 'AI' : aiLabel(row)), 1)
                      ]),
                      _: 2
                    }, 1032, ["aria-label", "title", "loading", "disabled", "onClick"]))
                  : _createCommentVNode("", true),
                (!__props.compact && can('cancel', row))
                  ? (_openBlock$1(), _createBlock$1(_component_VBtn, {
                      key: 1,
                      size: "small",
                      variant: "text",
                      color: "warning",
                      disabled: busy.value,
                      onClick: $event => (request('cancel', [row]))
                    }, {
                      default: _withCtx(() => [...(_cache[27] || (_cache[27] = [
                        _createTextVNode("取消", -1)
                      ]))]),
                      _: 1
                    }, 8, ["disabled", "onClick"]))
                  : _createCommentVNode("", true)
              ])
            ], 2))
          }), 128))
        ]),
        (!__props.compact && (offset.value || data.value.more))
          ? (_openBlock$1(), _createElementBlock("nav", _hoisted_32, [
              _createVNode(_component_VBtn, {
                size: "small",
                variant: "tonal",
                disabled: !offset.value || loading.value,
                onClick: _cache[8] || (_cache[8] = $event => (select(filter.value, order.value, offset.value - data.value.page_size)))
              }, {
                default: _withCtx(() => [...(_cache[28] || (_cache[28] = [
                  _createTextVNode("上一页", -1)
                ]))]),
                _: 1
              }, 8, ["disabled"]),
              _createElementVNode("span", null, "第 " + _toDisplayString(offset.value / data.value.page_size + 1) + " 页", 1),
              _createVNode(_component_VBtn, {
                size: "small",
                variant: "tonal",
                disabled: !data.value.more || loading.value,
                onClick: _cache[9] || (_cache[9] = $event => (select(filter.value, order.value, offset.value + data.value.page_size)))
              }, {
                default: _withCtx(() => [...(_cache[29] || (_cache[29] = [
                  _createTextVNode("下一页", -1)
                ]))]),
                _: 1
              }, 8, ["disabled"])
            ]))
          : _createCommentVNode("", true)
      ]),
      _: 1
    })),
    (upload.value)
      ? (_openBlock$1(), _createBlock$1(MediaDialog, {
          key: 2,
          row: upload.value,
          call: call,
          onClose: _cache[10] || (_cache[10] = $event => (upload.value = null)),
          onChanged: load
        }, null, 8, ["row"]))
      : _createCommentVNode("", true),
    _createVNode(_component_VDialog, {
      "model-value": Boolean(englishOptions.value),
      "max-width": "640",
      scrollable: "",
      persistent: busy.value,
      "aria-labelledby": "hyrule-english",
      "onUpdate:modelValue": _cache[13] || (_cache[13] = open => { if (!open) englishOptions.value = null; })
    }, {
      default: _withCtx(() => [
        (englishOptions.value)
          ? (_openBlock$1(), _createBlock$1(_component_VCard, { key: 0 }, {
              default: _withCtx(() => [
                _createVNode(_component_VCardTitle, { id: "hyrule-english" }, {
                  default: _withCtx(() => [...(_cache[30] || (_cache[30] = [
                    _createTextVNode("选择英文字幕", -1)
                  ]))]),
                  _: 1
                }),
                _createVNode(_component_VCardText, null, {
                  default: _withCtx(() => [
                    _createElementVNode("p", _hoisted_33, _toDisplayString(englishOptions.value.file), 1),
                    _cache[31] || (_cache[31] = _createElementVNode("p", null, "请核对片源版本，再下载并翻译。", -1)),
                    (actionError.value)
                      ? (_openBlock$1(), _createElementBlock("p", _hoisted_34, _toDisplayString(actionError.value), 1))
                      : _createCommentVNode("", true),
                    _createElementVNode("div", _hoisted_35, [
                      (_openBlock$1(true), _createElementBlock(_Fragment, null, _renderList(englishOptions.value.candidates, (item) => {
                        return (_openBlock$1(), _createElementBlock("label", {
                          key: item.index,
                          class: "english-option"
                        }, [
                          _withDirectives(_createElementVNode("input", {
                            "onUpdate:modelValue": _cache[11] || (_cache[11] = $event => ((englishIndex).value = $event)),
                            name: "hyrule-english-option",
                            type: "radio",
                            value: item.index,
                            disabled: busy.value
                          }, null, 8, _hoisted_36), [
                            [_vModelRadio, englishIndex.value]
                          ]),
                          _createElementVNode("span", null, [
                            _createTextVNode(_toDisplayString(item.title), 1),
                            _createElementVNode("small", null, _toDisplayString(item.provider) + _toDisplayString(item.hash_match ? ' · 哈希匹配' : ''), 1)
                          ])
                        ]))
                      }), 128))
                    ])
                  ]),
                  _: 1
                }),
                _createVNode(_component_VCardActions, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_VSpacer),
                    _createVNode(_component_VBtn, {
                      disabled: busy.value,
                      onClick: _cache[12] || (_cache[12] = $event => (englishOptions.value = null))
                    }, {
                      default: _withCtx(() => [...(_cache[32] || (_cache[32] = [
                        _createTextVNode("返回", -1)
                      ]))]),
                      _: 1
                    }, 8, ["disabled"]),
                    _createVNode(_component_VBtn, {
                      color: "primary",
                      disabled: englishIndex.value === null,
                      loading: busy.value,
                      onClick: translateEnglish
                    }, {
                      default: _withCtx(() => [...(_cache[33] || (_cache[33] = [
                        _createTextVNode("下载并翻译", -1)
                      ]))]),
                      _: 1
                    }, 8, ["disabled", "loading"])
                  ]),
                  _: 1
                })
              ]),
              _: 1
            }))
          : _createCommentVNode("", true)
      ]),
      _: 1
    }, 8, ["model-value", "persistent"]),
    _createVNode(_component_VDialog, {
      "model-value": Boolean(pending.value),
      "max-width": "420",
      "aria-labelledby": "hyrule-confirm",
      "onUpdate:modelValue": _cache[16] || (_cache[16] = open => { if (!open) pending.value = null; })
    }, {
      default: _withCtx(() => [
        (pending.value)
          ? (_openBlock$1(), _createBlock$1(_component_VCard, { key: 0 }, {
              default: _withCtx(() => [
                _createVNode(_component_VCardTitle, { id: "hyrule-confirm" }, {
                  default: _withCtx(() => [
                    _createTextVNode(_toDisplayString(actions[pending.value.action].label) + " " + _toDisplayString(pending.value.ids.length) + " 条任务？", 1)
                  ]),
                  _: 1
                }),
                _createVNode(_component_VCardText, null, {
                  default: _withCtx(() => [
                    _createTextVNode(_toDisplayString(pending.value.action === 'delete' ? '移除任务记录，保留视频和字幕文件。' : '使用当前订阅模型翻译，字幕另存为独立版本。'), 1)
                  ]),
                  _: 1
                }),
                _createVNode(_component_VCardActions, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_VSpacer),
                    _createVNode(_component_VBtn, {
                      onClick: _cache[14] || (_cache[14] = $event => (pending.value = null))
                    }, {
                      default: _withCtx(() => [...(_cache[34] || (_cache[34] = [
                        _createTextVNode("返回", -1)
                      ]))]),
                      _: 1
                    }),
                    _createVNode(_component_VBtn, {
                      color: actions[pending.value.action].color,
                      onClick: _cache[15] || (_cache[15] = $event => (perform(pending.value)))
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString(actions[pending.value.action].label), 1)
                      ]),
                      _: 1
                    }, 8, ["color"])
                  ]),
                  _: 1
                })
              ]),
              _: 1
            }))
          : _createCommentVNode("", true)
      ]),
      _: 1
    }, 8, ["model-value"]),
    _createVNode(_component_VDialog, {
      "model-value": Boolean(history.value),
      "max-width": "640",
      "aria-labelledby": "hyrule-history",
      "onUpdate:modelValue": _cache[20] || (_cache[20] = open => { if (!open) history.value = null; })
    }, {
      default: _withCtx(() => [
        (history.value)
          ? (_openBlock$1(), _createBlock$1(_component_VCard, { key: 0 }, {
              default: _withCtx(() => [
                _createVNode(_component_VCardTitle, { id: "hyrule-history" }, {
                  default: _withCtx(() => [
                    _createTextVNode(_toDisplayString(history.value.row.title) + " · 历史任务", 1)
                  ]),
                  _: 1
                }),
                _createVNode(_component_VCardText, null, {
                  default: _withCtx(() => [
                    (_openBlock$1(true), _createElementBlock(_Fragment, null, _renderList(history.value.jobs, (job) => {
                      return (_openBlock$1(), _createElementBlock("p", {
                        key: job.id
                      }, "#" + _toDisplayString(job.id) + " · " + _toDisplayString(filters[job.state]?.[0]) + " · " + _toDisplayString(job.detail), 1))
                    }), 128))
                  ]),
                  _: 1
                }),
                _createVNode(_component_VCardActions, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_VSpacer),
                    (history.value.at)
                      ? (_openBlock$1(), _createBlock$1(_component_VBtn, {
                          key: 0,
                          onClick: _cache[17] || (_cache[17] = $event => (loadHistory(history.value.row, history.value.at - 100)))
                        }, {
                          default: _withCtx(() => [...(_cache[35] || (_cache[35] = [
                            _createTextVNode("上一页", -1)
                          ]))]),
                          _: 1
                        }))
                      : _createCommentVNode("", true),
                    (history.value.more)
                      ? (_openBlock$1(), _createBlock$1(_component_VBtn, {
                          key: 1,
                          onClick: _cache[18] || (_cache[18] = $event => (loadHistory(history.value.row, history.value.at + 100)))
                        }, {
                          default: _withCtx(() => [...(_cache[36] || (_cache[36] = [
                            _createTextVNode("下一页", -1)
                          ]))]),
                          _: 1
                        }))
                      : _createCommentVNode("", true),
                    _createVNode(_component_VBtn, {
                      onClick: _cache[19] || (_cache[19] = $event => (history.value = null))
                    }, {
                      default: _withCtx(() => [...(_cache[37] || (_cache[37] = [
                        _createTextVNode("关闭", -1)
                      ]))]),
                      _: 1
                    })
                  ]),
                  _: 1
                })
              ]),
              _: 1
            }))
          : _createCommentVNode("", true)
      ]),
      _: 1
    }, 8, ["model-value"])
  ], 2))
}
}

};
const Page = /*#__PURE__*/_export_sfc(_sfc_main$1, [['__scopeId',"data-v-9ead3957"]]);

const {openBlock:_openBlock,createBlock:_createBlock} = await importShared('vue');


const _sfc_main = {
  __name: 'AppPage',
  props: { api: Object, pluginId: { type: String, default: 'SubtitleManualUpload' } },
  setup(__props) {



return (_ctx, _cache) => {
  return (_openBlock(), _createBlock(Page, {
    api: __props.api,
    "plugin-id": __props.pluginId,
    show_switch: false,
    show_close: false
  }, null, 8, ["api", "plugin-id"]))
}
}

};

const {createApp} = await importShared('vue');

createApp(_sfc_main).mount('#app');
