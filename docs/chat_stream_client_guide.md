# 流式 AI 对话接口 — App 接入指南

> 本文档聚焦于 **流式接口** 的客户端接入，包含 Android（Kotlin/OkHttp）与 Flutter（Dart/Dio）两套完整示例代码。

---

## 1. 接口信息

| 项 | 值 |
|---|---|
| URL | `POST https://www.huanguncle.cn/django/api/chat/conversations/{conversationId}/stream/` |
| 请求头 | `Authorization: Bearer <token>` |
| 请求头 | `Accept: text/event-stream` |
| 请求头 | `Content-Type: application/json` |
| 请求体 | `{"content": "用户消息内容"}` |
| 响应类型 | SSE（Server-Sent Events）逐行流式文本 |

---

## 2. SSE 协议格式

响应体是纯文本，每一条事件以 `data: <JSON>\n\n` 结尾（两个换行）。

```
: stream-open\n\n                             ← 注释行，客户端直接跳过
data: {"type":"status","content":"正在准备回复..."}\n\n
data: {"type":"status","content":"正在调用本地工具 xxx..."}\n\n
data: {"type":"tool_card","tool_name":"xxx","args":{...},"result":"..."}\n\n
data: {"type":"text","content":"贵"}\n\n
data: {"type":"text","content":"州茅台"}\n\n
data: {"type":"done"}\n\n
```

### 2.1 事件类型一览

| `type` | 说明 | 含有的字段 |
|---|---|---|
| `status` | 进度提示（准备中 / 调用工具中） | `content: String` |
| `tool_card` | 工具执行结果卡片 | `tool_name: String`, `args: Object`, `result: String` |
| `text` | AI 回复的文字片段（需拼接） | `content: String` |
| `done` | 流结束，连接可以关闭 | 无 |
| `error` | 出错 | `content: String`（错误信息） |

> **注意**：以 `: ` 开头的行是 SSE 注释，直接跳过即可，不需要解析。

### 2.2 解析一行的伪代码

```
读到一行原始文本 line:
  if line 以 ": " 开头  → 跳过（注释）
  if line 以 "data: " 开头 → json = line[6:] → 解析 JSON
  if line 为空           → 忽略
```

---

## 3. 完整交互流程

```
App                              Server
 |                                  |
 |-- POST /stream/ {content} ------>|
 |                                  | 写入 user 消息
 |<-- data: {type:status} ----------| 首包（准备中）
 |<-- data: {type:status} ----------| 调用工具中（如需）
 |<-- data: {type:tool_card} -------| 工具结果卡片（如需）
 |<-- data: {type:text} content:"贵"| 流式文字
 |<-- data: {type:text} content:"州"| ...
 |<-- data: {type:done} ------------| 结束
 |                                  | 落库 assistant 消息
 |  连接关闭                         |
```

---

## 4. Android（Kotlin + OkHttp）实现

### 4.1 添加依赖

```kotlin
// build.gradle.kts
implementation("com.squareup.okhttp3:okhttp:4.12.0")
```

### 4.2 核心实现

