# MoviePilot-Plugins

个人 MoviePilot 插件仓库。

## 插件列表

| 插件 | 目录 | 版本 | 主要功能 |
| --- | --- | --- | --- |
| 海拉鲁 AI 字幕 | `plugins.v2/subtitlemanualupload`、`plugins.v3/subtitlemanualupload` | 2.2.1 | ChatGPT 订阅、双语 ASS/SRT、字幕清点、SubHD 官网下载与手动上传 |
| AI字幕生成(联动版) | `plugins.v2/autosubv3` | 3.5.54 | 音轨识别、字幕提取、AI 翻译、任务队列、联动字幕匹配 |
| Emby媒体库封面生成 | `plugins.v2/mediacovergenerator` | 0.9.10 | 生成 Emby/Jellyfin 媒体库静态或动态封面 |

## 海拉鲁 AI 字幕

新入库影片直接进入 AI 翻译队列。插件从英文外挂、内封字幕或本地 Whisper 识别结果获取原稿，使用 ChatGPT 订阅调研译名、分批精翻并审校全集。手动字幕从 SubHD 官网下载，回到选中的影片或集数上传。

「查看数据」可按状态筛选、排序和批量管理字幕任务，并保留旧联动版已结束的任务记录。重新生成会另存译稿。使用海拉鲁时可停用「AI字幕生成（联动版）」，NAS 上的 ChatGPT 订阅服务需要继续运行。

[安装、订阅授权与使用说明](plugins.v3/subtitlemanualupload/README.md)

## AI字幕生成(联动版)

用于从音轨、内嵌字幕或外挂字幕生成中文字幕，也可以接收“字幕匹配”提交的在线英文字幕。

主要功能：

- 支持 faster-whisper 语音识别。
- 支持优先使用外挂字幕或内嵌字幕。
- 支持 OpenAI 兼容接口翻译。
- 支持双语字幕或纯中文字幕输出。
- 支持批量任务、任务状态查看、取消和重新生成。
- 支持与“字幕匹配”互相联动。

## Emby媒体库封面生成

用于给 Emby/Jellyfin 媒体库生成统一风格的入口封面。

主要功能：

- 支持静态封面和动态封面。
- 支持多种封面风格、字体、分辨率和颜色策略。
- 支持从媒体库海报/背景图提取视觉元素。
- 支持媒体数量角标。
- 支持历史封面保存，方便回滚或复用。

## 安装方式

在 MoviePilot 第三方插件仓库中添加本仓库地址：

```text
https://github.com/sokouu87/MoviePilot-Plugins
```

海拉鲁 AI 字幕可单独安装。2.0 沿用原插件 ID，已安装用户可在原条目升级。

## 致谢

本仓库基于 MoviePilot 插件机制开发。

参考项目和源代码：

- [MoviePilot](https://github.com/jxxghp/MoviePilot)
- [MoviePilot-Plugins](https://github.com/jxxghp/MoviePilot-Plugins)
- [ChineseSubFinder](https://github.com/ChineseSubFinder/ChineseSubFinder)
- [allanpk716/chinesesubfinder](https://github.com/allanpk716/chinesesubfinder)
- [HappyQuQu/jellyfin-library-poster](https://github.com/HappyQuQu/jellyfin-library-poster)
- Emby媒体库封面生成插件原库：[justzerock/MoviePilot-Plugins](https://github.com/justzerock/MoviePilot-Plugins)

主要依赖库：

- `faster-whisper`
- `openai`
- `httpx`
- `watchdog`
- `pillow`
- `numpy`
