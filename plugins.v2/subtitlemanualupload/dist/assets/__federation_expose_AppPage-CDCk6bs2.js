import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import Page from './__federation_expose_Page-CaCAvuet.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-pcqpp-6-.js';

const {createElementVNode:_createElementVNode$2,toDisplayString:_toDisplayString$1,createTextVNode:_createTextVNode$2,resolveComponent:_resolveComponent$1,withCtx:_withCtx$1,createVNode:_createVNode$1,openBlock:_openBlock$2,createElementBlock:_createElementBlock$2,createCommentVNode:_createCommentVNode$2,renderList:_renderList$1,Fragment:_Fragment$1,vModelText:_vModelText$1,withDirectives:_withDirectives$2} = await importShared('vue');


const _hoisted_1$2 = { class: "inventory" };
const _hoisted_2$2 = {
  key: 0,
  role: "status"
};
const _hoisted_3$1 = {
  key: 1,
  role: "alert",
  class: "inventory-error"
};
const _hoisted_4$1 = { key: 2 };
const _hoisted_5$1 = { class: "inventory-meta" };
const _hoisted_6$1 = {
  class: "inventory-filters",
  role: "group",
  "aria-label": "字幕覆盖状态"
};
const _hoisted_7$1 = { class: "inventory-filters" };
const _hoisted_8$1 = ["value"];
const _hoisted_9$1 = {
  key: 0,
  class: "inventory-table"
};
const _hoisted_10$1 = { "aria-label": "字幕清点结果" };
const _hoisted_11$1 = { key: 0 };
const _hoisted_12$1 = { key: 1 };
const _hoisted_13$1 = {
  class: "inventory-filters",
  "aria-label": "字幕清单分页"
};

const {computed,onBeforeUnmount: onBeforeUnmount$1,onMounted: onMounted$1,ref: ref$2,watch: watch$1} = await importShared('vue');



