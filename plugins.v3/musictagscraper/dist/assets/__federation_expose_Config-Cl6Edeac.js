import { importShared } from './__federation_fn_import-JrT3xvdd.js';

const {resolveComponent:_resolveComponent,createVNode:_createVNode,withCtx:_withCtx,createElementVNode:_createElementVNode,renderList:_renderList,Fragment:_Fragment,openBlock:_openBlock,createElementBlock:_createElementBlock,createTextVNode:_createTextVNode,toDisplayString:_toDisplayString,withModifiers:_withModifiers,createBlock:_createBlock} = await importShared('vue');


const _hoisted_1 = { class: "text-caption mb-1" };
const _hoisted_2 = { class: "text-caption mb-1" };

const {computed,onMounted,ref} = await importShared('vue');



const _sfc_main = {
  __name: 'Config',
  props: {
  initialConfig: { type: Object, default: () => ({}) },
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'MusicTagScraper' },
},
  emits: ['save', 'close'],
  setup(__props, { emit: __emit }) {

const props = __props;

const emit = __emit;

const DEFAULTS = {
  enabled: false,
  music_dirs: ['/vol2/1000/music'],
  exclude_dirs: [],
  sources: ['douban', 'musicbrainz', 'theaudiodb'],
  fill_tags: true,
  write_cover: true,
  write_folder_cover: true,
  folder_cover_names: ['cover.jpg'],
  write_lyrics: true,
  lrc_metadata: true,
  overwrite: false,
  overwrite_lyrics: false,
  min_score: 0.62,
  concurrency: 2,
  max_files_per_run: 200,
  schedule_hours: 0,
  notify: true,
  show_sidebar_nav: true,
  dashboard: true,
};

const base = computed(() => `plugin/${props.pluginId || 'MusicTagScraper'}`);
const saving = ref(false);
const config = ref({ ...DEFAULTS });
const dirsText = ref('/vol2/1000/music');
const excludeText = ref('');

const sourceItems = [
  { title: '豆瓣音乐（中文优先）', value: 'douban' },
  { title: 'MusicBrainz', value: 'musicbrainz' },
  { title: 'TheAudioDB', value: 'theaudiodb' },
];

const coverNameItems = [
  { title: 'cover.jpg（Navidrome / 群晖）', value: 'cover.jpg' },
  { title: 'folder.jpg（Windows / 飞牛）', value: 'folder.jpg' },
];

function unwrap(response) {
  if (response && Object.prototype.hasOwnProperty.call(response, 'data') && response.success !== undefined) {
    return response.data
  }
  return response?.data ?? response
}

function toList(value) {
  if (Array.isArray(value)) return value.map(item => String(item || '').trim()).filter(Boolean)
  if (!value) return []
  return String(value)
    .split(/\n|;|；/)
    .map(item => item.trim())
    .filter(Boolean)
}

function applyConfig(data) {
  const merged = { ...DEFAULTS, ...(data || {}) };
  config.value = merged;
  dirsText.value = toList(merged.music_dirs).join('\n');
  excludeText.value = toList(merged.exclude_dirs).join('\n');
}

async function loadConfig() {
  if (props.initialConfig && Object.keys(props.initialConfig).length) {
    applyConfig(props.initialConfig);
    return
  }
  if (!props.api?.get) {
    applyConfig({});
    return
  }
  try {
    applyConfig(unwrap(await props.api.get(`${base.value}/config`)));
  } catch (err) {
    applyConfig({});
  }
}

async function save() {
  saving.value = true;
  try {
    const payload = {
      ...config.value,
      music_dirs: toList(dirsText.value),
      exclude_dirs: toList(excludeText.value),
      sources: (config.value.sources || []).filter(Boolean),
      folder_cover_names: (config.value.folder_cover_names || []).filter(Boolean),
      concurrency: Number(config.value.concurrency || 2),
      max_files_per_run: Number(config.value.max_files_per_run || 200),
      schedule_hours: Number(config.value.schedule_hours || 0),
      min_score: Number(config.value.min_score || 0.62),
    };
    emit('save', payload);
  } finally {
    saving.value = false;
  }
}

onMounted(loadConfig);

return (_ctx, _cache) => {
  const _component_VSwitch = _resolveComponent("VSwitch");
  const _component_VCol = _resolveComponent("VCol");
  const _component_VRow = _resolveComponent("VRow");
  const _component_VTextarea = _resolveComponent("VTextarea");
  const _component_VCheckboxBtn = _resolveComponent("VCheckboxBtn");
  const _component_VDivider = _resolveComponent("VDivider");
  const _component_VAlert = _resolveComponent("VAlert");
  const _component_VSlider = _resolveComponent("VSlider");
  const _component_VTextField = _resolveComponent("VTextField");
  const _component_VSpacer = _resolveComponent("VSpacer");
  const _component_VBtn = _resolveComponent("VBtn");
  const _component_VContainer = _resolveComponent("VContainer");
  const _component_VForm = _resolveComponent("VForm");

  return (_openBlock(), _createBlock(_component_VForm, {
    onSubmit: _withModifiers(save, ["prevent"])
  }, {
    default: _withCtx(() => [
      _createVNode(_component_VContainer, { class: "pa-4" }, {
        default: _withCtx(() => [
          _createVNode(_component_VRow, null, {
            default: _withCtx(() => [
              _createVNode(_component_VCol, {
                cols: "12",
                md: "6"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VSwitch, {
                    modelValue: config.value.enabled,
                    "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((config.value.enabled) = $event)),
                    label: "启用插件",
                    color: "primary",
                    "hide-details": "",
                    class: "mb-2"
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              }),
              _createVNode(_component_VCol, {
                cols: "12",
                md: "6"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VSwitch, {
                    modelValue: config.value.show_sidebar_nav,
                    "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((config.value.show_sidebar_nav) = $event)),
                    label: "显示侧栏入口",
                    color: "primary",
                    "hide-details": "",
                    class: "mb-2"
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              })
            ]),
            _: 1
          }),
          _createVNode(_component_VTextarea, {
            modelValue: dirsText.value,
            "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((dirsText).value = $event)),
            label: "音乐目录（每行一个）",
            rows: "3",
            variant: "outlined",
            density: "comfortable",
            hint: "支持多个目录；子目录会自动递归扫描",
            "persistent-hint": "",
            class: "mb-3"
          }, null, 8, ["modelValue"]),
          _createVNode(_component_VTextarea, {
            modelValue: excludeText.value,
            "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((excludeText).value = $event)),
            label: "排除目录（每行一个，可留空）",
            rows: "2",
            variant: "outlined",
            density: "comfortable",
            hint: "例如 MV 目录、试听目录",
            "persistent-hint": "",
            class: "mb-3"
          }, null, 8, ["modelValue"]),
          _cache[24] || (_cache[24] = _createElementVNode("div", { class: "text-subtitle-2 mb-2" }, "元数据来源（按顺序回退）", -1)),
          (_openBlock(), _createElementBlock(_Fragment, null, _renderList(sourceItems, (item) => {
            return _createVNode(_component_VCheckboxBtn, {
              key: item.value,
              modelValue: config.value.sources,
              "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((config.value.sources) = $event)),
              label: item.title,
              value: item.value,
              color: "primary",
              inline: ""
            }, null, 8, ["modelValue", "label", "value"])
          }), 64)),
          _createVNode(_component_VDivider, { class: "my-3" }),
          _createVNode(_component_VRow, null, {
            default: _withCtx(() => [
              _createVNode(_component_VCol, {
                cols: "12",
                md: "3"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VSwitch, {
                    modelValue: config.value.fill_tags,
                    "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((config.value.fill_tags) = $event)),
                    label: "补全音频标签",
                    color: "primary",
                    "hide-details": ""
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              }),
              _createVNode(_component_VCol, {
                cols: "12",
                md: "3"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VSwitch, {
                    modelValue: config.value.write_cover,
                    "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((config.value.write_cover) = $event)),
                    label: "补齐内嵌封面",
                    color: "primary",
                    "hide-details": ""
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              }),
              _createVNode(_component_VCol, {
                cols: "12",
                md: "3"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VSwitch, {
                    modelValue: config.value.write_folder_cover,
                    "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => ((config.value.write_folder_cover) = $event)),
                    label: "写专辑目录封面",
                    color: "primary",
                    "hide-details": ""
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              }),
              _createVNode(_component_VCol, {
                cols: "12",
                md: "3"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VSwitch, {
                    modelValue: config.value.write_lyrics,
                    "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => ((config.value.write_lyrics) = $event)),
                    label: "写入歌词（.lrc）",
                    color: "primary",
                    "hide-details": ""
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              })
            ]),
            _: 1
          }),
          _cache[25] || (_cache[25] = _createElementVNode("div", { class: "text-caption text-medium-emphasis mt-3 mb-1" }, "目录封面文件名（可多选）", -1)),
          (_openBlock(), _createElementBlock(_Fragment, null, _renderList(coverNameItems, (item) => {
            return _createVNode(_component_VCheckboxBtn, {
              key: item.value,
              modelValue: config.value.folder_cover_names,
              "onUpdate:modelValue": _cache[9] || (_cache[9] = $event => ((config.value.folder_cover_names) = $event)),
              label: item.title,
              value: item.value,
              color: "primary",
              inline: ""
            }, null, 8, ["modelValue", "label", "value"])
          }), 64)),
          _createVNode(_component_VAlert, {
            type: "info",
            variant: "tonal",
            density: "compact",
            class: "mt-2 mb-1"
          }, {
            default: _withCtx(() => [...(_cache[20] || (_cache[20] = [
              _createTextVNode(" 目录封面只在专辑目录没有 cover/folder 图片时补写：优先在线封面，缺失时从音频内嵌封面提取， 不覆盖已有图片（除非勾选「覆盖已有标签」）。 ", -1)
            ]))]),
            _: 1
          }),
          _createVNode(_component_VRow, { class: "mt-2" }, {
            default: _withCtx(() => [
              _createVNode(_component_VCol, {
                cols: "12",
                md: "4"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VSwitch, {
                    modelValue: config.value.overwrite,
                    "onUpdate:modelValue": _cache[10] || (_cache[10] = $event => ((config.value.overwrite) = $event)),
                    label: "覆盖已有标签",
                    color: "warning",
                    "hide-details": ""
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              }),
              _createVNode(_component_VCol, {
                cols: "12",
                md: "4"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VSwitch, {
                    modelValue: config.value.overwrite_lyrics,
                    "onUpdate:modelValue": _cache[11] || (_cache[11] = $event => ((config.value.overwrite_lyrics) = $event)),
                    label: "覆盖已有歌词",
                    color: "warning",
                    "hide-details": ""
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              }),
              _createVNode(_component_VCol, {
                cols: "12",
                md: "4"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VSwitch, {
                    modelValue: config.value.lrc_metadata,
                    "onUpdate:modelValue": _cache[12] || (_cache[12] = $event => ((config.value.lrc_metadata) = $event)),
                    label: "歌词写入 LRC 头部信息",
                    color: "primary",
                    "hide-details": ""
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              })
            ]),
            _: 1
          }),
          _createVNode(_component_VRow, { class: "mt-2" }, {
            default: _withCtx(() => [
              _createVNode(_component_VCol, {
                cols: "12",
                md: "4"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VSwitch, {
                    modelValue: config.value.notify,
                    "onUpdate:modelValue": _cache[13] || (_cache[13] = $event => ((config.value.notify) = $event)),
                    label: "完成后通知",
                    color: "primary",
                    "hide-details": ""
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              }),
              _createVNode(_component_VCol, {
                cols: "12",
                md: "4"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VSwitch, {
                    modelValue: config.value.dashboard,
                    "onUpdate:modelValue": _cache[14] || (_cache[14] = $event => ((config.value.dashboard) = $event)),
                    label: "首页显示仪表板",
                    color: "primary",
                    "hide-details": ""
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              })
            ]),
            _: 1
          }),
          _createVNode(_component_VRow, { class: "mt-2" }, {
            default: _withCtx(() => [
              _createVNode(_component_VCol, {
                cols: "12",
                md: "4"
              }, {
                default: _withCtx(() => [
                  _createElementVNode("div", _hoisted_1, "匹配阈值：" + _toDisplayString(Number(config.value.min_score).toFixed(2)), 1),
                  _createVNode(_component_VSlider, {
                    modelValue: config.value.min_score,
                    "onUpdate:modelValue": _cache[15] || (_cache[15] = $event => ((config.value.min_score) = $event)),
                    min: 0.3,
                    max: 1,
                    step: 0.01,
                    "thumb-label": "",
                    "hide-details": ""
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              }),
              _createVNode(_component_VCol, {
                cols: "12",
                md: "4"
              }, {
                default: _withCtx(() => [
                  _createElementVNode("div", _hoisted_2, "并发：" + _toDisplayString(config.value.concurrency), 1),
                  _createVNode(_component_VSlider, {
                    modelValue: config.value.concurrency,
                    "onUpdate:modelValue": _cache[16] || (_cache[16] = $event => ((config.value.concurrency) = $event)),
                    min: 1,
                    max: 8,
                    step: 1,
                    "thumb-label": "",
                    "hide-details": ""
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              }),
              _createVNode(_component_VCol, {
                cols: "12",
                md: "4"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VTextField, {
                    modelValue: config.value.max_files_per_run,
                    "onUpdate:modelValue": _cache[17] || (_cache[17] = $event => ((config.value.max_files_per_run) = $event)),
                    modelModifiers: { number: true },
                    label: "单次最多处理音频数",
                    type: "number",
                    density: "comfortable",
                    variant: "outlined",
                    "hide-details": ""
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              })
            ]),
            _: 1
          }),
          _createVNode(_component_VRow, { class: "mt-3" }, {
            default: _withCtx(() => [
              _createVNode(_component_VCol, {
                cols: "12",
                md: "4"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VTextField, {
                    modelValue: config.value.schedule_hours,
                    "onUpdate:modelValue": _cache[18] || (_cache[18] = $event => ((config.value.schedule_hours) = $event)),
                    modelModifiers: { number: true },
                    label: "定时补全间隔（小时，0=关闭）",
                    type: "number",
                    density: "comfortable",
                    variant: "outlined",
                    hint: "例如 24 表示每天补一次",
                    "persistent-hint": ""
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              })
            ]),
            _: 1
          }),
          _createVNode(_component_VAlert, {
            type: "info",
            variant: "tonal",
            density: "compact",
            class: "mt-4"
          }, {
            default: _withCtx(() => [...(_cache[21] || (_cache[21] = [
              _createTextVNode(" 插件只写音频文件的标签与同名 .lrc 歌词，不重命名、不移动、不删除；默认「只补空缺」， 勾选覆盖才会改写已有内容。试跑只扫描不写入。 ", -1)
            ]))]),
            _: 1
          }),
          _createVNode(_component_VRow, { class: "mt-4" }, {
            default: _withCtx(() => [
              _createVNode(_component_VSpacer),
              _createVNode(_component_VBtn, {
                variant: "text",
                onClick: _cache[19] || (_cache[19] = $event => (emit('close')))
              }, {
                default: _withCtx(() => [...(_cache[22] || (_cache[22] = [
                  _createTextVNode("关闭", -1)
                ]))]),
                _: 1
              }),
              _createVNode(_component_VBtn, {
                color: "primary",
                variant: "tonal",
                loading: saving.value,
                onClick: save
              }, {
                default: _withCtx(() => [...(_cache[23] || (_cache[23] = [
                  _createTextVNode("保存配置", -1)
                ]))]),
                _: 1
              }, 8, ["loading"])
            ]),
            _: 1
          })
        ]),
        _: 1
      })
    ]),
    _: 1
  }))
}
}

};

export { _sfc_main as default };
