import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import AppPage from './__federation_expose_AppPage-C8xrISwD.js';

const {resolveComponent:_resolveComponent,createVNode:_createVNode,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,withCtx:_withCtx,createElementBlock:_createElementBlock} = await importShared('vue');

const _sfc_main = {
  __name: 'Page',
  props: { api: Object, pluginId: String, show_switch: { type: Boolean, default: true } },
  emits: ['switch','close'],
  setup(__props) {




return (_ctx, _cache) => {
  const _component_VSpacer = _resolveComponent("VSpacer");
  const _component_VBtn = _resolveComponent("VBtn");
  const _component_VToolbar = _resolveComponent("VToolbar");

  return (_openBlock(), _createElementBlock("div", null, [
    _createVNode(_component_VToolbar, { density: "compact" }, {
      default: _withCtx(() => [
        _createVNode(_component_VSpacer),
        (__props.show_switch)
          ? (_openBlock(), _createBlock(_component_VBtn, {
              key: 0,
              "aria-label": "插件设置",
              icon: "mdi-cog-outline",
              onClick: _cache[0] || (_cache[0] = $event => (_ctx.$emit('switch')))
            }))
          : _createCommentVNode("", true),
        _createVNode(_component_VBtn, {
          "aria-label": "关闭",
          icon: "mdi-close",
          onClick: _cache[1] || (_cache[1] = $event => (_ctx.$emit('close')))
        })
      ]),
      _: 1
    }),
    _createVNode(AppPage, {
      api: __props.api,
      "plugin-id": __props.pluginId
    }, null, 8, ["api", "plugin-id"])
  ]))
}
}

};

export { _sfc_main as default };
