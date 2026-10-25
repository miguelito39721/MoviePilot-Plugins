import { importShared } from './__federation_fn_import-JrT3xvdd.js';

const _export_sfc = (sfc, props) => {
  const target = sfc.__vccOpts || sfc;
  for (const [key, val] of props) {
    target[key] = val;
  }
  return target;
};

const {resolveComponent:_resolveComponent,createVNode:_createVNode,createElementVNode:_createElementVNode,withCtx:_withCtx,createTextVNode:_createTextVNode,renderList:_renderList,Fragment:_Fragment,openBlock:_openBlock,createElementBlock:_createElementBlock,toDisplayString:_toDisplayString,createBlock:_createBlock,createCommentVNode:_createCommentVNode,normalizeClass:_normalizeClass} = await importShared('vue');


const _hoisted_1 = { class: "d-flex align-center ga-2" };
const _hoisted_2 = { class: "text-caption" };
const _hoisted_3 = { class: "text-h5" };
const _hoisted_4 = { class: "d-flex align-center justify-space-between mb-2" };
const _hoisted_5 = { class: "text-body-2" };
const _hoisted_6 = { class: "text-body-2" };
const _hoisted_7 = { class: "text-body-2 text-success" };
const _hoisted_8 = { class: "text-body-2 text-info" };
const _hoisted_9 = { class: "text-body-2 text-medium-emphasis" };
const _hoisted_10 = { class: "text-body-2 text-error" };
const _hoisted_11 = { class: "text-caption text-medium-emphasis" };
const _hoisted_12 = { class: "text-caption" };
const _hoisted_13 = { class: "text-caption text-error" };
const _hoisted_14 = { class: "text-caption" };
const _hoisted_15 = {
  key: 0,
  class: "text-caption text-medium-emphasis"
};
const _hoisted_16 = { class: "text-medium-emphasis" };
const _hoisted_17 = {
  key: 0,
  class: "d-flex flex-wrap ga-3 mt-2"
};
const _hoisted_18 = { class: "text-caption text-medium-emphasis" };
const _hoisted_19 = {
  key: 0,
  class: "d-flex flex-wrap ga-3 mb-3"
};
const _hoisted_20 = { class: "d-flex align-center flex-wrap ga-2 mb-1" };
const _hoisted_21 = { class: "text-body-2" };
const _hoisted_22 = {
  key: 0,
  class: "text-medium-emphasis"
};
const _hoisted_23 = { class: "text-caption text-medium-emphasis" };
const _hoisted_24 = {
  class: "text-caption",
  style: {"word-break":"break-all"}
};
const _hoisted_25 = { class: "text-caption" };
const _hoisted_26 = { class: "text-caption" };
const _hoisted_27 = { class: "text-caption" };
const _hoisted_28 = { class: "text-caption text-medium-emphasis mt-2" };
const _hoisted_29 = { class: "text-caption text-medium-emphasis ms-4" };
const _hoisted_30 = {
  key: 0,
  class: "d-flex flex-wrap ga-3 mb-3"
};
const _hoisted_31 = { style: {"width":"44px"} };
const _hoisted_32 = { class: "text-caption" };
const _hoisted_33 = { class: "text-caption" };
const _hoisted_34 = { class: "text-caption" };
const _hoisted_35 = { class: "text-caption" };
const _hoisted_36 = {
  key: 0,
  class: "text-medium-emphasis"
};
const _hoisted_37 = {
  key: 1,
  class: "text-medium-emphasis"
};
const _hoisted_38 = { class: "text-caption" };
const _hoisted_39 = {
  key: 1,
  class: "text-medium-emphasis"
};
const _hoisted_40 = { class: "text-caption text-medium-emphasis ms-4" };

const {computed,onBeforeUnmount,onMounted,ref} = await importShared('vue');



