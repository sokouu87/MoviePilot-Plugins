import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import Page from './__federation_expose_Page-CMgAoxvD.js';

const {openBlock:_openBlock,createBlock:_createBlock} = await importShared('vue');


const _sfc_main = {
  __name: 'Dashboard',
  props: { api: Object, config: Object, allowRefresh: { type: Boolean, default: true } },
  setup(__props) {



return (_ctx, _cache) => {
  return (_openBlock(), _createBlock(Page, {
    api: __props.api,
    "plugin-id": __props.config?.id || 'SubtitleManualUpload',
    "allow-refresh": __props.allowRefresh,
    compact: "",
    show_switch: false,
    show_close: false
  }, null, 8, ["api", "plugin-id", "allow-refresh"]))
}
}

};

export { _sfc_main as default };
