# MoviePilot-Plugins

本仓库是 [MoviePilot](https://github.com/jxxghp/MoviePilot) 的插件仓库（**V3**），收录自用的 MoviePilot 插件。

## 插件列表

| 插件 | 说明 | 版本 |
| --- | --- | --- |
| **站点保种统计（SeedStats）** | 按 tracker 汇总各站点在本机下载器中的做种 / 辅种数量，并合并站点账户信息（上传 / 下载 / 分享率 / 等级 / 魔力 / 时魔估算）；提供插件详情页与首页仪表板 | 1.3.1 |

## 安装方法

1. 打开 MoviePilot「**设置 → 插件市场地址**」（`PLUGIN_MARKET`），把本仓库地址加进去（多个地址用英文逗号分隔）：

   ```
   https://github.com/miguelito39721/MoviePilot-Plugins
   ```

2. 到「**插件**」页面刷新一下市场，搜索插件名（例如「站点保种统计」），点击安装即可。
3. 本仓库更新版本后，已安装的插件会在列表里出现「更新」提示，可直接升级。

## 目录结构

```
package.v3.json               插件市场索引（V3）
plugins.v3/<plugin_id>/       V3 插件源码目录
```

## 说明

- 本仓库的插件面向 **MoviePilot V3（≥ 3.0.0）**。
- 每个插件的详细说明、配置项与注意事项见 `plugins.v3/<插件目录>/README.md`。
- 插件均为只读/非破坏性设计，安装前建议先阅读对应说明。