```kotlin
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader

data class SseEvent(
    val type: String,          // status / text / tool_card / done / error
    val content: String? = null,
    val toolName: String? = null,
    val args: JSONObject? = null,
    val result: String? = null,
)

class ChatStreamRepository(
    private val token: String,
    private val baseUrl: String = "https://www.huanguncle.cn",
) {
    private val client = OkHttpClient.Builder()
        .readTimeout(0, java.util.concurrent.TimeUnit.MILLISECONDS) // SSE 不超时
        .build()

    /**
     * 发送消息并以 Flow 形式逐条返回 SSE 事件
     *
     * 使用方：
     *   viewModelScope.launch {
     *       repo.streamChat(conversationId, "用户消息").collect { event ->
     *           when (event.type) {
     *               "status"    -> showLoading(event.content)
     *               "text"      -> appendText(event.content)
     *               "tool_card" -> showToolCard(event.toolName, event.result)
     *               "done"      -> hideLoading()
     *               "error"     -> showError(event.content)
     *           }
     *       }
     *   }
     */
    fun streamChat(conversationId: Long, content: String): Flow<SseEvent> = flow {
        val body = JSONObject().apply { put("content", content) }
            .toString()
            .toRequestBody("application/json; charset=utf-8".toMediaType())

        val request = Request.Builder()
            .url("$baseUrl/django/api/chat/conversations/$conversationId/stream/")
            .addHeader("Authorization", "Bearer $token")
            .addHeader("Accept", "text/event-stream")
            .post(body)
            .build()

        val response = client.newCall(request).execute()

        if (!response.isSuccessful) {
            emit(SseEvent(type = "error", content = "HTTP ${response.code}"))
            return@flow
        }

        val reader = BufferedReader(InputStreamReader(response.body!!.byteStream(), Charsets.UTF_8))
        try {
            var line: String?
            while (reader.readLine().also { line = it } != null) {
                val trimmed = line!!.trim()
                // 跳过注释行和空行
                if (trimmed.isEmpty() || trimmed.startsWith(":")) continue
                // 解析 data: 行
                if (!trimmed.startsWith("data:")) continue
                val jsonStr = trimmed.removePrefix("data:").trim()
                val json = runCatching { JSONObject(jsonStr) }.getOrNull() ?: continue
                val event = parseSseEvent(json)
                emit(event)
                if (event.type == "done" || event.type == "error") break
            }
        } finally {
            reader.close()
            response.close()
        }
    }

    private fun parseSseEvent(json: JSONObject): SseEvent {
        return when (val type = json.optString("type")) {
            "text"      -> SseEvent(type = type, content = json.optString("content"))
            "status"    -> SseEvent(type = type, content = json.optString("content"))
            "tool_card" -> SseEvent(
                type = type,
                toolName = json.optString("tool_name"),
                args = json.optJSONObject("args"),
                result = json.optString("result"),
            )
            "done"  -> SseEvent(type = type)
            "error" -> SseEvent(type = type, content = json.optString("content"))
            else    -> SseEvent(type = "unknown")
        }
    }
}
```

### 4.3 ViewModel 调用示例

```kotlin
class ChatViewModel(private val repo: ChatStreamRepository) : ViewModel() {

    val displayText = MutableStateFlow("")
    val statusText  = MutableStateFlow("")
    val isLoading   = MutableStateFlow(false)

    fun sendMessage(conversationId: Long, content: String) {
        displayText.value = ""
        isLoading.value = true

        viewModelScope.launch(Dispatchers.IO) {
            repo.streamChat(conversationId, content).collect { event ->
                when (event.type) {
                    "status" -> statusText.value = event.content ?: ""
                    "text"   -> displayText.value += event.content ?: ""
                    "tool_card" -> {
                        // 渲染工具卡片，例如展示股票行情表格
                        statusText.value = "数据加载完成：${event.toolName}"
                    }
                    "done", "error" -> {
                        isLoading.value = false
                        statusText.value = ""
                    }
                }
            }
        }
    }
}
```

---

## 5. Flutter（Dart + http 包）实现

### 5.1 添加依赖

```yaml
# pubspec.yaml
dependencies:
  http: ^1.2.0
```

### 5.2 核心实现