const _sfc_main$2 = {
  __name: 'SubtitleInventory',
  props: { api: Object, pluginId: String },
  setup(__props) {

const props = __props;
const labels = { all: '全部', present: '已有中文', missing: '缺中文字幕', unknown: '待确认', disc: '原盘分段' };
const kind = ref$2('all'), state = ref$2('missing'), q = ref$2(''), offset = ref$2(0);
const data = ref$2({ rows: [], matches: 0, page_size: 100 });
const loading = ref$2(false), starting = ref$2(false), error = ref$2('');
const counts = computed(() => data.value.summary?.[kind.value]);
let generation = 0;
let poll, debounce;

async function request(method, endpoint) {
  const result = await props.api[method](`plugin/${props.pluginId}/${endpoint}`);
  const payload = result?.data ?? result;
  if (result?.success === false || payload?.success === false)
    throw new Error(payload?.message || result?.message || '无法读取字幕清单')
  return payload?.data ?? payload
}

function failed(reason) {
  error.value = reason?.response?.data?.detail || reason?.message || '无法读取字幕清单';
}

async function load() {
  const pending = ++generation;
  loading.value = true;
  try {
    const params = new URLSearchParams({ state: state.value, kind: kind.value, q: q.value, offset: offset.value });
    const snapshot = await request('get', 'subtitle_inventory?' + params);
    if (pending !== generation) return
    if (offset.value && !snapshot.rows.length) {
      offset.value = 0;
      return load()
    }
    data.value = snapshot;
    error.value = snapshot.error || '';
  } catch (reason) {
    if (pending === generation) failed(reason);
  } finally {
    if (pending === generation) loading.value = false;
  }
}

async function scan() {
  starting.value = true;
  error.value = '';
  try {
    await request('post', 'inventory_scan');
    await load();
  } catch (reason) { failed(reason); }
  finally { starting.value = false; }
}

function select(nextState, nextKind = kind.value, nextOffset = 0) {
  clearTimeout(debounce);
  state.value = nextState;
  kind.value = nextKind;
  offset.value = nextOffset;
  load();
}

function title(row) {
  if (row.type === 'Movie') return row.year ? `${row.title} (${row.year})` : row.title
  const season = row.season == null ? '' : 'S' + String(row.season).padStart(2, '0');
  const episode = row.episode == null ? '' : 'E' + String(row.episode).padStart(2, '0');
  const end = row.episode_end > row.episode ? '–E' + String(row.episode_end).padStart(2, '0') : '';
  return [row.series, season + episode + end, row.title].filter(Boolean).join(' · ')
}

function notes(row) {
  return [row.bilingual && '中英双语', row.chinese.includes('embedded') && '内封中文',
    row.chinese.includes('external') && '外挂中文', row.english && '有英文文本', row.reason].filter(Boolean).join(' · ')
}

watch$1(q, () => {
  clearTimeout(debounce);
  debounce = setTimeout(() => select(state.value), 200);
});
onMounted$1(() => {
  load();
  poll = setInterval(() => { if (data.value.scanning && !loading.value && !document.hidden) load(); }, 3000);
});
onBeforeUnmount$1(() => { ++generation; clearInterval(poll); clearTimeout(debounce); });

return (_ctx, _cache) => {
  const _component_VBtn = _resolveComponent$1("VBtn");

  return (_openBlock$2(), _createElementBlock$2("section", _hoisted_1$2, [
    _createElementVNode$2("header", null, [
      _cache[4] || (_cache[4] = _createElementVNode$2("h3", null, "片库字幕清单", -1)),
      _createVNode$1(_component_VBtn, {
        color: "primary",
        variant: "tonal",
        disabled: starting.value || data.value.scanning,
        onClick: scan
      }, {
        default: _withCtx$1(() => [
          _createTextVNode$2(_toDisplayString$1(data.value.created ? '重新清点片库' : '清点整个 Emby 片库'), 1)
        ]),
        _: 1
      }, 8, ["disabled"])
    ]),
    (data.value.scanning)
      ? (_openBlock$2(), _createElementBlock$2("p", _hoisted_2$2, _toDisplayString$1(data.value.progress || '正在清点 Emby 片库…'), 1))
      : _createCommentVNode$2("", true),
    (error.value)
      ? (_openBlock$2(), _createElementBlock$2("p", _hoisted_3$1, _toDisplayString$1(error.value), 1))
      : _createCommentVNode$2("", true),
    (!data.value.created && !data.value.scanning && !loading.value)
      ? (_openBlock$2(), _createElementBlock$2("p", _hoisted_4$1, "清点会读取电影和单集的字幕轨，生成一份可筛选的清单。"))
      : _createCommentVNode$2("", true),
    (data.value.created)
      ? (_openBlock$2(), _createElementBlock$2(_Fragment$1, { key: 3 }, [
          _createElementVNode$2("p", _hoisted_5$1, _toDisplayString$1(new Date(data.value.created).toLocaleString('zh-CN', { hour12: false })) + " · " + _toDisplayString$1(data.value.summary.Movie.items) + " 条电影记录 · " + _toDisplayString$1(data.value.summary.Episode.items) + " 条单集记录 · " + _toDisplayString$1(data.value.summary.all.total) + " 个片源 ", 1),
          _createElementVNode$2("div", _hoisted_6$1, [
            (_openBlock$2(), _createElementBlock$2(_Fragment$1, null, _renderList$1(labels, (label, key) => {
              return _createVNode$1(_component_VBtn, {
                key: key,
                size: "small",
                color: "primary",
                variant: state.value === key ? 'flat' : 'tonal',
                "aria-pressed": state.value === key,
                onClick: $event => (select(key))
              }, {
                default: _withCtx$1(() => [
                  _createTextVNode$2(_toDisplayString$1(label) + " " + _toDisplayString$1(key === 'all' ? counts.value.total : counts.value[key]), 1)
                ]),
                _: 2
              }, 1032, ["variant", "aria-pressed", "onClick"])
            }), 64))
          ]),
          _createElementVNode$2("div", _hoisted_7$1, [
            _createElementVNode$2("label", null, [
              _cache[6] || (_cache[6] = _createTextVNode$2("类型 ", -1)),
              _createElementVNode$2("select", {
                value: kind.value,
                onChange: _cache[0] || (_cache[0] = $event => (select(state.value, $event.target.value)))
              }, [...(_cache[5] || (_cache[5] = [
                _createElementVNode$2("option", { value: "all" }, "全部影视", -1),
                _createElementVNode$2("option", { value: "Movie" }, "电影", -1),
                _createElementVNode$2("option", { value: "Episode" }, "剧集", -1)
              ]))], 40, _hoisted_8$1)
            ]),
            _withDirectives$2(_createElementVNode$2("input", {
              "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((q).value = $event)),
              type: "search",
              "aria-label": "搜索字幕清单",
              placeholder: "片名、剧名、S01E01 或文件名"
            }, null, 512), [
              [_vModelText$1, q.value]
            ])
          ]),
          (data.value.rows.length)
            ? (_openBlock$2(), _createElementBlock$2("div", _hoisted_9$1, [
                _createElementVNode$2("table", _hoisted_10$1, [
                  _cache[7] || (_cache[7] = _createElementVNode$2("thead", null, [
                    _createElementVNode$2("tr", null, [
                      _createElementVNode$2("th", null, "作品"),
                      _createElementVNode$2("th", null, "片源"),
                      _createElementVNode$2("th", null, "字幕")
                    ])
                  ], -1)),
                  _createElementVNode$2("tbody", null, [
                    (_openBlock$2(true), _createElementBlock$2(_Fragment$1, null, _renderList$1(data.value.rows, (row, i) => {
                      return (_openBlock$2(), _createElementBlock$2("tr", { key: i }, [
                        _createElementVNode$2("td", null, _toDisplayString$1(title(row)), 1),
                        _createElementVNode$2("td", null, _toDisplayString$1(row.file || 'Emby 条目 ' + row.item), 1),
                        _createElementVNode$2("td", null, [
                          _createElementVNode$2("strong", null, _toDisplayString$1(labels[row.state]), 1),
                          (notes(row))
                            ? (_openBlock$2(), _createElementBlock$2("small", _hoisted_11$1, _toDisplayString$1(notes(row)), 1))
                            : _createCommentVNode$2("", true)
                        ])
                      ]))
                    }), 128))
                  ])
                ])
              ]))
            : (_openBlock$2(), _createElementBlock$2("p", _hoisted_12$1, _toDisplayString$1(loading.value ? '正在读取清单…' : '当前筛选没有结果'), 1)),
          _createElementVNode$2("nav", _hoisted_13$1, [
            _createVNode$1(_component_VBtn, {
              size: "small",
              variant: "tonal",
              disabled: !offset.value || loading.value,
              onClick: _cache[2] || (_cache[2] = $event => (select(state.value, kind.value, offset.value - data.value.page_size)))
            }, {
              default: _withCtx$1(() => [...(_cache[8] || (_cache[8] = [
                _createTextVNode$2("上一页", -1)
              ]))]),
              _: 1
            }, 8, ["disabled"]),
            _createElementVNode$2("span", null, _toDisplayString$1(data.value.matches) + " 个结果 · 第 " + _toDisplayString$1(offset.value / data.value.page_size + 1) + " 页", 1),
            _createVNode$1(_component_VBtn, {
              size: "small",
              variant: "tonal",
              disabled: offset.value + data.value.page_size >= data.value.matches || loading.value,
              onClick: _cache[3] || (_cache[3] = $event => (select(state.value, kind.value, offset.value + data.value.page_size)))
            }, {
              default: _withCtx$1(() => [...(_cache[9] || (_cache[9] = [
                _createTextVNode$2("下一页", -1)
              ]))]),
              _: 1
            }, 8, ["disabled"])
          ])
        ], 64))
      : _createCommentVNode$2("", true)
  ]))
}
}

};
const SubtitleInventory = /*#__PURE__*/_export_sfc(_sfc_main$2, [['__scopeId',"data-v-e0260150"]]);

