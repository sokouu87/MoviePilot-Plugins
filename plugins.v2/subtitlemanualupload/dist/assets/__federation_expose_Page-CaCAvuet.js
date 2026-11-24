import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-pcqpp-6-.js';

const {createElementVNode:_createElementVNode,toDisplayString:_toDisplayString,createTextVNode:_createTextVNode,Fragment:_Fragment,openBlock:_openBlock,createElementBlock:_createElementBlock,createCommentVNode:_createCommentVNode,resolveComponent:_resolveComponent,withCtx:_withCtx,createVNode:_createVNode,renderList:_renderList,createBlock:_createBlock,vModelCheckbox:_vModelCheckbox,withDirectives:_withDirectives,normalizeClass:_normalizeClass} = await importShared('vue');


const _hoisted_1 = { class: "records" };
const _hoisted_2 = { class: "toolbar" };
const _hoisted_3 = { class: "heading" };
const _hoisted_4 = {
  class: "tools",
  role: "group",
  "aria-label": "任务操作"
};
const _hoisted_5 = { class: "content" };
const _hoisted_6 = {
  class: "filters",
  "aria-label": "按任务状态筛选"
};
const _hoisted_7 = {
  key: 0,
  class: "feedback error-text",
  role: "alert"
};
const _hoisted_8 = {
  key: 1,
  class: "feedback",
  role: "status"
};
const _hoisted_9 = {
  key: 2,
  class: "empty"
};
const _hoisted_10 = { class: "cards" };
const _hoisted_11 = { class: "pick" };
const _hoisted_12 = ["value", "aria-label"];
const _hoisted_13 = { class: "body" };
const _hoisted_14 = { class: "title" };
const _hoisted_15 = { class: "path" };
const _hoisted_16 = { class: "meta" };
const _hoisted_17 = { key: 0 };
const _hoisted_18 = { key: 1 };
const _hoisted_19 = { key: 2 };
const _hoisted_20 = { key: 3 };
const _hoisted_21 = ["datetime"];
const _hoisted_22 = ["datetime"];
const _hoisted_23 = ["datetime"];
const _hoisted_24 = { key: 0 };
const _hoisted_25 = ["href"];
const _hoisted_26 = { class: "actions" };
const _hoisted_27 = {
  key: 3,
  class: "pages",
  "aria-label": "任务分页"
};

const {computed,onBeforeUnmount,onMounted,ref} = await importShared('vue');


const pageSize = 100;

