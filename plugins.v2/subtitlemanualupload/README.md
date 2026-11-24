# 海拉鲁 AI 字幕

MoviePilot 入库后，插件按英文外挂、完整英文文本轨、本地 Whisper 听写的顺序选择原稿。ChatGPT 订阅负责调研、精翻和审校。保留原插件标识 `SubtitleManualUpload`，V2 和 V3 使用同一个安装包。

## 使用

1. 在插件设置启用「海拉鲁 AI 字幕」和「入库后自动翻译」。升级会继承以前的入库开关。旧「AI字幕生成（联动版）」可以停用，保留 NAS 上已授权的 ChatGPT 订阅服务运行。
2. 在侧栏或插件「查看数据」打开清单。一个搜索框覆盖 MoviePilot 入库记录和 Emby 片库。每个片源显示最近的任务，可展开查看审校和历史。
3. 片源右侧可选择「AI 生成」「SubHD」或「上传」。上传对话框提供作品资料和剧集译名表。AI 任务会显示原稿来源、处理阶段、审校记录和输出文件。
4. SubHD 在新标签打开。完成官网验证和下载后，返回原列表上传。ZIP 中有多个字幕时可指定成员。RAR 和 7z 请先解压。英文原稿可以提交 AI 翻译。

自动处理只监听新的整理事件。索引已有电影、剧集和配置中的 STRM 目录供手动操作。STRM 的 AI 翻译需要本地英文外挂或上传的英文原稿，插件只读本地文件。Whisper 需要容器内的 ffmpeg、ffprobe 和本地 CTranslate2 模型目录。设置留空时优先复用旧 AutoSubv3 的 large-v3 模型缓存。

## 查看数据

列表默认最新在前。可按最近入库、中文覆盖、原盘和任务状态筛选。内嵌字幕、已生成的双语文件和缺英文原稿用主题色标签显示。

勾选任务后可以批量操作。「取消」可停止等待任务，运行中的任务会在当前步骤结束后停止。「重新生成」按当前设置从头翻译，另存为 `.r<任务号>.zh-en.ai.ass` 和对应的 SRT。「删除」仅移除海拉鲁面板上的记录，保留视频和字幕文件。

升级后，列表自动读取原「AI字幕生成（联动版）」已结束的任务，标记为「联动版历史」。原插件停用后，已导入的记录仍可查看。

## Emby 和原盘

同一视频按实际路径合并。Emby 库与 MoviePilot 的挂载名称不同时，在插件设置填写「Emby 目录映射」，每行一个 `/Emby路径=/MoviePilot路径`。映射只应用于 Emby 返回的媒体库目录。

蓝光和 DVD 原盘按影片目录归组。蓝光通过主播放列表识别内封中文，也会核对 Emby 已识别的主片字幕。缺少可靠轨道信息的原盘显示待确认。原盘使用 SubHD 和手动上传。能够确定单一主片时，外挂按主片文件名保存在它旁边。无法定位单一主片时，外挂保存在影片目录，可在播放器手动加载。字幕写入有同名文件校验。

## ChatGPT 套餐授权

插件访问同一网络命名空间的 `127.0.0.1:18743`。字幕专用订阅服务的源文件在 `subscription/`。模型与推理档位可配置，默认 `gpt-6.2-astra / high`。订阅不可用时，任务保留失败原因，不会切换到按量计费的 API。

- 已部署 1.0 服务时，用本版 Dockerfile 构建新镜像，以原网络模式、端口和专用状态卷替换运行容器。保持同一时间只有一个服务写入该卷。升级后既支持新的精翻接口，也支持旧插件的 Chat Completions。保留旧镜像可回滚。
- 首次使用时，在浏览器所在电脑建立私有凭证目录，用 Node.js 22 或更新版本运行 `node authorize.mjs <私有目录>`。打开控制台显示的回环登录入口，完成 OpenAI 授权。用受保护的传输方式将生成的 `credentials.json` 放入 NAS 的专用持久卷 `/state`。运行用户为 `65532:65532`，目录权限 0700，凭证权限 0600。
- 镜像可从 `subscription/` 运行 `docker build -t local/moviepilot-chatgpt-subtitle:2.0.0 .` 构建。若 MoviePilot 使用主机网络，可用 `docker run -d --name moviepilot-chatgpt-subtitle --network host --restart unless-stopped -v moviepilot-chatgpt-subtitle-state:/state local/moviepilot-chatgpt-subtitle:2.0.0`。使用容器网络时改用 `--network container:<MoviePilot容器名>`。首次启动前，确保该卷的所有者和权限已设置。
- 服务首次运行会在同卷生成 `bridge.key`。插件可继承 AutoSubv3 中指向上述回环地址的 `chatgpt-subscription` 专用线路，也可以在插件设置填写本地密钥。OAuth 令牌始终由订阅服务保存和续期。

## 翻译与输出

全片英文和元数据用于第一次联网调研。模型考证人物关系、惯用译名和年代语气。分批精翻按顺序处理，每批最多 100 轴，附前五轴中文、后五轴英文及译名表。新增专名单独查证。最后按整集中英对照做一致性审校。网站访问和严格 JSON Schema 分两次调用，网页依据来自实际的搜索工具事件。字幕内容和所需元数据将发送给已授权的 OpenAI 服务。

每集输出同名的 `.zh-en.ai.ass` 和 `.zh-en.ai.srt`。ASS 使用 PingFang SC 和 Helvetica，支持英文整句斜体、顶部画面字和少量注释。时间码和英文由本地排版。常规音效丢弃，剧情音效保留。SRT 按保留的轴重新编号。人工字幕使用独立的语言后缀。写入遇到同名不同内容会保留原文件。

剧集词表、队列和断点保存在原插件数据目录下的 `ai_studio/`。词表按作品区分，文件名为 `glossary.json`。播放器字体表现取决于本机字体和渲染器。

[OpenAI 自托管授权指南](https://developers.openai.com/siwc/token-sharing-open-source/self-hosted-vms) · [订阅推理说明](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