const {createElementVNode:_createElementVNode$1,toDisplayString:_toDisplayString,openBlock:_openBlock$1,createBlock:_createBlock$1,createCommentVNode:_createCommentVNode$1,createElementBlock:_createElementBlock$1,vModelText:_vModelText,withDirectives:_withDirectives$1,renderList:_renderList,Fragment:_Fragment,createTextVNode:_createTextVNode$1,withModifiers:_withModifiers,vModelSelect:_vModelSelect,vShow:_vShow$1} = await importShared('vue');


const _hoisted_1$1 = { class: "studio" };
const _hoisted_2$1 = { class: "row" };
const _hoisted_3 = ["aria-expanded"];
const _hoisted_4 = {
  key: 0,
  role: "status"
};
const _hoisted_5 = {
  key: 1,
  class: "err",
  role: "alert"
};
const _hoisted_6 = {
  key: 2,
  role: "status"
};
const _hoisted_7 = { class: "row" };
const _hoisted_8 = ["disabled"];
const _hoisted_9 = { class: "choices" };
const _hoisted_10 = ["disabled", "aria-pressed", "onClick"];
const _hoisted_11 = { key: 0 };
const _hoisted_12 = { key: 3 };
const _hoisted_13 = { class: "filename" };
const _hoisted_14 = { class: "row" };
const _hoisted_15 = ["disabled"];
const _hoisted_16 = ["disabled"];
const _hoisted_17 = ["disabled"];
const _hoisted_18 = ["onUpdate:modelValue"];
const _hoisted_19 = ["disabled"];
const _hoisted_20 = ["disabled"];
const _hoisted_21 = ["href"];
const _hoisted_22 = { key: 2 };
const _hoisted_23 = { class: "row" };
const _hoisted_24 = ["disabled"];

