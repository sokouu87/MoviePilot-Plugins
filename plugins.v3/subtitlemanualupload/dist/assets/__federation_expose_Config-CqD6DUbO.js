import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-pcqpp-6-.js';

const {createElementVNode:_createElementVNode,vModelCheckbox:_vModelCheckbox,withDirectives:_withDirectives,createTextVNode:_createTextVNode,renderList:_renderList,Fragment:_Fragment,openBlock:_openBlock,createElementBlock:_createElementBlock,toDisplayString:_toDisplayString,createCommentVNode:_createCommentVNode,vModelSelect:_vModelSelect,vModelText:_vModelText,resolveComponent:_resolveComponent,withCtx:_withCtx,createVNode:_createVNode,withModifiers:_withModifiers} = await importShared('vue');


const _hoisted_1 = ["value"];
const _hoisted_2 = ["value"];

const {ref,watch} = await importShared('vue');


const _sfc_main = {
  __name: 'Config',
  props: {initialConfig:{type:Object,default:()=>({})},saving:Boolean},
  emits: ['save','close'],
  setup(__props, { emit: __emit }) {

const props=__props;
const emit=__emit;
const models=['gpt-6.2-astra', 'gpt-6.2-sol'];
const data=ref({});
watch(()=>props.initialConfig, (value)=>{
  const v=value || {};
  data.value={...v, enabled:v.enabled ?? false, auto_translate:v.auto_translate ?? v.auto_search_on_transfer ?? true,
    show_sidebar_nav:v.show_sidebar_nav ?? true, model:v.model || 'gpt-6.2-astra', effort:v.effort || 'high',
    bridge_key:v.bridge_key || '', whisper:v.whisper || '', banned:v.banned ?? '破防、内卷、绝绝子、老铁、诸葛亮、塞翁失马、三顾茅庐',
    manual_dirs:v.manual_dirs ?? (v.manual_strm_enabled ? [].concat(v.manual_strm_paths || []).join('\n') : ''),
    emby_directory_map:v.emby_directory_map || ''};
},{immediate:true});

return (_ctx, _cache) => {
  const _component_VBtn = _resolveComponent("VBtn");

  return (_openBlock(), _createElementBlock("form", {
    class: "options",
    onSubmit: _cache[11] || (_cache[11] = _withModifiers($event => (emit('save', {...data.value, auto_search_on_transfer: data.value.auto_translate})), ["prevent"]))
  }, [
    _cache[25] || (_cache[25] = _createElementVNode("h3", null, "海拉鲁 AI 字幕设置", -1)),
    _createElementVNode("label", null, [
      _withDirectives(_createElementVNode("input", {
        "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((data.value.enabled) = $event)),
        type: "checkbox"
      }, null, 512), [
        [_vModelCheckbox, data.value.enabled]
      ]),
      _cache[12] || (_cache[12] = _createTextVNode(" 启用插件", -1))
    ]),
    _createElementVNode("label", null, [
      _withDirectives(_createElementVNode("input", {
        "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((data.value.auto_translate) = $event)),
        type: "checkbox"
      }, null, 512), [
        [_vModelCheckbox, data.value.auto_translate]
      ]),
      _cache[13] || (_cache[13] = _createTextVNode(" 入库后自动翻译", -1))
    ]),
    _createElementVNode("label", null, [
      _withDirectives(_createElementVNode("input", {
        "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((data.value.show_sidebar_nav) = $event)),
        type: "checkbox"
      }, null, 512), [
        [_vModelCheckbox, data.value.show_sidebar_nav]
      ]),
      _cache[14] || (_cache[14] = _createTextVNode(" 在侧栏显示", -1))
    ]),
    _createElementVNode("label", null, [
      _cache[15] || (_cache[15] = _createTextVNode("订阅模型 ", -1)),
      _withDirectives(_createElementVNode("select", {
        "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((data.value.model) = $event)),
        required: ""
      }, [
        (_openBlock(), _createElementBlock(_Fragment, null, _renderList(models, (model) => {
          return _createElementVNode("option", {
            key: model,
            value: model
          }, _toDisplayString(model), 9, _hoisted_1)
        }), 64)),
        (__props.initialConfig?.model && !models.includes(__props.initialConfig.model))
          ? (_openBlock(), _createElementBlock("option", {
              key: 0,
              value: __props.initialConfig.model
            }, _toDisplayString(__props.initialConfig.model) + "（当前配置）", 9, _hoisted_2))
          : _createCommentVNode("", true)
      ], 512), [
        [_vModelSelect, data.value.model]
      ])
    ]),
    _createElementVNode("label", null, [
      _cache[17] || (_cache[17] = _createTextVNode("推理档位", -1)),
      _withDirectives(_createElementVNode("select", {
        "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((data.value.effort) = $event))
      }, [...(_cache[16] || (_cache[16] = [
        _createElementVNode("option", null, "medium", -1),
        _createElementVNode("option", null, "high", -1),
        _createElementVNode("option", null, "xhigh", -1)
      ]))], 512), [
        [_vModelSelect, data.value.effort]
      ])
    ]),
    _createElementVNode("label", null, [
      _cache[18] || (_cache[18] = _createTextVNode("本机订阅服务密钥", -1)),
      _withDirectives(_createElementVNode("input", {
        "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((data.value.bridge_key) = $event)),
        type: "password",
        autocomplete: "new-password",
        placeholder: "已配置旧订阅线路时可留空"
      }, null, 512), [
        [
          _vModelText,
          data.value.bridge_key,
          void 0,
          { trim: true }
        ]
      ])
    ]),
    _createElementVNode("label", null, [
      _cache[19] || (_cache[19] = _createTextVNode("Whisper 模型目录", -1)),
      _withDirectives(_createElementVNode("input", {
        "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((data.value.whisper) = $event)),
        placeholder: "留空使用 AutoSubv3 已缓存的模型"
      }, null, 512), [
        [
          _vModelText,
          data.value.whisper,
          void 0,
          { trim: true }
        ]
      ])
    ]),
    _createElementVNode("label", null, [
      _cache[20] || (_cache[20] = _createTextVNode("额外 STRM 目录，每行一条", -1)),
      _withDirectives(_createElementVNode("textarea", {
        "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => ((data.value.manual_dirs) = $event)),
        rows: "2"
      }, null, 512), [
        [_vModelText, data.value.manual_dirs]
      ])
    ]),
    _createElementVNode("label", null, [
      _cache[21] || (_cache[21] = _createTextVNode("Emby 目录映射，每行一条", -1)),
      _withDirectives(_createElementVNode("textarea", {
        "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => ((data.value.emby_directory_map) = $event)),
        rows: "2",
        placeholder: "/Emby目录=/MoviePilot目录"
      }, null, 512), [
        [_vModelText, data.value.emby_directory_map]
      ])
    ]),
    _createElementVNode("label", null, [
      _cache[22] || (_cache[22] = _createTextVNode("翻译禁用词，以顿号或换行分隔", -1)),
      _withDirectives(_createElementVNode("textarea", {
        "onUpdate:modelValue": _cache[9] || (_cache[9] = $event => ((data.value.banned) = $event)),
        rows: "2"
      }, null, 512), [
        [_vModelText, data.value.banned]
      ])
    ]),
    _createVNode(_component_VBtn, {
      type: "submit",
      color: "primary",
      loading: __props.saving
    }, {
      default: _withCtx(() => [...(_cache[23] || (_cache[23] = [
        _createTextVNode("保存", -1)
      ]))]),
      _: 1
    }, 8, ["loading"]),
    _cache[26] || (_cache[26] = _createTextVNode()),
    _createVNode(_component_VBtn, {
      disabled: __props.saving,
      onClick: _cache[10] || (_cache[10] = $event => (emit('close')))
    }, {
      default: _withCtx(() => [...(_cache[24] || (_cache[24] = [
        _createTextVNode("关闭", -1)
      ]))]),
      _: 1
    }, 8, ["disabled"])
  ], 32))
}
}

};
const Config = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-ad7087df"]]);

export { Config as default };