const _sfc_main = {
  __name: 'Page',
  props: {
  api: Object,
  pluginId: { type: String, default: 'SubtitleManualUpload' },
  show_switch: { type: Boolean, default: true },
  show_close: { type: Boolean, default: true },
},
  emits: ['close', 'switch'],
  setup(__props, { emit: __emit }) {

const props = __props;
const emit = __emit;
const states = {
  all: ['总数', 'primary'], queued: ['等待', 'info'], running: ['处理中', 'warning'],
  done: ['完成', 'success'], failed: ['失败', 'error'], cancelled: ['已取消', 'default'], skipped: ['已跳过', 'default'],
};
const actions = {
  cancel: { name: '取消', color: 'warning', icon: 'mdi-cancel', result: '已提交取消请求' },
  restart: { name: '重新生成', color: 'primary', icon: 'mdi-restart', result: '已提交重新生成' },
  delete: { name: '删除', color: 'error', icon: 'mdi-delete-outline', result: '已删除任务记录' },
};
const stampFormat = new Intl.DateTimeFormat('sv-SE', { dateStyle: 'short', timeStyle: 'medium', hourCycle: 'h23' });
const data = ref({ jobs: [], counts: {}, total: 0 });
const filter = ref('all');
const order = ref('desc');
const offset = ref(0);
const selected = ref([]);
const pending = ref(null);
const busy = ref(false);
const loading = ref(false);
const loadError = ref('');
const actionError = ref('');
const notice = ref('');
const picked = computed(() => data.value.jobs.filter(row => selected.value.includes(row.id)));
const allPicked = computed(() => picked.value.length > 0 && picked.value.length === data.value.jobs.length);
let requestId = 0;
let timer;

async function api(method, endpoint, body) {
  const result = await props.api[method](`plugin/${props.pluginId}/${endpoint}`, body);
  const payload = result?.data ?? result;
  if (result?.success === false || payload?.success === false) {
    throw new Error(payload?.message || result?.message || '操作失败')
  }
  return payload?.data ?? payload
}

function errorText(error) {
  return error?.response?.data?.detail || error?.message || '无法访问字幕插件'
}

async function load() {
  const id = ++requestId;
  loading.value = true;
  try {
    const params = new URLSearchParams({ state: filter.value, order: order.value, offset: offset.value });
    const result = await api('get', 'task_page?' + params);
    if (id !== requestId) return
    if (!result.jobs.length && offset.value) {
      const size = filter.value === 'all' ? result.total : result.counts[filter.value] || 0;
      offset.value = Math.floor(Math.max(0, size - 1) / pageSize) * pageSize;
      return load()
    }
    data.value = result;
    selected.value = selected.value.filter(key => result.jobs.some(row => row.id === key));
    loadError.value = result.history_error || '';
  } catch (error) {
    if (id === requestId) loadError.value = errorText(error);
  } finally {
    if (id === requestId) loading.value = false;
  }
}

function selectView(state, sort, start = 0) {
  filter.value = state;
  order.value = sort;
  offset.value = start;
  selected.value = [];
  notice.value = '';
  actionError.value = '';
  data.value = { ...data.value, jobs: [] };
  load();
}

function can(action, row) {
  const active = row.state === 'queued' || row.state === 'running';
  return action === 'cancel' ? active && !row.cancelling && !row.publishing : !active
}

function request(action, rows) {
  const ids = rows.filter(row => can(action, row)).map(row => row.id);
  if (!ids.length || busy.value) return
  if (action === 'cancel') return perform({ action, ids })
  pending.value = { action, ids };
}

async function perform(operation) {
  if (!operation || busy.value) return
  pending.value = null;
  busy.value = true;
  actionError.value = '';
  notice.value = '';
  try {
    const result = await api('post', 'task_actions', operation);
    const skipped = result.skipped.map(item => '#' + item.id + ' ' + item.reason);
    notice.value = `${actions[operation.action].result} ${result.changed.length} 条`;
    if (skipped.length) notice.value += `，跳过 ${skipped.length} 条（${skipped.slice(0, 3).join('、')}）`;
    selected.value = [];
    await load();
  } catch (error) {
    actionError.value = errorText(error);
  } finally {
    busy.value = false;
  }
}

async function retry(row) {
  if (busy.value) return
  busy.value = true;
  actionError.value = '';
  notice.value = '';
  try {
    await api('post', 'retry', { id: row.id });
    notice.value = `任务 #${row.id} 已进入队列`;
    await load();
  } catch (error) {
    actionError.value = errorText(error);
  } finally {
    busy.value = false;
  }
}

function utc(value) {
  return value.replace(' ', 'T') + 'Z'
}

function when(value) {
  const date = new Date(utc(value));
  return Number.isNaN(date.valueOf()) ? value : stampFormat.format(date)
}

function pathText(path) {
  return path.replace(/([\\/])((?:Season[ _.-]*\d+|S\d{1,2})(?:[\\/]|$))/i, '$1\n$2')
}

function hasReview(report) {
  return report.sources?.length || report.ambiguities?.length || Object.keys(report.warnings || {}).length
}

onMounted(() => {
  load();
  timer = setInterval(() => {
    if (!document.hidden && !busy.value && !loading.value && !pending.value) load();
  }, 8000);
});
onBeforeUnmount(() => { ++requestId; clearInterval(timer); });

return (_ctx, _cache) => {
  const _component_VBtn = _resolveComponent("VBtn");
  const _component_VChip = _resolveComponent("VChip");
  const _component_VCardTitle = _resolveComponent("VCardTitle");
  const _component_VCardText = _resolveComponent("VCardText");
  const _component_VSpacer = _resolveComponent("VSpacer");
  const _component_VCardActions = _resolveComponent("VCardActions");
  const _component_VCard = _resolveComponent("VCard");
  const _component_VDialog = _resolveComponent("VDialog");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createElementVNode("header", _hoisted_2, [
      _createElementVNode("div", _hoisted_3, [
        _cache[10] || (_cache[10] = _createElementVNode("h2", null, "海拉鲁 AI 字幕", -1)),
        _createElementVNode("p", null, [
          _createTextVNode(_toDisplayString(data.value.auto === undefined ? '字幕任务' : data.value.auto ? '已接管入库自动翻译' : '手动翻译'), 1),
          (data.value.model)
            ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
                _createTextVNode(" · " + _toDisplayString(data.value.model) + " · " + _toDisplayString(data.value.effort), 1)
              ], 64))
            : _createCommentVNode("", true)
        ])
      ]),
      _createElementVNode("div", _hoisted_4, [
        _createVNode(_component_VBtn, {
          color: "primary",
          variant: "tonal",
          "prepend-icon": order.value === 'desc' ? 'mdi-sort-clock-descending' : 'mdi-sort-clock-ascending',
          onClick: _cache[0] || (_cache[0] = $event => (selectView(filter.value, order.value === 'desc' ? 'asc' : 'desc')))
        }, {
          default: _withCtx(() => [
            _createTextVNode(_toDisplayString(order.value === 'desc' ? '最新在前' : '最早在前'), 1)
          ]),
          _: 1
        }, 8, ["prepend-icon"]),
        _createVNode(_component_VBtn, {
          color: "primary",
          variant: "tonal",
          "prepend-icon": "mdi-checkbox-multiple-marked-outline",
          disabled: !data.value.jobs.length || busy.value,
          onClick: _cache[1] || (_cache[1] = $event => (selected.value = allPicked.value ? [] : data.value.jobs.map(row => row.id)))
        }, {
          default: _withCtx(() => [
            _createTextVNode(_toDisplayString(allPicked.value ? '取消全选' : (offset.value || data.value.more ? '全选本页' : '全选')), 1)
          ]),
          _: 1
        }, 8, ["disabled"]),
        (_openBlock(), _createElementBlock(_Fragment, null, _renderList(actions, (spec, action) => {
          return _createVNode(_component_VBtn, {
            key: action,
            color: spec.color,
            variant: "tonal",
            "prepend-icon": spec.icon,
            disabled: busy.value || !picked.value.some(row => can(action, row)),
            onClick: $event => (request(action, picked.value))
          }, {
            default: _withCtx(() => [
              _createTextVNode("批量" + _toDisplayString(spec.name), 1)
            ]),
            _: 2
          }, 1032, ["color", "prepend-icon", "disabled", "onClick"])
        }), 64)),
        _createVNode(_component_VBtn, {
          icon: "mdi-refresh",
          color: "primary",
          variant: "text",
          "aria-label": "刷新任务",
          title: "刷新任务",
          loading: loading.value,
          disabled: busy.value,
          onClick: load
        }, null, 8, ["loading", "disabled"]),
        (__props.show_switch)
          ? (_openBlock(), _createBlock(_component_VBtn, {
              key: 0,
              icon: "mdi-cog-outline",
              color: "primary",
              variant: "text",
              "aria-label": "插件设置",
              title: "插件设置",
              onClick: _cache[2] || (_cache[2] = $event => (emit('switch')))
            }))
          : _createCommentVNode("", true),
        (__props.show_close)
          ? (_openBlock(), _createBlock(_component_VBtn, {
              key: 1,
              icon: "mdi-close",
              color: "primary",
              variant: "text",
              "aria-label": "关闭",
              title: "关闭",
              onClick: _cache[3] || (_cache[3] = $event => (emit('close')))
            }))
          : _createCommentVNode("", true)
      ])
    ]),
    _createElementVNode("main", _hoisted_5, [
      _createElementVNode("nav", _hoisted_6, [
        (_openBlock(), _createElementBlock(_Fragment, null, _renderList(states, ([label, color], state) => {
          return _createVNode(_component_VChip, {
            key: state,
            tag: "button",
            type: "button",
            size: "small",
            color: color,
            variant: filter.value === state ? 'flat' : 'tonal',
            "aria-pressed": filter.value === state,
            onClick: $event => (selectView(state, order.value))
          }, {
            default: _withCtx(() => [
              _createTextVNode(_toDisplayString(label) + " " + _toDisplayString(state === 'all' ? data.value.total : data.value.counts[state] || 0), 1)
            ]),
            _: 2
          }, 1032, ["color", "variant", "aria-pressed", "onClick"])
        }), 64))
      ]),
      (loadError.value || actionError.value)
        ? (_openBlock(), _createElementBlock("p", _hoisted_7, _toDisplayString(actionError.value || loadError.value), 1))
        : _createCommentVNode("", true),
      (notice.value)
        ? (_openBlock(), _createElementBlock("p", _hoisted_8, _toDisplayString(notice.value), 1))
        : _createCommentVNode("", true),
      (!data.value.jobs.length && !loadError.value)
        ? (_openBlock(), _createElementBlock("p", _hoisted_9, _toDisplayString(loading.value ? '正在读取任务…' : filter.value === 'all' ? '暂无字幕任务' : '当前筛选暂无任务'), 1))
        : _createCommentVNode("", true),
      _createElementVNode("div", _hoisted_10, [
        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(data.value.jobs, (row) => {
          return (_openBlock(), _createElementBlock("article", {
            key: row.id,
            class: _normalizeClass(["task", { marked: selected.value.includes(row.id) }])
          }, [
            _createElementVNode("label", _hoisted_11, [
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((selected).value = $event)),
                type: "checkbox",
                value: row.id,
                "aria-label": '选择 ' + row.file
              }, null, 8, _hoisted_12), [
                [_vModelCheckbox, selected.value]
              ])
            ]),
            _createElementVNode("div", _hoisted_13, [
              _createElementVNode("div", _hoisted_14, [
                _createElementVNode("strong", null, _toDisplayString(row.file), 1),
                _createVNode(_component_VChip, {
                  size: "x-small",
                  variant: "tonal",
                  color: states[row.state]?.[1]
                }, {
                  default: _withCtx(() => [
                    _createTextVNode(_toDisplayString(row.cancelling ? '取消中' : row.state === 'done' ? '已完成' : states[row.state]?.[0] || row.state), 1)
                  ]),
                  _: 2
                }, 1032, ["color"])
              ]),
              _createElementVNode("div", _hoisted_15, _toDisplayString(pathText(row.path)), 1),
              _createElementVNode("div", _hoisted_16, [
                _createElementVNode("span", null, [
                  _createTextVNode(_toDisplayString(row.origin), 1),
                  (row.legacy)
                    ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
                        _createTextVNode(" · 联动版历史")
                      ], 64))
                    : _createCommentVNode("", true)
                ]),
                (row.report.source)
                  ? (_openBlock(), _createElementBlock("span", _hoisted_17, _toDisplayString(row.report.source), 1))
                  : _createCommentVNode("", true),
                (row.report.model)
                  ? (_openBlock(), _createElementBlock("span", _hoisted_18, _toDisplayString(row.report.model), 1))
                  : _createCommentVNode("", true),
                (row.report.cues)
                  ? (_openBlock(), _createElementBlock("span", _hoisted_19, _toDisplayString(row.report.cues) + " 轴", 1))
                  : _createCommentVNode("", true),
                (row.report.files?.length)
                  ? (_openBlock(), _createElementBlock("span", _hoisted_20, "输出：" + _toDisplayString(row.report.files.join('、')), 1))
                  : _createCommentVNode("", true),
                (row.created)
                  ? (_openBlock(), _createElementBlock("time", {
                      key: 4,
                      datetime: utc(row.created),
                      title: "创建时间"
                    }, _toDisplayString(when(row.created)), 9, _hoisted_21))
                  : _createCommentVNode("", true),
                (row.finished)
                  ? (_openBlock(), _createElementBlock("time", {
                      key: 5,
                      datetime: utc(row.finished),
                      title: "结束时间"
                    }, _toDisplayString(when(row.finished)), 9, _hoisted_22))
                  : (row.report.rendered)
                    ? (_openBlock(), _createElementBlock("time", {
                        key: 6,
                        datetime: utc(row.report.rendered)
                      }, "译稿生成时间 " + _toDisplayString(when(row.report.rendered)), 9, _hoisted_23))
                    : _createCommentVNode("", true)
              ]),
              _createElementVNode("p", {
                class: _normalizeClass(["detail", { 'error-text': row.state === 'failed' }])
              }, _toDisplayString(row.cancelling ? '正在取消，等待当前步骤结束' : row.detail), 3),
              (hasReview(row.report))
                ? (_openBlock(), _createElementBlock("details", _hoisted_24, [
                    _cache[11] || (_cache[11] = _createElementVNode("summary", null, "审校记录", -1)),
                    (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(row.report.warnings, (words, id) => {
                      return (_openBlock(), _createElementBlock("p", { key: id }, "第 " + _toDisplayString(id) + " 轴 · " + _toDisplayString(words.join('、')), 1))
                    }), 128)),
                    (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(row.report.ambiguities, (a) => {
                      return (_openBlock(), _createElementBlock("p", {
                        key: a.id
                      }, "第 " + _toDisplayString(a.id) + " 轴 · " + _toDisplayString(a.options.join(' / ')) + " · " + _toDisplayString(a.reason), 1))
                    }), 128)),
                    (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(row.report.sources, (url) => {
                      return (_openBlock(), _createElementBlock("div", { key: url }, [
                        _createElementVNode("a", {
                          href: url,
                          target: "_blank",
                          rel: "noopener noreferrer"
                        }, _toDisplayString(url), 9, _hoisted_25)
                      ]))
                    }), 128))
                  ]))
                : _createCommentVNode("", true)
            ]),
            _createElementVNode("div", _hoisted_26, [
              (row.state === 'failed' && !row.legacy)
                ? (_openBlock(), _createBlock(_component_VBtn, {
                    key: 0,
                    size: "small",
                    color: "primary",
                    variant: "tonal",
                    disabled: busy.value,
                    onClick: $event => (retry(row))
                  }, {
                    default: _withCtx(() => [...(_cache[12] || (_cache[12] = [
                      _createTextVNode("从断点重试", -1)
                    ]))]),
                    _: 1
                  }, 8, ["disabled", "onClick"]))
                : _createCommentVNode("", true),
              (_openBlock(), _createElementBlock(_Fragment, null, _renderList(actions, (spec, action) => {
                return _createVNode(_component_VBtn, {
                  key: action,
                  size: "small",
                  color: spec.color,
                  variant: "tonal",
                  disabled: busy.value || !can(action, row),
                  onClick: $event => (request(action, [row]))
                }, {
                  default: _withCtx(() => [
                    _createTextVNode(_toDisplayString(spec.name), 1)
                  ]),
                  _: 2
                }, 1032, ["color", "disabled", "onClick"])
              }), 64))
            ])
          ], 2))
        }), 128))
      ]),
      (offset.value || data.value.more)
        ? (_openBlock(), _createElementBlock("nav", _hoisted_27, [
            _createVNode(_component_VBtn, {
              size: "small",
              variant: "tonal",
              disabled: !offset.value || loading.value,
              onClick: _cache[5] || (_cache[5] = $event => (selectView(filter.value, order.value, offset.value - pageSize)))
            }, {
              default: _withCtx(() => [...(_cache[13] || (_cache[13] = [
                _createTextVNode("上一页", -1)
              ]))]),
              _: 1
            }, 8, ["disabled"]),
            _createElementVNode("span", null, "第 " + _toDisplayString(offset.value / pageSize + 1) + " 页", 1),
            _createVNode(_component_VBtn, {
              size: "small",
              variant: "tonal",
              disabled: !data.value.more || loading.value,
              onClick: _cache[6] || (_cache[6] = $event => (selectView(filter.value, order.value, offset.value + pageSize)))
            }, {
              default: _withCtx(() => [...(_cache[14] || (_cache[14] = [
                _createTextVNode("下一页", -1)
              ]))]),
              _: 1
            }, 8, ["disabled"])
          ]))
        : _createCommentVNode("", true)
    ]),
    _createVNode(_component_VDialog, {
      "model-value": Boolean(pending.value),
      "max-width": "420",
      "aria-labelledby": "hyrule-confirm",
      "onUpdate:modelValue": _cache[9] || (_cache[9] = open => { if (!open) pending.value = null; })
    }, {
      default: _withCtx(() => [
        (pending.value)
          ? (_openBlock(), _createBlock(_component_VCard, { key: 0 }, {
              default: _withCtx(() => [
                _createVNode(_component_VCardTitle, { id: "hyrule-confirm" }, {
                  default: _withCtx(() => [
                    _createTextVNode(_toDisplayString(actions[pending.value.action].name) + " " + _toDisplayString(pending.value.ids.length) + " 条任务？", 1)
                  ]),
                  _: 1
                }),
                _createVNode(_component_VCardText, null, {
                  default: _withCtx(() => [
                    _createTextVNode(_toDisplayString(pending.value.action === 'delete' ? '移除所选任务记录。视频和字幕文件会保留。' : '用当前订阅模型重新翻译。新字幕将使用独立文件名。'), 1)
                  ]),
                  _: 1
                }),
                _createVNode(_component_VCardActions, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_VSpacer),
                    _createVNode(_component_VBtn, {
                      variant: "text",
                      onClick: _cache[7] || (_cache[7] = $event => (pending.value = null))
                    }, {
                      default: _withCtx(() => [...(_cache[15] || (_cache[15] = [
                        _createTextVNode("返回", -1)
                      ]))]),
                      _: 1
                    }),
                    _createVNode(_component_VBtn, {
                      variant: "tonal",
                      color: actions[pending.value.action].color,
                      onClick: _cache[8] || (_cache[8] = $event => (perform(pending.value)))
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString(actions[pending.value.action].name), 1)
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
    }, 8, ["model-value"])
  ]))
}
}

};
const Page = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-e65d025b"]]);

export { Page as default };