const {ref: ref$1,onMounted,onBeforeUnmount,watch} = await importShared('vue');


const _sfc_main$1 = {
  __name: 'MediaLibrary',
  props: { api: Object, pluginId: { type: String, default: 'SubtitleManualUpload' } },
  setup(__props) {

const props = __props;
const storeKey = 'hyrule-ai.selection.' + props.pluginId;
const query = ref$1(''), rows = ref$1([]), selected = ref$1(null), more = ref$1(false);
const file = ref$1(null), member = ref$1(''), members = ref$1([]), role = ref$1('zh-Hans'), input = ref$1(null);
const busy = ref$1(false), message = ref$1(''), error = ref$1(''), index = ref$1(false), account = ref$1(''), configured = ref$1(true);
const glossary = ref$1(null), meta = ref$1(null);
const showInventory = ref$1(false);
let timer, debounce, searchSeq = 0, disposed = false;

async function api(method, endpoint, body) {
  const value = await props.api[method]('plugin/' + props.pluginId + '/' + endpoint, body);
  if (value?.success === false) throw new Error(value.message || 'MoviePilot 请求失败')
  return value?.data ?? value
}
function fail(e) {
  error.value = e?.response?.data?.detail || e?.detail || e?.message || '请求失败';
}
async function list(append = false) {
  const seq = ++searchSeq;
  try {
    const res = await api('get', 'targets?q=' + encodeURIComponent(query.value) + '&offset=' + (append ? rows.value.length : 0));
    if (disposed || seq !== searchSeq) return
    rows.value = append ? rows.value.concat(res.targets) : res.targets;
    more.value = res.more;
    index.value = res.indexing;
    if (res.error) error.value = res.error;
  } catch (e) { if (seq === searchSeq) fail(e); }
}
async function loadAccount() {
  const data = await api('get', 'jobs');
  if (disposed) return
  configured.value = data.configured;
  account.value = data.model + ' · ' + data.effort;
}
function clearFile() {
  file.value = null;
  member.value = '';
  members.value = [];
  if (input.value) input.value.value = '';
}
function pick(item) {
  selected.value = item;
  try { sessionStorage.setItem(storeKey, JSON.stringify(item)); } catch {}
  clearFile();
  glossary.value = null;
  meta.value = null;
  message.value = error.value = '';
}
async function act(fn) {
  if (busy.value) return
  busy.value = true;
  message.value = error.value = '';
  try { await fn(); } catch (e) { fail(e); } finally { busy.value = false; }
}
function translate() {
  return act(async () => {
    const result = await api('post', 'translate', { target: selected.value.id });
    message.value = '翻译任务 #' + result.id + ' 已进入队列';
  })
}
function upload() {
  return act(async () => {
    if (!file.value) throw new Error('请先选择字幕')
    const data = new FormData();
    data.append('target', selected.value.id);
    data.append('role', role.value);
    data.append('member', member.value);
    data.append('file', file.value);
    const res = await api('post', 'upload', data);
    if (res.members) {
      members.value = res.members;
      message.value = '请选择与当前影片或集数对应的字幕文件';
    } else {
      message.value = '已上传 ' + res.file + '（' + res.cues + ' 轴）';
      clearFile();
    }
  })
}
function editGlossary() {
  return act(async () => {
    const res = await api('get', 'glossary?target=' + encodeURIComponent(selected.value.id));
    glossary.value = JSON.stringify(res.glossary, null, 2);
  })
}
function saveGlossary() {
  return act(async () => {
    await api('post', 'glossary', { target: selected.value.id, glossary: JSON.parse(glossary.value) });
    glossary.value = null;
    message.value = '已保存本剧译名表';
  })
}
function saveMeta() {
  return act(async () => {
    await api('post', 'metadata', { ...meta.value, target: selected.value.id });
    const updated = await api('get', 'target?id=' + encodeURIComponent(selected.value.id));
    pick(updated);
    await list();
    message.value = '作品资料已保存';
  })
}
watch(query, () => { clearTimeout(debounce); debounce = setTimeout(() => list(), 200); });
onMounted(async () => {
  try {
    const saved = JSON.parse(sessionStorage.getItem(storeKey) || 'null');
    if (saved?.id) {
      try { selected.value = await api('get', 'target?id=' + encodeURIComponent(saved.id)); }
      catch { sessionStorage.removeItem(storeKey); }
    }
    await Promise.all([list(), loadAccount()]);
  } catch (e) { fail(e); }
  if (disposed) return
  timer = setInterval(() => { if (index.value) list(); }, 5000);
});
onBeforeUnmount(() => { disposed = true; clearInterval(timer); clearTimeout(debounce); });

return (_ctx, _cache) => {
  return (_openBlock$1(), _createElementBlock$1("main", _hoisted_1$1, [
    _createElementVNode$1("header", null, [
      _cache[12] || (_cache[12] = _createElementVNode$1("h2", null, "海拉鲁 AI 字幕", -1)),
      _createElementVNode$1("div", _hoisted_2$1, [
        _createElementVNode$1("span", null, _toDisplayString(account.value), 1),
        _createElementVNode$1("button", {
          "aria-expanded": showInventory.value,
          onClick: _cache[0] || (_cache[0] = $event => (showInventory.value = !showInventory.value))
        }, _toDisplayString(showInventory.value ? '返回选片' : '字幕清单'), 9, _hoisted_3)
      ])
    ]),
    (showInventory.value)
      ? (_openBlock$1(), _createBlock$1(SubtitleInventory, {
          key: 0,
          api: api,
          "plugin-id": __props.pluginId
        }, null, 8, ["plugin-id"]))
      : _createCommentVNode$1("", true),
    _withDirectives$1(_createElementVNode$1("div", null, [
      (!configured.value)
        ? (_openBlock$1(), _createElementBlock$1("p", _hoisted_4, "请在插件设置中填入本机订阅线路密钥，或启用已配置的 AutoSubv3 订阅线路。"))
        : _createCommentVNode$1("", true),
      (error.value)
        ? (_openBlock$1(), _createElementBlock$1("p", _hoisted_5, _toDisplayString(error.value), 1))
        : _createCommentVNode$1("", true),
      (message.value)
        ? (_openBlock$1(), _createElementBlock$1("p", _hoisted_6, _toDisplayString(message.value), 1))
        : _createCommentVNode$1("", true),
      _createElementVNode$1("section", null, [
        _cache[13] || (_cache[13] = _createElementVNode$1("h3", null, "选择影片或剧集", -1)),
        _createElementVNode$1("div", _hoisted_7, [
          _withDirectives$1(_createElementVNode$1("input", {
            "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((query).value = $event)),
            type: "search",
            "aria-label": "搜索媒体",
            placeholder: "输入片名、集数或文件名"
          }, null, 512), [
            [_vModelText, query.value]
          ]),
          _createElementVNode$1("button", {
            disabled: busy.value || index.value,
            onClick: _cache[2] || (_cache[2] = $event => {act(async () => { await api('post','refresh',{}); await list(); });})
          }, _toDisplayString(index.value ? '正在索引…' : '刷新媒体'), 9, _hoisted_8)
        ]),
        _createElementVNode$1("ul", _hoisted_9, [
          (_openBlock$1(true), _createElementBlock$1(_Fragment, null, _renderList(rows.value, (t) => {
            return (_openBlock$1(), _createElementBlock$1("li", {
              key: t.id
            }, [
              _createElementVNode$1("button", {
                disabled: busy.value,
                "aria-pressed": selected.value?.id===t.id,
                onClick: $event => (pick(t))
              }, [
                _createElementVNode$1("strong", null, _toDisplayString(t.label), 1),
                _createElementVNode$1("small", null, _toDisplayString(t.file), 1)
              ], 8, _hoisted_10)
            ]))
          }), 128))
        ]),
        (!rows.value.length)
          ? (_openBlock$1(), _createElementBlock$1("p", _hoisted_11, _toDisplayString(index.value ? '正在读取媒体库…' : '没有匹配的媒体'), 1))
          : _createCommentVNode$1("", true),
        (more.value)
          ? (_openBlock$1(), _createElementBlock$1("button", {
              key: 1,
              onClick: _cache[3] || (_cache[3] = $event => (list(true)))
            }, "更多结果"))
          : _createCommentVNode$1("", true)
      ]),
      (selected.value)
        ? (_openBlock$1(), _createElementBlock$1("section", _hoisted_12, [
            _createElementVNode$1("h3", null, _toDisplayString(selected.value.label), 1),
            _createElementVNode$1("p", _hoisted_13, _toDisplayString(selected.value.file), 1),
            _createElementVNode$1("div", _hoisted_14, [
              _createElementVNode$1("button", {
                class: "primary",
                disabled: busy.value || !configured.value,
                onClick: translate
              }, "AI 翻译", 8, _hoisted_15),
              _createElementVNode$1("button", {
                disabled: busy.value,
                onClick: editGlossary
              }, "本剧译名表", 8, _hoisted_16),
              _createElementVNode$1("button", {
                disabled: busy.value,
                onClick: _cache[4] || (_cache[4] = $event => (meta.value = {...selected.value.meta}))
              }, "作品资料", 8, _hoisted_17)
            ]),
            (meta.value)
              ? (_openBlock$1(), _createElementBlock$1("form", {
                  key: 0,
                  onSubmit: _withModifiers(saveMeta, ["prevent"])
                }, [
                  (_openBlock$1(), _createElementBlock$1(_Fragment, null, _renderList({title:'片名',year:'年份',season:'季',episode:'集'}, (label, k) => {
                    return _createElementVNode$1("label", { key: k }, [
                      _createTextVNode$1(_toDisplayString(label), 1),
                      _withDirectives$1(_createElementVNode$1("input", {
                        "onUpdate:modelValue": $event => ((meta.value[k]) = $event)
                      }, null, 8, _hoisted_18), [
                        [_vModelText, meta.value[k]]
                      ])
                    ])
                  }), 64)),
                  _createElementVNode$1("button", { disabled: busy.value }, "保存资料", 8, _hoisted_19),
                  _createElementVNode$1("button", {
                    type: "button",
                    onClick: _cache[5] || (_cache[5] = $event => (meta.value=null))
                  }, "取消")
                ], 32))
              : _createCommentVNode$1("", true),
            (glossary.value !== null)
              ? (_openBlock$1(), _createElementBlock$1("form", {
                  key: 1,
                  onSubmit: _withModifiers(saveGlossary, ["prevent"])
                }, [
                  _createElementVNode$1("label", null, [
                    _cache[14] || (_cache[14] = _createTextVNode$1("译名表 JSON", -1)),
                    _withDirectives$1(_createElementVNode$1("textarea", {
                      "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((glossary).value = $event)),
                      rows: "10"
                    }, null, 512), [
                      [_vModelText, glossary.value]
                    ])
                  ]),
                  _createElementVNode$1("label", null, [
                    _cache[15] || (_cache[15] = _createTextVNode$1("从文件导入", -1)),
                    _createElementVNode$1("input", {
                      type: "file",
                      accept: ".json",
                      onChange: _cache[7] || (_cache[7] = e => act(async () => { const f = e.target.files[0]; if (f) glossary.value = await f.text(); }))
                    }, null, 32)
                  ]),
                  _createElementVNode$1("button", { disabled: busy.value }, "保存译名表", 8, _hoisted_20),
                  _createElementVNode$1("button", {
                    type: "button",
                    onClick: _cache[8] || (_cache[8] = $event => (glossary.value=null))
                  }, "取消")
                ], 32))
              : _createCommentVNode$1("", true),
            _cache[21] || (_cache[21] = _createElementVNode$1("h4", null, "SubHD 手动字幕", -1)),
            _createElementVNode$1("a", {
              href: selected.value.search_url,
              target: "_blank",
              rel: "noopener noreferrer"
            }, "在 SubHD 搜索 ↗", 8, _hoisted_21),
            _cache[22] || (_cache[22] = _createElementVNode$1("p", null, "到官网完成验证和下载，回到此处上传到上方影片。RAR 或 7z 请先解压。", -1)),
            _createElementVNode$1("label", null, [
              _cache[16] || (_cache[16] = _createTextVNode$1("字幕文件", -1)),
              _createElementVNode$1("input", {
                ref_key: "input",
                ref: input,
                type: "file",
                accept: ".srt,.ass,.ssa,.zip",
                onChange: _cache[9] || (_cache[9] = e => { file.value=e.target.files[0]; members.value=[]; member.value=''; })
              }, null, 544)
            ]),
            (members.value.length)
              ? (_openBlock$1(), _createElementBlock$1("label", _hoisted_22, [
                  _cache[18] || (_cache[18] = _createTextVNode$1("压缩包成员", -1)),
                  _withDirectives$1(_createElementVNode$1("select", {
                    "onUpdate:modelValue": _cache[10] || (_cache[10] = $event => ((member).value = $event))
                  }, [
                    _cache[17] || (_cache[17] = _createElementVNode$1("option", {
                      disabled: "",
                      value: ""
                    }, "请选择对应集数", -1)),
                    (_openBlock$1(true), _createElementBlock$1(_Fragment, null, _renderList(members.value, (name) => {
                      return (_openBlock$1(), _createElementBlock$1("option", { key: name }, _toDisplayString(name), 1))
                    }), 128))
                  ], 512), [
                    [_vModelSelect, member.value]
                  ])
                ]))
              : _createCommentVNode$1("", true),
            _createElementVNode$1("div", _hoisted_23, [
              _createElementVNode$1("label", null, [
                _cache[20] || (_cache[20] = _createTextVNode$1("用途", -1)),
                _withDirectives$1(_createElementVNode$1("select", {
                  "onUpdate:modelValue": _cache[11] || (_cache[11] = $event => ((role).value = $event))
                }, [...(_cache[19] || (_cache[19] = [
                  _createElementVNode$1("option", { value: "zh-Hans" }, "简中成品", -1),
                  _createElementVNode$1("option", { value: "zh-Hant" }, "繁中成品", -1),
                  _createElementVNode$1("option", { value: "zh-en" }, "中英成品", -1),
                  _createElementVNode$1("option", { value: "eng" }, "英文原稿，供 AI 翻译", -1)
                ]))], 512), [
                  [_vModelSelect, role.value]
                ])
              ]),
              _createElementVNode$1("button", {
                disabled: busy.value || !file.value || (members.value.length && !member.value),
                onClick: upload
              }, "上传到当前影片", 8, _hoisted_24)
            ])
          ]))
        : _createCommentVNode$1("", true)
    ], 512), [
      [_vShow$1, !showInventory.value]
    ])
  ]))
}
}

};
const MediaLibrary = /*#__PURE__*/_export_sfc(_sfc_main$1, [['__scopeId',"data-v-e390054f"]]);