```dart
import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

enum SseEventType { status, text, toolCard, done, error, unknown }

class SseEvent {
  final SseEventType type;
  final String? content;
  final String? toolName;
  final Map<String, dynamic>? args;
  final String? result;

  const SseEvent({
    required this.type,
    this.content,
    this.toolName,
    this.args,
    this.result,
  });
}

class ChatStreamService {
  final String token;
  final String baseUrl;

  ChatStreamService({required this.token, this.baseUrl = 'https://www.huanguncle.cn'});

  /// 返回 Stream<SseEvent>，每收到一条 SSE 事件就 yield 一次
  ///
  /// 用法：
  ///   chatService.streamChat(conversationId, '用户消息').listen((event) {
  ///     switch (event.type) {
  ///       case SseEventType.text:      setState(() => _text += event.content!);
  ///       case SseEventType.status:    setState(() => _status = event.content!);
  ///       case SseEventType.toolCard:  _showToolCard(event);
  ///       case SseEventType.done:      setState(() => _loading = false);
  ///       case SseEventType.error:     _showError(event.content);
  ///       default: break;
  ///     }
  ///   });
  Stream<SseEvent> streamChat(int conversationId, String content) async* {
    final uri = Uri.parse(
      '$baseUrl/django/api/chat/conversations/$conversationId/stream/',
    );

    final request = http.Request('POST', uri)
      ..headers['Authorization'] = 'Bearer $token'
      ..headers['Accept'] = 'text/event-stream'
      ..headers['Content-Type'] = 'application/json; charset=utf-8'
      ..body = jsonEncode({'content': content});

    final http.Client client = http.Client();
    try {
      final streamedResponse = await client.send(request);

      if (streamedResponse.statusCode != 200) {
        yield SseEvent(
          type: SseEventType.error,
          content: 'HTTP ${streamedResponse.statusCode}',
        );
        return;
      }

      // 按行拆分响应字节流
      final lineStream = streamedResponse.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter());

      await for (final line in lineStream) {
        final trimmed = line.trim();
        // 跳过注释行和空行
        if (trimmed.isEmpty || trimmed.startsWith(':')) continue;
        if (!trimmed.startsWith('data:')) continue;

        final jsonStr = trimmed.substring('data:'.length).trim();
        final Map<String, dynamic> json;
        try {
          json = jsonDecode(jsonStr) as Map<String, dynamic>;
        } catch (_) {
          continue;
        }

        final event = _parseSseEvent(json);
        yield event;
        if (event.type == SseEventType.done || event.type == SseEventType.error) break;
      }
    } finally {
      client.close();
    }
  }

  SseEvent _parseSseEvent(Map<String, dynamic> json) {
    final type = json['type'] as String? ?? '';
    switch (type) {
      case 'text':
        return SseEvent(type: SseEventType.text, content: json['content'] as String?);
      case 'status':
        return SseEvent(type: SseEventType.status, content: json['content'] as String?);
      case 'tool_card':
        return SseEvent(
          type: SseEventType.toolCard,
          toolName: json['tool_name'] as String?,
          args: json['args'] as Map<String, dynamic>?,
          result: json['result'] as String?,
        );
      case 'done':
        return SseEvent(type: SseEventType.done);
      case 'error':
        return SseEvent(type: SseEventType.error, content: json['content'] as String?);
      default:
        return SseEvent(type: SseEventType.unknown);
    }
  }
}
```

### 5.3 Widget 调用示例

```dart
class _ChatPageState extends State<ChatPage> {
  String _displayText = '';
  String _statusText  = '';
  bool   _loading     = false;
  StreamSubscription? _sub;

  void _send(String content) {
    setState(() { _displayText = ''; _loading = true; });

    _sub?.cancel();
    _sub = chatService.streamChat(widget.conversationId, content).listen(
      (event) {
        setState(() {
          switch (event.type) {
            case SseEventType.status:
              _statusText = event.content ?? '';
            case SseEventType.text:
              _displayText += event.content ?? '';
            case SseEventType.toolCard:
              // 插入工具卡片 Widget，例如行情表格
              _statusText = '数据已加载：${event.toolName}';
            case SseEventType.done:
              _loading = false;
              _statusText = '';
            case SseEventType.error:
              _loading = false;
              _statusText = '出错：${event.content}';
            default:
              break;
          }
        });
      },
      onError: (e) => setState(() { _loading = false; _statusText = '连接出错'; }),
      onDone: ()  => setState(() { _loading = false; }),
      cancelOnError: true,
    );
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}
```

---

## 6. 常见错误排查

| 现象 | 原因 | 解决方式 |
|---|---|---|
| 全部内容一次性出来 | 客户端用了 `response.body` / `await body.string()` 等整包读取 | 改为流式逐行读（见示例） |
| 首包很慢才来 | 网络或代理缓冲 | 服务端已加 `X-Accel-Buffering: no`；确认 nginx 有 `proxy_buffering off` |
| 中文乱码 | 未指定 UTF-8 解码 | 解码时明确用 `Charsets.UTF_8`（Android）或 `utf8.decoder`（Flutter） |
| 连接立刻断开 | OkHttp 默认读超时 30s | 设置 `readTimeout(0, ...)` 禁用读超时 |
| 401 / 403 | Token 未带或已过期 | 请求头加 `Authorization: Bearer <token>` |
| 收到 `error` 事件 | 模型调用失败 / 工具执行失败 | 读 `content` 字段，提示用户，结束本次流 |

---

## 7. 推荐的 UI 交互逻辑

```
收到 status  → 气泡底部显示加载动画 + 提示文字（如"正在调用数据..."）
收到 tool_card → 在对话中渲染数据卡片（行情表格、K线等）
收到 text    → 打字机效果逐字追加到 AI 气泡内
收到 done    → 隐藏加载动画，滚动到底部
收到 error   → 隐藏动画，显示错误提示，允许重试
```
