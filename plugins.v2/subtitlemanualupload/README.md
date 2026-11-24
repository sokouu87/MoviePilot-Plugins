# 海拉鲁 AI 字幕

MoviePilot 入库后，插件按英文外挂、完整英文文本轨、本地 Whisper 听写的顺序选择原稿。ChatGPT 订阅负责调研、精翻和审校。保留原插件标识 `SubtitleManualUpload`，V2 和 V3 使用同一个安装包。

## 使用

1. 在插件设置启用「海拉鲁 AI 字幕」和「入库后自动翻译」。升级会继承以前的入库开关。旧「AI字幕生成（联动版）」可以停用，保留 NAS 上已授权的 ChatGPT 订阅服务运行。
2. 手动处理时，打开侧栏的「海拉鲁 AI 字幕」，切换到「片库字幕」，选择具体影片或集数。可以补充作品资料，或打开「本剧译名表」编辑和导入 JSON。
3. 点击「AI 翻译」。任务记录会显示来源、阶段、歧义、阅读速度警告、调研时打开或引用的网页，以及写出的文件名。失败任务可从已通过质检的批次续跑。
4. 需要现成字幕时，点击「在 SubHD 搜索」。官网在新标签打开。按网站要求完成验证和下载，返回原标签，选择文件和用途后上传。ZIP 有多个字幕时须选择成员。RAR、7z 请先解压。英文原稿上传后可点击「AI 翻译」，中文成品可直接播放。

自动处理只监听新的整理事件。索引已有电影、剧集和配置中的 STRM 目录供手动操作。STRM 的 AI 翻译需要本地英文外挂或上传的英文原稿，插件只读本地文件。Whisper 需要容器内的 ffmpeg、ffprobe 和本地 CTranslate2 模型目录。设置留空时优先复用旧 AutoSubv3 的 large-v3 模型缓存。

## 查看数据

从侧栏打开「海拉鲁 AI 字幕」，或在「插件」页打开「查看数据」，都能看到同一个任务面板。列表默认最新在前，顶部的状态计数可以筛选任务。每张卡片显示媒体路径、任务来源、字幕来源、时间、输出文件和失败原因。

勾选任务后可以批量操作。「取消」可停止等待任务，运行中的任务会在当前步骤结束后停止。「重新生成」按当前设置从头翻译，另存为 `.r<任务号>.zh-en.ai.ass` 和对应的 SRT。「删除」仅移除海拉鲁面板上的记录，保留视频和字幕文件。

升级后，列表自动读取原「AI字幕生成（联动版）」已结束的任务，标记为「联动版历史」。原插件停用后，已导入的记录仍可查看。

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
