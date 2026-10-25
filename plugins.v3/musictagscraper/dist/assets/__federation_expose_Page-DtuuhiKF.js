import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { _ as _export_sfc, P as Panel } from './Panel-DP2CfRiy.js';

const {createElementVNode:_createElementVNode,resolveComponent:_resolveComponent,createVNode:_createVNode,mergeProps:_mergeProps,withCtx:_withCtx,openBlock:_openBlock,createElementBlock:_createElementBlock} = await importShared('vue');


const _hoisted_1 = { class: "mts-page-wrapper" };


const _sfc_main = {
  __name: 'Page',
  props: {
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'MusicTagScraper' },
  navKey: { type: String, default: 'main' },
},
  emits: ['close', 'switch'],
  setup(__props, { emit: __emit }) {

const props = __props;

const emit = __emit;

return (_ctx, _cache) => {
  const _component_VSpacer = _resolveComponent("VSpacer");
  const _component_VBtn = _resolveComponent("VBtn");
  const _component_VTooltip = _resolveComponent("VTooltip");
  const _component_VToolbar = _resolveComponent("VToolbar");
  const _component_VDivider = _resolveComponent("VDivider");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createVNode(_component_VToolbar, {
      density: "comfortable",
      class: "mts-toolbar"
    }, {
      default: _withCtx(() => [
        _cache[2] || (_cache[2] = _createElementVNode("div", { class: "text-h6 ms-3" }, "音乐标签刮削", -1)),
        _createVNode(_component_VSpacer),
        _createVNode(_component_VTooltip, {
          text: "插件设置",
          location: "bottom"
        }, {
          activator: _withCtx(({ props: tooltipProps }) => [
            _createVNode(_component_VBtn, _mergeProps(tooltipProps, {
              icon: "mdi-cog-outline",
              variant: "text",
              "aria-label": "插件设置",
              onClick: _cache[0] || (_cache[0] = $event => (emit('switch')))
            }), null, 16)
          ]),
          _: 1
        }),
        _createVNode(_component_VBtn, {
          icon: "mdi-close",
          variant: "text",
          "aria-label": "关闭",
          onClick: _cache[1] || (_cache[1] = $event => (emit('close')))
        })
      ]),
      _: 1
    }),
    _createVNode(_component_VDivider),
    _createVNode(Panel, {
      api: props.api,
      "plugin-id": props.pluginId,
      compact: ""
    }, null, 8, ["api", "plugin-id"])
  ]))
}
}

};
const Page = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-ddcdecb0"]]);

export { Page as default };