const {createTextVNode:_createTextVNode,resolveComponent:_resolveComponent,withCtx:_withCtx,createVNode:_createVNode,createElementVNode:_createElementVNode,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,vShow:_vShow,withDirectives:_withDirectives,createElementBlock:_createElementBlock} = await importShared('vue');


const _hoisted_1 = { class: "hyrule-app" };
const _hoisted_2 = {
  class: "views",
  "aria-label": "海拉鲁页面"
};

const {ref} = await importShared('vue');


const _sfc_main = {
  __name: 'AppPage',
  props: { api: Object, pluginId: { type: String, default: 'SubtitleManualUpload' } },
  setup(__props) {



const showLibrary = ref(false);
const libraryOpened = ref(false);

function openLibrary() {
  libraryOpened.value = true;
  showLibrary.value = true;
}

return (_ctx, _cache) => {
  const _component_VBtn = _resolveComponent("VBtn");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createElementVNode("nav", _hoisted_2, [
      _createVNode(_component_VBtn, {
        variant: showLibrary.value ? 'text' : 'tonal',
        color: "primary",
        "aria-pressed": !showLibrary.value,
        onClick: _cache[0] || (_cache[0] = $event => (showLibrary.value = false))
      }, {
        default: _withCtx(() => [...(_cache[1] || (_cache[1] = [
          _createTextVNode("任务面板", -1)
        ]))]),
        _: 1
      }, 8, ["variant", "aria-pressed"]),
      _createVNode(_component_VBtn, {
        variant: showLibrary.value ? 'tonal' : 'text',
        color: "primary",
        "aria-pressed": showLibrary.value,
        onClick: openLibrary
      }, {
        default: _withCtx(() => [...(_cache[2] || (_cache[2] = [
          _createTextVNode("片库字幕", -1)
        ]))]),
        _: 1
      }, 8, ["variant", "aria-pressed"])
    ]),
    (!showLibrary.value)
      ? (_openBlock(), _createBlock(Page, {
          key: 0,
          api: __props.api,
          "plugin-id": __props.pluginId,
          show_switch: false,
          show_close: false
        }, null, 8, ["api", "plugin-id"]))
      : _createCommentVNode("", true),
    (libraryOpened.value)
      ? _withDirectives((_openBlock(), _createBlock(MediaLibrary, {
          key: 1,
          api: __props.api,
          "plugin-id": __props.pluginId
        }, null, 8, ["api", "plugin-id"])), [
          [_vShow, showLibrary.value]
        ])
      : _createCommentVNode("", true)
  ]))
}
}

};
const AppPage = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-c7cb5a1b"]]);

export { AppPage as default };
