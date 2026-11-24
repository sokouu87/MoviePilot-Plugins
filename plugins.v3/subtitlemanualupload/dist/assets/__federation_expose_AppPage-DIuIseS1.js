import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import Page from './__federation_expose_Page-CaCAvuet.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-pcqpp-6-.js';

const {createElementVNode:_createElementVNode$1,toDisplayString:_toDisplayString,openBlock:_openBlock$1,createElementBlock:_createElementBlock$1,createCommentVNode:_createCommentVNode$1,vModelText:_vModelText,withDirectives:_withDirectives$1,renderList:_renderList,Fragment:_Fragment,createTextVNode:_createTextVNode$1,withModifiers:_withModifiers,vModelSelect:_vModelSelect} = await importShared('vue');


const _hoisted_1$1 = { class: "studio" };
const _hoisted_2$1 = {
  key: 0,
  role: "status"
};
const _hoisted_3 = {
  key: 1,
  class: "err",
  role: "alert"
};
const _hoisted_4 = {
  key: 2,
  role: "status"
};
const _hoisted_5 = { class: "row" };
const _hoisted_6 = ["disabled"];
const _hoisted_7 = { class: "choices" };
const _hoisted_8 = ["disabled", "aria-pressed", "onClick"];
const _hoisted_9 = { key: 0 };
const _hoisted_10 = { key: 3 };
const _hoisted_11 = { class: "filename" };
const _hoisted_12 = { class: "row" };
const _hoisted_13 = ["disabled"];
const _hoisted_14 = ["disabled"];
const _hoisted_15 = ["disabled"];
const _hoisted_16 = ["onUpdate:modelValue"];
const _hoisted_17 = ["disabled"];
const _hoisted_18 = ["disabled"];
const _hoisted_19 = ["href"];
const _hoisted_20 = { key: 2 };
const _hoisted_21 = { class: "row" };
const _hoisted_22 = ["disabled"];

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
      _cache[11] || (_cache[11] = _createElementVNode$1("h2", null, "海拉鲁 AI 字幕", -1)),
      _createElementVNode$1("span", null, _toDisplayString(account.value), 1)
    ]),
    (!configured.value)
      ? (_openBlock$1(), _createElementBlock$1("p", _hoisted_2$1, "请在插件设置中填入本机订阅线路密钥，或启用已配置的 AutoSubv3 订阅线路。"))
      : _createCommentVNode$1("", true),
    (error.value)
      ? (_openBlock$1(), _createElementBlock$1("p", _hoisted_3, _toDisplayString(error.value), 1))
      : _createCommentVNode$1("", true),
    (message.value)
      ? (_openBlock$1(), _createElementBlock$1("p", _hoisted_4, _toDisplayString(message.value), 1))
      : _createCommentVNode$1("", true),
    _createElementVNode$1("section", null, [
      _cache[12] || (_cache[12] = _createElementVNode$1("h3", null, "选择影片或剧集", -1)),
      _createElementVNode$1("div", _hoisted_5, [
        _withDirectives$1(_createElementVNode$1("input", {
          "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((query).value = $event)),
          type: "search",
          "aria-label": "搜索媒体",
          placeholder: "输入片名、集数或文件名"
        }, null, 512), [
          [_vModelText, query.value]
        ]),
        _createElementVNode$1("button", {
          disabled: busy.value || index.value,
          onClick: _cache[1] || (_cache[1] = $event => {act(async () => { await api('post','refresh',{}); await list(); });})
        }, _toDisplayString(index.value ? '正在索引…' : '刷新媒体'), 9, _hoisted_6)
      ]),
      _createElementVNode$1("ul", _hoisted_7, [
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
            ], 8, _hoisted_8)
          ]))
        }), 128))
      ]),
      (!rows.value.length)
        ? (_openBlock$1(), _createElementBlock$1("p", _hoisted_9, _toDisplayString(index.value ? '正在读取媒体库…' : '没有匹配的媒体'), 1))
        : _createCommentVNode$1("", true),
      (more.value)
        ? (_openBlock$1(), _createElementBlock$1("button", {
            key: 1,
            onClick: _cache[2] || (_cache[2] = $event => (list(true)))
          }, "更多结果"))
        : _createCommentVNode$1("", true)
    ]),
    (selected.value)
      ? (_openBlock$1(), _createElementBlock$1("section", _hoisted_10, [
          _createElementVNode$1("h3", null, _toDisplayString(selected.value.label), 1),
          _createElementVNode$1("p", _hoisted_11, _toDisplayString(selected.value.file), 1),
          _createElementVNode$1("div", _hoisted_12, [
            _createElementVNode$1("button", {
              class: "primary",
              disabled: busy.value || !configured.value,
              onClick: translate
            }, "AI 翻译", 8, _hoisted_13),
            _createElementVNode$1("button", {
              disabled: busy.value,
              onClick: editGlossary
            }, "本剧译名表", 8, _hoisted_14),
            _createElementVNode$1("button", {
              disabled: busy.value,
              onClick: _cache[3] || (_cache[3] = $event => (meta.value = {...selected.value.meta}))
            }, "作品资料", 8, _hoisted_15)
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
                    }, null, 8, _hoisted_16), [
                      [_vModelText, meta.value[k]]
                    ])
                  ])
                }), 64)),
                _createElementVNode$1("button", { disabled: busy.value }, "保存资料", 8, _hoisted_17),
                _createElementVNode$1("button", {
                  type: "button",
                  onClick: _cache[4] || (_cache[4] = $event => (meta.value=null))
                }, "取消")
              ], 32))
            : _createCommentVNode$1("", true),
          (glossary.value !== null)
            ? (_openBlock$1(), _createElementBlock$1("form", {
                key: 1,
                onSubmit: _withModifiers(saveGlossary, ["prevent"])
              }, [
                _createElementVNode$1("label", null, [
                  _cache[13] || (_cache[13] = _createTextVNode$1("译名表 JSON", -1)),
                  _withDirectives$1(_createElementVNode$1("textarea", {
                    "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((glossary).value = $event)),
                    rows: "10"
                  }, null, 512), [
                    [_vModelText, glossary.value]
                  ])
                ]),
                _createElementVNode$1("label", null, [
                  _cache[14] || (_cache[14] = _createTextVNode$1("从文件导入", -1)),
                  _createElementVNode$1("input", {
                    type: "file",
                    accept: ".json",
                    onChange: _cache[6] || (_cache[6] = e => act(async () => { const f = e.target.files[0]; if (f) glossary.value = await f.text(); }))
                  }, null, 32)
                ]),
                _createElementVNode$1("button", { disabled: busy.value }, "保存译名表", 8, _hoisted_18),
                _createElementVNode$1("button", {
                  type: "button",
                  onClick: _cache[7] || (_cache[7] = $event => (glossary.value=null))
                }, "取消")
              ], 32))
            : _createCommentVNode$1("", true),
          _cache[20] || (_cache[20] = _createElementVNode$1("h4", null, "SubHD 手动字幕", -1)),
          _createElementVNode$1("a", {
            href: selected.value.search_url,
            target: "_blank",
            rel: "noopener noreferrer"
          }, "在 SubHD 搜索 ↗", 8, _hoisted_19),
          _cache[21] || (_cache[21] = _createElementVNode$1("p", null, "到官网完成验证和下载，回到此处上传到上方影片。RAR 或 7z 请先解压。", -1)),
          _createElementVNode$1("label", null, [
            _cache[15] || (_cache[15] = _createTextVNode$1("字幕文件", -1)),
            _createElementVNode$1("input", {
              ref_key: "input",
              ref: input,
              type: "file",
              accept: ".srt,.ass,.ssa,.zip",
              onChange: _cache[8] || (_cache[8] = e => { file.value=e.target.files[0]; members.value=[]; member.value=''; })
            }, null, 544)
          ]),
          (members.value.length)
            ? (_openBlock$1(), _createElementBlock$1("label", _hoisted_20, [
                _cache[17] || (_cache[17] = _createTextVNode$1("压缩包成员", -1)),
                _withDirectives$1(_createElementVNode$1("select", {
                  "onUpdate:modelValue": _cache[9] || (_cache[9] = $event => ((member).value = $event))
                }, [
                  _cache[16] || (_cache[16] = _createElementVNode$1("option", {
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
          _createElementVNode$1("div", _hoisted_21, [
            _createElementVNode$1("label", null, [
              _cache[19] || (_cache[19] = _createTextVNode$1("用途", -1)),
              _withDirectives$1(_createElementVNode$1("select", {
                "onUpdate:modelValue": _cache[10] || (_cache[10] = $event => ((role).value = $event))
              }, [...(_cache[18] || (_cache[18] = [
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
            }, "上传到当前影片", 8, _hoisted_22)
          ])
        ]))
      : _createCommentVNode$1("", true)
  ]))
}
}

};
const MediaLibrary = /*#__PURE__*/_export_sfc(_sfc_main$1, [['__scopeId',"data-v-923f2e82"]]);

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