const _sfc_main = {
  __name: 'Panel',
  props: {
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'MusicTagScraper' },
  compact: { type: Boolean, default: false },
},
  setup(__props) {

const props = __props;

const base = computed(() => `plugin/${props.pluginId || 'MusicTagScraper'}`);
const status = ref(null);
ref(false);
const busy = ref('');
const message = ref('');
const messageType = ref('info');
const showMessage = ref(false);
const previewDialog = ref(false);
const preview = ref(null);
const selected = ref([]);
const dedupeDialog = ref(false);
const dedupe = ref(null);
const dedupeSelected = ref([]);
ref(false);
let timer = null;
let dedupeTimer = null;

function unwrap(response) {
  if (response && Object.prototype.hasOwnProperty.call(response, 'data') && response.success !== undefined) {
    return response.data
  }
  return response?.data ?? response
}

function errorText(err) {
  if (!err) return '未知错误'
  return err.message || String(err)
}

function notify(text, type = 'info') {
  message.value = text;
  messageType.value = type;
  showMessage.value = true;
}

async function refresh() {
  if (!props.api?.get) return
  try {
    status.value = unwrap(await props.api.get(`${base.value}/status`));
  } catch (err) {
    notify(`读取状态失败：${errorText(err)}`, 'error');
  }
}

async function doPreview() {
  if (!props.api?.post) return
  busy.value = 'preview';
  try {
    const data = unwrap(await props.api.post(`${base.value}/preview`, { body: { sample: 8 } }));
    preview.value = data;
    selected.value = (data?.items || []).map(item => item.key);
    previewDialog.value = true;
    if (!data?.items?.length) {
      notify(data?.stats ? `扫描 ${data.stats.scanned} 个音频，暂无待处理` : '暂无待处理音频', 'info');
    }
  } catch (err) {
    notify(`试跑失败：${errorText(err)}`, 'error');
  } finally {
    busy.value = '';
  }
}

async function doRun(paths = []) {
  if (!props.api?.post) return
  busy.value = 'run';
  try {
    const body = Array.isArray(paths) && paths.length ? { paths, limit: paths.length, force: true } : {};
    const data = unwrap(await props.api.post(`${base.value}/run`, { body }));
    notify(
      data?.started
        ? `已启动，待处理 ${data.total} 个音频`
        : data?.message || '未能启动',
      data?.started ? 'success' : 'warning',
    );
    await refresh();
    if (data?.started) startPolling();
  } catch (err) {
    notify(`启动失败：${errorText(err)}`, 'error');
  } finally {
    busy.value = '';
  }
}

async function doRunSelected() {
  if (!selected.value.length) {
    notify('请先勾选需要处理的音频', 'warning');
    return
  }
  previewDialog.value = false;
  await doRun(selected.value);
}

async function retryOne(item) {
  if (!props.api?.post) return
  busy.value = `retry:${item.key}`;
  try {
    const data = unwrap(await props.api.post(`${base.value}/retry`, { body: { keys: [item.key] } }));
    notify(data?.started ? '已重试该条' : data?.message || '无法重试', data?.started ? 'success' : 'warning');
    await refresh();
    if (data?.started) startPolling();
  } catch (err) {
    notify(`重试失败：${errorText(err)}`, 'error');
  } finally {
    busy.value = '';
  }
}

function toggleAll() {
  const items = preview.value?.items || [];
  selected.value = selected.value.length === items.length ? [] : items.map(item => item.key);
}

const allSelected = computed(() => {
  const items = preview.value?.items || [];
  return items.length > 0 && selected.value.length === items.length
});

function formatSize(bytes) {
  const value = Number(bytes || 0);
  if (!value) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let index = 0;
  let size = value;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}

async function doDetect() {
  if (!props.api?.post) return
  busy.value = 'dedupe';
  try {
    const data = unwrap(await props.api.post(`${base.value}/duplicates`, { body: {} }));
    if (data?.groups) {
      applyDedupe(data);
      return
    }
    if (data?.started === false && !data?.running) {
      notify(data?.message || '无法开始查重', 'warning');
      return
    }
    notify(data?.running ? '查重已开始，扫描完成后自动打开结果' : '查重已开始', 'info');
    await refresh();
    stopDedupePolling();
    dedupeTimer = setInterval(pollDedupe, 2500);
  } catch (err) {
    notify(`查重失败：${errorText(err)}`, 'error');
  } finally {
    busy.value = '';
  }
}

function applyDedupe(data) {
  dedupe.value = data;
  dedupeSelected.value = (data?.groups || []).flatMap(group => group.duplicates || []);
  dedupeDialog.value = true;
  if (!data?.groups?.length) {
    notify(`扫描 ${data?.stats?.scanned ?? 0} 个音频，未发现重复`, 'success');
  } else {
    notify(`发现 ${data.groups.length} 组重复，可省 ${formatSize(data?.stats?.wasted_bytes)}`, 'info');
  }
}

async function pollDedupe() {
  if (!props.api?.post) return
  try {
    const snapshot = unwrap(await props.api.post(`${base.value}/duplicates/result`, { body: {} }));
    if (snapshot?.running) return
    stopDedupePolling();
    await refresh();
    const result = snapshot?.result;
    if (result?.stats) {
      applyDedupe(result);
    } else {
      notify(snapshot?.run?.message || '查重结束但没有结果', 'warning');
    }
  } catch (err) {
    stopDedupePolling();
    notify(`读取查重结果失败：${errorText(err)}`, 'error');
  }
}

function stopDedupePolling() {
  if (dedupeTimer) {
    clearInterval(dedupeTimer);
    dedupeTimer = null;
  }
}

function toggleDedupeAll() {
  const all = (dedupe.value?.groups || []).flatMap(group => group.duplicates || []);
  dedupeSelected.value = dedupeSelected.value.length === all.length ? [] : all;
}

async function doQuarantine() {
  if (!props.api?.post) return
  if (!dedupeSelected.value.length) {
    notify('请先勾选需要隔离的重复文件', 'warning');
    return
  }
  busy.value = 'quarantine';
  try {
    const data = unwrap(await props.api.post(`${base.value}/duplicates/quarantine`, {
      body: { paths: dedupeSelected.value },
    }));
    const failed = data?.failed?.length || 0;
    notify(
      `已隔离 ${data?.moved ?? 0} 个文件（${formatSize(data?.moved_bytes)}）${failed ? `，失败 ${failed} 个` : ''}`,
      failed ? 'warning' : 'success',
    );
    dedupeDialog.value = false;
    await refresh();
  } catch (err) {
    notify(`隔离失败：${errorText(err)}`, 'error');
  } finally {
    busy.value = '';
  }
}

async function doRestore() {
  if (!props.api?.post) return
  busy.value = 'restore';
  try {
    const data = unwrap(await props.api.post(`${base.value}/duplicates/restore`, { body: {} }));
    notify(`已还原 ${data?.restored ?? 0} 个文件`, 'success');
    await refresh();
  } catch (err) {
    notify(`还原失败：${errorText(err)}`, 'error');
  } finally {
    busy.value = '';
  }
}

const dedupeStats = computed(() => status.value?.dedupe?.stats || status.value?.dedupe || {});
const quarantinedCount = computed(() => status.value?.quarantined_count ?? 0);

async function doStop() {
  if (!props.api?.post) return
  busy.value = 'stop';
  try {
    await props.api.post(`${base.value}/stop`);
    notify('已请求停止', 'warning');
    await refresh();
  } catch (err) {
    notify(`停止失败：${errorText(err)}`, 'error');
  } finally {
    busy.value = '';
  }
}

async function doRetry() {
  if (!props.api?.post) return
  busy.value = 'retry';
  try {
    const data = unwrap(await props.api.post(`${base.value}/retry`));
    notify(data?.started ? '已开始重试失败条目' : data?.message || '没有可重试的条目', 'info');
    await refresh();
    if (data?.started) startPolling();
  } catch (err) {
    notify(`重试失败：${errorText(err)}`, 'error');
  } finally {
    busy.value = '';
  }
}

async function doClear() {
  if (!props.api?.post) return
  busy.value = 'clear';
  try {
    const data = unwrap(await props.api.post(`${base.value}/clear`));
    notify(`已清空 ${data?.cleared ?? 0} 条记录`, 'success');
    await refresh();
  } catch (err) {
    notify(`清空失败：${errorText(err)}`, 'error');
  } finally {
    busy.value = '';
  }
}

function startPolling() {
  stopPolling();
  timer = setInterval(async () => {
    await refresh();
    if (!status.value?.running) stopPolling();
  }, 3000);
}

function stopPolling() {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
}

const running = computed(() => Boolean(status.value?.running));
const run = computed(() => status.value?.run || {});
const lastRun = computed(() => status.value?.last_run || {});
const failures = computed(() => status.value?.failures || []);
const logs = computed(() => status.value?.logs || []);
const progress = computed(() => {
  const total = Number(run.value?.total || 0);
  const finished = Number(run.value?.finished || 0);
  if (!total) return 0
  return Math.min(100, Math.round((finished / total) * 100))
});
const cards = computed(() => [
  { title: '已处理音频', value: status.value?.processed_total ?? 0, icon: 'mdi-music-note', color: 'primary' },
  { title: '今日更新', value: status.value?.today?.updated ?? 0, icon: 'mdi-check-circle-outline', color: 'success' },
  { title: '失败条目', value: status.value?.failure_count ?? 0, icon: 'mdi-alert-circle-outline', color: 'error' },
  { title: '目录封面', value: status.value?.cover_dir_count ?? 0, icon: 'mdi-image-multiple-outline', color: 'info' },
]);

const sourceLabels = { douban: '豆瓣音乐', musicbrainz: 'MusicBrainz', theaudiodb: 'TheAudioDB' };

function missingLabel(items) {
  const mapping = {
    title: '标题', artist: '艺人', album: '专辑', year: '年份', track: '曲序', lyrics: '歌词',
    folder_cover: '目录封面',
  };
  return (items || []).map(item => mapping[item] || item).join('、')
}

onMounted(async () => {
  await refresh();
  if (status.value?.running) startPolling();
});

onBeforeUnmount(() => {
  stopPolling();
  stopDedupePolling();
});

return (_ctx, _cache) => {
  const _component_VIcon = _resolveComponent("VIcon");
  const _component_VCol = _resolveComponent("VCol");
  const _component_VSpacer = _resolveComponent("VSpacer");
  const _component_VBtn = _resolveComponent("VBtn");
  const _component_VRow = _resolveComponent("VRow");
  const _component_VCardText = _resolveComponent("VCardText");
  const _component_VCard = _resolveComponent("VCard");
  const _component_VChip = _resolveComponent("VChip");
  const _component_VProgressLinear = _resolveComponent("VProgressLinear");
  const _component_VCardTitle = _resolveComponent("VCardTitle");
  const _component_VAlert = _resolveComponent("VAlert");
  const _component_VTable = _resolveComponent("VTable");
  const _component_VCheckboxBtn = _resolveComponent("VCheckboxBtn");
  const _component_VCardActions = _resolveComponent("VCardActions");
  const _component_VDialog = _resolveComponent("VDialog");
  const _component_VSnackbar = _resolveComponent("VSnackbar");
  const _component_VContainer = _resolveComponent("VContainer");

  return (_openBlock(), _createBlock(_component_VContainer, {
    class: _normalizeClass(props.compact ? 'pa-2' : 'pa-4')
  }, {
    default: _withCtx(() => [
      _createVNode(_component_VRow, {
        class: "mb-2",
        align: "center"
      }, {
        default: _withCtx(() => [
          _createVNode(_component_VCol, {
            cols: "12",
            md: "auto"
          }, {
            default: _withCtx(() => [
              _createElementVNode("div", _hoisted_1, [
                _createVNode(_component_VIcon, {
                  icon: "mdi-music-note-plus",
                  size: "28",
                  color: "primary"
                }),
                _cache[10] || (_cache[10] = _createElementVNode("div", null, [
                  _createElementVNode("div", { class: "text-h6" }, "音乐标签刮削"),
                  _createElementVNode("div", { class: "text-caption text-medium-emphasis" }, " 多源补全标签 / 歌词 / 封面，只补空缺，不移动文件 ")
                ], -1))
              ])
            ]),
            _: 1
          }),
          _createVNode(_component_VSpacer),
          _createVNode(_component_VCol, {
            cols: "12",
            md: "auto",
            class: "d-flex ga-2 flex-wrap justify-end"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_VBtn, {
                variant: "tonal",
                "prepend-icon": "mdi-magnify-scan",
                loading: busy.value === 'preview',
                onClick: doPreview
              }, {
                default: _withCtx(() => [...(_cache[11] || (_cache[11] = [
                  _createTextVNode(" 试跑预览 ", -1)
                ]))]),
                _: 1
              }, 8, ["loading"]),
              _createVNode(_component_VBtn, {
                color: "primary",
                "prepend-icon": "mdi-play",
                loading: busy.value === 'run',
                disabled: running.value,
                onClick: doRun
              }, {
                default: _withCtx(() => [...(_cache[12] || (_cache[12] = [
                  _createTextVNode(" 开始补全 ", -1)
                ]))]),
                _: 1
              }, 8, ["loading", "disabled"]),
              _createVNode(_component_VBtn, {
                variant: "outlined",
                color: "warning",
                "prepend-icon": "mdi-stop",
                disabled: !running.value,
                loading: busy.value === 'stop',
                onClick: doStop
              }, {
                default: _withCtx(() => [...(_cache[13] || (_cache[13] = [
                  _createTextVNode(" 停止 ", -1)
                ]))]),
                _: 1
              }, 8, ["disabled", "loading"])
            ]),
            _: 1
          })
        ]),
        _: 1
      }),
      _createVNode(_component_VRow, null, {
        default: _withCtx(() => [
          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(cards.value, (card) => {
            return (_openBlock(), _createBlock(_component_VCol, {
              key: card.title,
              cols: "6",
              md: "3"
            }, {
              default: _withCtx(() => [
                _createVNode(_component_VCard, {
                  variant: "tonal",
                  color: card.color
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_VCardText, { class: "d-flex align-center ga-3" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_VIcon, {
                          icon: card.icon,
                          size: "30"
                        }, null, 8, ["icon"]),
                        _createElementVNode("div", null, [
                          _createElementVNode("div", _hoisted_2, _toDisplayString(card.title), 1),
                          _createElementVNode("div", _hoisted_3, _toDisplayString(card.value), 1)
                        ])
                      ]),
                      _: 2
                    }, 1024)
                  ]),
                  _: 2
                }, 1032, ["color"])
              ]),
              _: 2
            }, 1024))
          }), 128))
        ]),
        _: 1
      }),
      (running.value)
        ? (_openBlock(), _createBlock(_component_VCard, {
            key: 0,
            variant: "outlined",
            class: "mt-4"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_VCardText, null, {
                default: _withCtx(() => [
                  _createElementVNode("div", _hoisted_4, [
                    _createElementVNode("span", _hoisted_5, _toDisplayString(run.value.message || '正在处理…'), 1),
                    _createVNode(_component_VChip, {
                      size: "small",
                      color: "primary",
                      variant: "tonal"
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString(progress.value) + "%", 1)
                      ]),
                      _: 1
                    })
                  ]),
                  _createVNode(_component_VProgressLinear, {
                    "model-value": progress.value,
                    color: "primary",
                    height: "10",
                    rounded: ""
                  }, null, 8, ["model-value"])
                ]),
                _: 1
              })
            ]),
            _: 1
          }))
        : (lastRun.value && lastRun.value.state)
          ? (_openBlock(), _createBlock(_component_VCard, {
              key: 1,
              variant: "outlined",
              class: "mt-4"
            }, {
              default: _withCtx(() => [
                _createVNode(_component_VCardText, { class: "d-flex flex-wrap ga-3 align-center" }, {
                  default: _withCtx(() => [
                    _createVNode(_component_VChip, {
                      size: "small",
                      color: lastRun.value.state === 'finished' ? 'success' : 'warning',
                      variant: "tonal"
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString(lastRun.value.state === 'finished' ? '上次完成' : lastRun.value.state === 'cancelled' ? '上次已停止' : '上次失败'), 1)
                      ]),
                      _: 1
                    }, 8, ["color"]),
                    _createElementVNode("span", _hoisted_6, "共 " + _toDisplayString(lastRun.value.total || 0) + " 条", 1),
                    _createElementVNode("span", _hoisted_7, "更新 " + _toDisplayString(lastRun.value.updated || 0), 1),
                    _createElementVNode("span", _hoisted_8, "目录封面 " + _toDisplayString(lastRun.value.folder_cover || 0), 1),
                    _createElementVNode("span", _hoisted_9, "跳过 " + _toDisplayString(lastRun.value.skipped || 0), 1),
                    _createElementVNode("span", _hoisted_10, "失败 " + _toDisplayString(lastRun.value.failed || 0), 1),
                    _createVNode(_component_VSpacer),
                    _createElementVNode("span", _hoisted_11, _toDisplayString(lastRun.value.finished_at), 1)
                  ]),
                  _: 1
                })
              ]),
              _: 1
            }))
          : _createCommentVNode("", true),
      _createVNode(_component_VRow, { class: "mt-4" }, {
        default: _withCtx(() => [
          _createVNode(_component_VCol, {
            cols: "12",
            md: "6"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_VCard, { variant: "tonal" }, {
                default: _withCtx(() => [
                  _createVNode(_component_VCardTitle, { class: "d-flex align-center" }, {
                    default: _withCtx(() => [
                      _createVNode(_component_VIcon, {
                        icon: "mdi-tools",
                        class: "me-2"
                      }),
                      _cache[16] || (_cache[16] = _createTextVNode("失败与重试 ", -1)),
                      _createVNode(_component_VSpacer),
                      _createVNode(_component_VBtn, {
                        size: "small",
                        variant: "text",
                        loading: busy.value === 'retry',
                        onClick: doRetry
                      }, {
                        default: _withCtx(() => [...(_cache[14] || (_cache[14] = [
                          _createTextVNode("重试失败", -1)
                        ]))]),
                        _: 1
                      }, 8, ["loading"]),
                      _createVNode(_component_VBtn, {
                        size: "small",
                        variant: "text",
                        color: "warning",
                        loading: busy.value === 'clear',
                        onClick: doClear
                      }, {
                        default: _withCtx(() => [...(_cache[15] || (_cache[15] = [
                          _createTextVNode("清空记录", -1)
                        ]))]),
                        _: 1
                      }, 8, ["loading"])
                    ]),
                    _: 1
                  }),
                  _createVNode(_component_VCardText, null, {
                    default: _withCtx(() => [
                      (!failures.value.length)
                        ? (_openBlock(), _createBlock(_component_VAlert, {
                            key: 0,
                            type: "success",
                            variant: "tonal",
                            density: "compact"
                          }, {
                            default: _withCtx(() => [...(_cache[17] || (_cache[17] = [
                              _createTextVNode(" 暂无失败条目 ", -1)
                            ]))]),
                            _: 1
                          }))
                        : (_openBlock(), _createBlock(_component_VTable, {
                            key: 1,
                            density: "compact"
                          }, {
                            default: _withCtx(() => [
                              _cache[19] || (_cache[19] = _createElementVNode("thead", null, [
                                _createElementVNode("tr", null, [
                                  _createElementVNode("th", null, "文件"),
                                  _createElementVNode("th", null, "原因"),
                                  _createElementVNode("th", null, "次数"),
                                  _createElementVNode("th")
                                ])
                              ], -1)),
                              _createElementVNode("tbody", null, [
                                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(failures.value.slice(0, 8), (item) => {
                                  return (_openBlock(), _createElementBlock("tr", {
                                    key: item.key
                                  }, [
                                    _createElementVNode("td", _hoisted_12, _toDisplayString(item.name), 1),
                                    _createElementVNode("td", _hoisted_13, _toDisplayString(item.message), 1),
                                    _createElementVNode("td", _hoisted_14, _toDisplayString(item.count), 1),
                                    _createElementVNode("td", null, [
                                      _createVNode(_component_VBtn, {
                                        size: "x-small",
                                        variant: "text",
                                        loading: busy.value === `retry:${item.key}`,
                                        onClick: $event => (retryOne(item))
                                      }, {
                                        default: _withCtx(() => [...(_cache[18] || (_cache[18] = [
                                          _createTextVNode(" 重试 ", -1)
                                        ]))]),
                                        _: 1
                                      }, 8, ["loading", "onClick"])
                                    ])
                                  ]))
                                }), 128))
                              ])
                            ]),
                            _: 1
                          }))
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              })
            ]),
            _: 1
          }),
          _createVNode(_component_VCol, {
            cols: "12",
            md: "6"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_VCard, { variant: "tonal" }, {
                default: _withCtx(() => [
                  _createVNode(_component_VCardTitle, { class: "d-flex align-center" }, {
                    default: _withCtx(() => [
                      _createVNode(_component_VIcon, {
                        icon: "mdi-text-box-outline",
                        class: "me-2"
                      }),
                      _cache[20] || (_cache[20] = _createTextVNode("运行日志 ", -1))
                    ]),
                    _: 1
                  }),
                  _createVNode(_component_VCardText, { style: {"max-height":"260px","overflow-y":"auto"} }, {
                    default: _withCtx(() => [
                      (!logs.value.length)
                        ? (_openBlock(), _createElementBlock("div", _hoisted_15, "暂无日志"))
                        : _createCommentVNode("", true),
                      (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(logs.value.slice().reverse(), (log, index) => {
                        return (_openBlock(), _createElementBlock("div", {
                          key: index,
                          class: "text-caption mb-1"
                        }, [
                          _createElementVNode("span", _hoisted_16, _toDisplayString(log.time), 1),
                          _createElementVNode("span", {
                            class: _normalizeClass(log.level === 'error' ? 'text-error' : '')
                          }, _toDisplayString(log.message), 3)
                        ]))
                      }), 128))
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              })
            ]),
            _: 1
          })
        ]),
        _: 1
      }),
      _createVNode(_component_VRow, { class: "mt-4" }, {
        default: _withCtx(() => [
          _createVNode(_component_VCol, { cols: "12" }, {
            default: _withCtx(() => [
              _createVNode(_component_VCard, { variant: "tonal" }, {
                default: _withCtx(() => [
                  _createVNode(_component_VCardTitle, { class: "d-flex align-center flex-wrap ga-2" }, {
                    default: _withCtx(() => [
                      _createVNode(_component_VIcon, {
                        icon: "mdi-content-duplicate",
                        class: "me-2"
                      }),
                      _cache[24] || (_cache[24] = _createTextVNode("重复检测 ", -1)),
                      (quarantinedCount.value)
                        ? (_openBlock(), _createBlock(_component_VChip, {
                            key: 0,
                            size: "small",
                            color: "warning",
                            variant: "tonal"
                          }, {
                            default: _withCtx(() => [
                              _createTextVNode(" 已隔离 " + _toDisplayString(quarantinedCount.value), 1)
                            ]),
                            _: 1
                          }))
                        : _createCommentVNode("", true),
                      (status.value?.dedupe_running)
                        ? (_openBlock(), _createBlock(_component_VChip, {
                            key: 1,
                            size: "small",
                            color: "info",
                            variant: "tonal"
                          }, {
                            default: _withCtx(() => [...(_cache[21] || (_cache[21] = [
                              _createTextVNode(" 查重中… ", -1)
                            ]))]),
                            _: 1
                          }))
                        : _createCommentVNode("", true),
                      _createVNode(_component_VSpacer),
                      _createVNode(_component_VBtn, {
                        size: "small",
                        variant: "text",
                        loading: busy.value === 'restore',
                        disabled: !quarantinedCount.value,
                        onClick: doRestore
                      }, {
                        default: _withCtx(() => [...(_cache[22] || (_cache[22] = [
                          _createTextVNode(" 还原隔离 ", -1)
                        ]))]),
                        _: 1
                      }, 8, ["loading", "disabled"]),
                      _createVNode(_component_VBtn, {
                        size: "small",
                        variant: "tonal",
                        color: "primary",
                        loading: busy.value === 'dedupe' || status.value?.dedupe_running,
                        onClick: doDetect
                      }, {
                        default: _withCtx(() => [...(_cache[23] || (_cache[23] = [
                          _createTextVNode(" 扫描重复 ", -1)
                        ]))]),
                        _: 1
                      }, 8, ["loading"])
                    ]),
                    _: 1
                  }),
                  _createVNode(_component_VCardText, null, {
                    default: _withCtx(() => [
                      _cache[25] || (_cache[25] = _createElementVNode("div", { class: "text-caption text-medium-emphasis" }, " 按文件内容识别完全重复，按「曲名 + 艺人 + 时长」识别同曲多版本；只盘点、不自动删除， 勾选后可移入隔离目录（保留相对路径，随时一键还原）。 ", -1)),
                      (dedupeStats.value.groups)
                        ? (_openBlock(), _createElementBlock("div", _hoisted_17, [
                            _createVNode(_component_VChip, {
                              size: "small",
                              variant: "tonal"
                            }, {
                              default: _withCtx(() => [
                                _createTextVNode("重复组 " + _toDisplayString(dedupeStats.value.groups), 1)
                              ]),
                              _: 1
                            }),
                            _createVNode(_component_VChip, {
                              size: "small",
                              variant: "tonal",
                              color: "primary"
                            }, {
                              default: _withCtx(() => [
                                _createTextVNode("可清理 " + _toDisplayString(dedupeStats.value.duplicate_files) + " 个", 1)
                              ]),
                              _: 1
                            }),
                            _createVNode(_component_VChip, {
                              size: "small",
                              variant: "tonal",
                              color: "warning"
                            }, {
                              default: _withCtx(() => [
                                _createTextVNode("可省 " + _toDisplayString(formatSize(dedupeStats.value.wasted_bytes)), 1)
                              ]),
                              _: 1
                            }),
                            _createElementVNode("span", _hoisted_18, _toDisplayString(status.value?.dedupe?.time), 1)
                          ]))
                        : _createCommentVNode("", true)
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              })
            ]),
            _: 1
          })
        ]),
        _: 1
      }),
      _createVNode(_component_VDialog, {
        modelValue: dedupeDialog.value,
        "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((dedupeDialog).value = $event)),
        "max-width": "1000"
      }, {
        default: _withCtx(() => [
          _createVNode(_component_VCard, null, {
            default: _withCtx(() => [
              _createVNode(_component_VCardTitle, { class: "d-flex align-center flex-wrap ga-2" }, {
                default: _withCtx(() => [
                  _createVNode(_component_VIcon, {
                    icon: "mdi-content-duplicate",
                    class: "me-2"
                  }),
                  _cache[27] || (_cache[27] = _createTextVNode("重复扫描结果 ", -1)),
                  _createVNode(_component_VSpacer),
                  _createVNode(_component_VBtn, {
                    size: "small",
                    variant: "text",
                    onClick: toggleDedupeAll
                  }, {
                    default: _withCtx(() => [...(_cache[26] || (_cache[26] = [
                      _createTextVNode("全选 / 取消", -1)
                    ]))]),
                    _: 1
                  }),
                  _createVNode(_component_VBtn, {
                    icon: "mdi-close",
                    variant: "text",
                    onClick: _cache[0] || (_cache[0] = $event => (dedupeDialog.value = false))
                  })
                ]),
                _: 1
              }),
              _createVNode(_component_VCardText, { style: {"max-height":"60vh","overflow-y":"auto"} }, {
                default: _withCtx(() => [
                  (dedupe.value?.stats)
                    ? (_openBlock(), _createElementBlock("div", _hoisted_19, [
                        _createVNode(_component_VChip, {
                          size: "small",
                          variant: "tonal"
                        }, {
                          default: _withCtx(() => [
                            _createTextVNode("扫描 " + _toDisplayString(dedupe.value.stats.scanned), 1)
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VChip, {
                          size: "small",
                          variant: "tonal"
                        }, {
                          default: _withCtx(() => [
                            _createTextVNode("完全重复 " + _toDisplayString(dedupe.value.stats.exact_groups) + " 组", 1)
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VChip, {
                          size: "small",
                          variant: "tonal"
                        }, {
                          default: _withCtx(() => [
                            _createTextVNode("同曲多版本 " + _toDisplayString(dedupe.value.stats.track_groups) + " 组", 1)
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VChip, {
                          size: "small",
                          variant: "tonal",
                          color: "warning"
                        }, {
                          default: _withCtx(() => [
                            _createTextVNode("可省 " + _toDisplayString(formatSize(dedupe.value.stats.wasted_bytes)), 1)
                          ]),
                          _: 1
                        })
                      ]))
                    : _createCommentVNode("", true),
                  (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(dedupe.value?.groups || [], (group) => {
                    return (_openBlock(), _createElementBlock("div", {
                      key: group.id,
                      class: "mb-4"
                    }, [
                      _createElementVNode("div", _hoisted_20, [
                        _createVNode(_component_VChip, {
                          size: "small",
                          color: group.kind === 'exact' ? 'error' : 'warning',
                          variant: "tonal"
                        }, {
                          default: _withCtx(() => [
                            _createTextVNode(_toDisplayString(group.kind === 'exact' ? '完全重复' : '同曲多版本'), 1)
                          ]),
                          _: 2
                        }, 1032, ["color"]),
                        _createElementVNode("span", _hoisted_21, [
                          _createTextVNode(_toDisplayString(group.title) + " ", 1),
                          (group.album)
                            ? (_openBlock(), _createElementBlock("span", _hoisted_22, " · " + _toDisplayString(group.album), 1))
                            : _createCommentVNode("", true)
                        ]),
                        _createElementVNode("span", _hoisted_23, "可省 " + _toDisplayString(formatSize(group.wasted)), 1)
                      ]),
                      _createVNode(_component_VTable, { density: "compact" }, {
                        default: _withCtx(() => [
                          _cache[30] || (_cache[30] = _createElementVNode("thead", null, [
                            _createElementVNode("tr", null, [
                              _createElementVNode("th", { style: {"width":"44px"} }),
                              _createElementVNode("th", null, "文件"),
                              _createElementVNode("th", null, "格式"),
                              _createElementVNode("th", null, "码率"),
                              _createElementVNode("th", null, "大小"),
                              _createElementVNode("th", null, "状态")
                            ])
                          ], -1)),
                          _createElementVNode("tbody", null, [
                            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(group.files, (file) => {
                              return (_openBlock(), _createElementBlock("tr", {
                                key: file.path
                              }, [
                                _createElementVNode("td", null, [
                                  _createVNode(_component_VCheckboxBtn, {
                                    modelValue: dedupeSelected.value,
                                    "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((dedupeSelected).value = $event)),
                                    value: file.path,
                                    disabled: file.path === group.keep,
                                    density: "compact",
                                    "hide-details": "",
                                    color: "error"
                                  }, null, 8, ["modelValue", "value", "disabled"])
                                ]),
                                _createElementVNode("td", _hoisted_24, _toDisplayString(file.path), 1),
                                _createElementVNode("td", _hoisted_25, _toDisplayString((file.ext || '').replace('.', '').toUpperCase()) + _toDisplayString(file.lossless ? ' · 无损' : ''), 1),
                                _createElementVNode("td", _hoisted_26, _toDisplayString(file.bitrate ? `${file.bitrate} kbps` : '—'), 1),
                                _createElementVNode("td", _hoisted_27, _toDisplayString(formatSize(file.size)), 1),
                                _createElementVNode("td", null, [
                                  (file.path === group.keep)
                                    ? (_openBlock(), _createBlock(_component_VChip, {
                                        key: 0,
                                        size: "x-small",
                                        color: "success",
                                        variant: "tonal"
                                      }, {
                                        default: _withCtx(() => [...(_cache[28] || (_cache[28] = [
                                          _createTextVNode(" 保留 ", -1)
                                        ]))]),
                                        _: 1
                                      }))
                                    : (_openBlock(), _createBlock(_component_VChip, {
                                        key: 1,
                                        size: "x-small",
                                        color: "error",
                                        variant: "tonal"
                                      }, {
                                        default: _withCtx(() => [...(_cache[29] || (_cache[29] = [
                                          _createTextVNode("重复", -1)
                                        ]))]),
                                        _: 1
                                      }))
                                ])
                              ]))
                            }), 128))
                          ])
                        ]),
                        _: 2
                      }, 1024)
                    ]))
                  }), 128)),
                  (!dedupe.value?.groups?.length)
                    ? (_openBlock(), _createBlock(_component_VAlert, {
                        key: 1,
                        type: "success",
                        variant: "tonal",
                        density: "compact"
                      }, {
                        default: _withCtx(() => [...(_cache[31] || (_cache[31] = [
                          _createTextVNode(" 未发现重复文件 ", -1)
                        ]))]),
                        _: 1
                      }))
                    : _createCommentVNode("", true),
                  _createElementVNode("div", _hoisted_28, " 隔离只会移动文件到隔离目录，不会删除；位置：" + _toDisplayString(dedupe.value?.stats?.quarantine_dir || '默认音乐目录同级'), 1)
                ]),
                _: 1
              }),
              _createVNode(_component_VCardActions, null, {
                default: _withCtx(() => [
                  _createElementVNode("span", _hoisted_29, "已选 " + _toDisplayString(dedupeSelected.value.length) + " 个", 1),
                  _createVNode(_component_VSpacer),
                  _createVNode(_component_VBtn, {
                    variant: "text",
                    onClick: _cache[2] || (_cache[2] = $event => (dedupeDialog.value = false))
                  }, {
                    default: _withCtx(() => [...(_cache[32] || (_cache[32] = [
                      _createTextVNode("关闭", -1)
                    ]))]),
                    _: 1
                  }),
                  _createVNode(_component_VBtn, {
                    color: "error",
                    variant: "tonal",
                    disabled: !dedupeSelected.value.length,
                    loading: busy.value === 'quarantine',
                    onClick: doQuarantine
                  }, {
                    default: _withCtx(() => [
                      _createTextVNode(" 隔离选中（" + _toDisplayString(dedupeSelected.value.length) + "） ", 1)
                    ]),
                    _: 1
                  }, 8, ["disabled", "loading"])
                ]),
                _: 1
              })
            ]),
            _: 1
          })
        ]),
        _: 1
      }, 8, ["modelValue"]),
      _createVNode(_component_VDialog, {
        modelValue: previewDialog.value,
        "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => ((previewDialog).value = $event)),
        "max-width": "900"
      }, {
        default: _withCtx(() => [
          _createVNode(_component_VCard, null, {
            default: _withCtx(() => [
              _createVNode(_component_VCardTitle, { class: "d-flex align-center" }, {
                default: _withCtx(() => [
                  _createVNode(_component_VIcon, {
                    icon: "mdi-magnify-scan",
                    class: "me-2"
                  }),
                  _cache[33] || (_cache[33] = _createTextVNode("试跑结果 ", -1)),
                  _createVNode(_component_VSpacer),
                  _createVNode(_component_VBtn, {
                    icon: "mdi-close",
                    variant: "text",
                    onClick: _cache[4] || (_cache[4] = $event => (previewDialog.value = false))
                  })
                ]),
                _: 1
              }),
              _createVNode(_component_VCardText, null, {
                default: _withCtx(() => [
                  (preview.value?.stats)
                    ? (_openBlock(), _createElementBlock("div", _hoisted_30, [
                        _createVNode(_component_VChip, {
                          size: "small",
                          variant: "tonal"
                        }, {
                          default: _withCtx(() => [
                            _createTextVNode("扫描 " + _toDisplayString(preview.value.stats.scanned), 1)
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VChip, {
                          size: "small",
                          variant: "tonal",
                          color: "primary"
                        }, {
                          default: _withCtx(() => [
                            _createTextVNode("待处理 " + _toDisplayString(preview.value.stats.candidates), 1)
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VChip, {
                          size: "small",
                          variant: "tonal"
                        }, {
                          default: _withCtx(() => [
                            _createTextVNode("跳过 " + _toDisplayString(preview.value.stats.skipped), 1)
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VChip, {
                          size: "small",
                          variant: "tonal",
                          color: "warning"
                        }, {
                          default: _withCtx(() => [
                            _createTextVNode(" 缺目录封面 " + _toDisplayString(preview.value.stats.missing_folder_cover ?? 0), 1)
                          ]),
                          _: 1
                        })
                      ]))
                    : _createCommentVNode("", true),
                  (preview.value?.items?.length)
                    ? (_openBlock(), _createBlock(_component_VTable, {
                        key: 1,
                        density: "compact"
                      }, {
                        default: _withCtx(() => [
                          _createElementVNode("thead", null, [
                            _createElementVNode("tr", null, [
                              _createElementVNode("th", _hoisted_31, [
                                _createVNode(_component_VCheckboxBtn, {
                                  "model-value": allSelected.value,
                                  density: "compact",
                                  "hide-details": "",
                                  color: "primary",
                                  "onUpdate:modelValue": toggleAll
                                }, null, 8, ["model-value"])
                              ]),
                              _cache[34] || (_cache[34] = _createElementVNode("th", null, "文件", -1)),
                              _cache[35] || (_cache[35] = _createElementVNode("th", null, "缺失", -1)),
                              _cache[36] || (_cache[36] = _createElementVNode("th", null, "目录封面", -1)),
                              _cache[37] || (_cache[37] = _createElementVNode("th", null, "匹配专辑", -1)),
                              _cache[38] || (_cache[38] = _createElementVNode("th", null, "来源", -1))
                            ])
                          ]),
                          _createElementVNode("tbody", null, [
                            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(preview.value.items, (item) => {
                              return (_openBlock(), _createElementBlock("tr", {
                                key: item.key
                              }, [
                                _createElementVNode("td", null, [
                                  _createVNode(_component_VCheckboxBtn, {
                                    modelValue: selected.value,
                                    "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((selected).value = $event)),
                                    value: item.key,
                                    density: "compact",
                                    "hide-details": "",
                                    color: "primary"
                                  }, null, 8, ["modelValue", "value"])
                                ]),
                                _createElementVNode("td", _hoisted_32, _toDisplayString(item.name), 1),
                                _createElementVNode("td", _hoisted_33, _toDisplayString(missingLabel(item.missing)), 1),
                                _createElementVNode("td", _hoisted_34, [
                                  (item.folder_cover_ok)
                                    ? (_openBlock(), _createBlock(_component_VChip, {
                                        key: 0,
                                        size: "x-small",
                                        color: "success",
                                        variant: "tonal"
                                      }, {
                                        default: _withCtx(() => [...(_cache[39] || (_cache[39] = [
                                          _createTextVNode("已有", -1)
                                        ]))]),
                                        _: 1
                                      }))
                                    : (_openBlock(), _createBlock(_component_VChip, {
                                        key: 1,
                                        size: "x-small",
                                        color: "warning",
                                        variant: "tonal"
                                      }, {
                                        default: _withCtx(() => [...(_cache[40] || (_cache[40] = [
                                          _createTextVNode("待补", -1)
                                        ]))]),
                                        _: 1
                                      }))
                                ]),
                                _createElementVNode("td", _hoisted_35, [
                                  _createTextVNode(_toDisplayString(item.album || '—') + " ", 1),
                                  (item.album_artist)
                                    ? (_openBlock(), _createElementBlock("span", _hoisted_36, " / " + _toDisplayString(item.album_artist), 1))
                                    : _createCommentVNode("", true),
                                  (item.year)
                                    ? (_openBlock(), _createElementBlock("span", _hoisted_37, " (" + _toDisplayString(item.year) + ")", 1))
                                    : _createCommentVNode("", true)
                                ]),
                                _createElementVNode("td", _hoisted_38, [
                                  (item.source)
                                    ? (_openBlock(), _createBlock(_component_VChip, {
                                        key: 0,
                                        size: "x-small",
                                        variant: "tonal"
                                      }, {
                                        default: _withCtx(() => [
                                          _createTextVNode(_toDisplayString(sourceLabels[item.source] || item.source), 1)
                                        ]),
                                        _: 2
                                      }, 1024))
                                    : (_openBlock(), _createElementBlock("span", _hoisted_39, "未命中"))
                                ])
                              ]))
                            }), 128))
                          ])
                        ]),
                        _: 1
                      }))
                    : (_openBlock(), _createBlock(_component_VAlert, {
                        key: 2,
                        type: "info",
                        variant: "tonal",
                        density: "compact"
                      }, {
                        default: _withCtx(() => [...(_cache[41] || (_cache[41] = [
                          _createTextVNode(" 没有待处理音频（已补全或未达到上限） ", -1)
                        ]))]),
                        _: 1
                      })),
                  _cache[42] || (_cache[42] = _createElementVNode("div", { class: "text-caption text-medium-emphasis mt-3" }, " 试跑只做扫描与匹配，不会写入任何标签或歌词。 ", -1))
                ]),
                _: 1
              }),
              _createVNode(_component_VCardActions, null, {
                default: _withCtx(() => [
                  _createElementVNode("span", _hoisted_40, "已选 " + _toDisplayString(selected.value.length) + " / " + _toDisplayString(preview.value?.items?.length || 0), 1),
                  _createVNode(_component_VSpacer),
                  _createVNode(_component_VBtn, {
                    variant: "text",
                    onClick: _cache[6] || (_cache[6] = $event => (previewDialog.value = false))
                  }, {
                    default: _withCtx(() => [...(_cache[43] || (_cache[43] = [
                      _createTextVNode("关闭", -1)
                    ]))]),
                    _: 1
                  }),
                  _createVNode(_component_VBtn, {
                    variant: "tonal",
                    disabled: !preview.value?.items?.length,
                    onClick: doRunSelected
                  }, {
                    default: _withCtx(() => [
                      _createTextVNode(" 仅处理选中（" + _toDisplayString(selected.value.length) + "） ", 1)
                    ]),
                    _: 1
                  }, 8, ["disabled"]),
                  _createVNode(_component_VBtn, {
                    color: "primary",
                    variant: "tonal",
                    onClick: _cache[7] || (_cache[7] = $event => {previewDialog.value = false; doRun();})
                  }, {
                    default: _withCtx(() => [...(_cache[44] || (_cache[44] = [
                      _createTextVNode("全部处理", -1)
                    ]))]),
                    _: 1
                  })
                ]),
                _: 1
              })
            ]),
            _: 1
          })
        ]),
        _: 1
      }, 8, ["modelValue"]),
      _createVNode(_component_VSnackbar, {
        modelValue: showMessage.value,
        "onUpdate:modelValue": _cache[9] || (_cache[9] = $event => ((showMessage).value = $event)),
        color: messageType.value,
        timeout: 4000,
        location: "bottom"
      }, {
        default: _withCtx(() => [
          _createTextVNode(_toDisplayString(message.value), 1)
        ]),
        _: 1
      }, 8, ["modelValue", "color"])
    ]),
    _: 1
  }, 8, ["class"]))
}
}

};
const Panel = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-125e93f0"]]);

export { Panel as P, _export_sfc as _ };
