import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { P as Panel } from './Panel-YdzmuVr7.js';

const {openBlock:_openBlock,createBlock:_createBlock} = await importShared('vue');


const _sfc_main = {
  __name: 'AppPage',
  props: {
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'MusicTagScraper' },
  navKey: { type: String, default: 'main' },
},
  setup(__props) {

const props = __props;

return (_ctx, _cache) => {
  return (_openBlock(), _createBlock(Panel, {
    api: props.api,
    "plugin-id": props.pluginId
  }, null, 8, ["api", "plugin-id"]))
}
}

};

export { _sfc_main as default };
