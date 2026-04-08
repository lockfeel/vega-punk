# Vega-Punk 文件上传功能设计规格

**日期:** 2026-04-09
**功能:** 聊天增加文件和图片支持
**模式:** CONDENSED

---

## 1. Goal (目标)

在 vega-punk 聊天系统中增加文件上传功能，用户可通过前端上传文件到阿里云 OSS，返回公网 URL 后发送给 AI 处理。

---

## 2. How (实现方式)

### 架构流程

```
用户选择文件 → 前端上传到阿里云 OSS → 返回公网 URL → WebSocket 发送 URL → vega.py 转发给 AI
```

### 支持的文件类型

| 类型 | 格式 |
|------|------|
| 图片 | jpg, jpeg, png, gif, webp, bmp |
| 文档 | doc, docx, ppt, pptx, xls, xlsx, pdf, txt, json |

---

## 3. 接口设计

### 前端 → 后端上传接口

**POST /upload**

| 参数 | 类型 | 说明 |
|------|------|------|
| file | FormData | 上传的文件 |

**响应:**

```json
{
  "success": true,
  "url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/2026-04-09/xxx.jpg",
  "filename": "example.jpg",
  "filetype": "image/jpeg",
  "size": 1024000
}
```

### 前端 → WebSocket 消息格式

```json
{
  "type": "file",
  "user": "user-id",
  "text": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/xxx.jpg",
  "botId": "vega-punk",
  "filename": "example.jpg",
  "filetype": "image/jpeg"
}
```

---

## 4. 文件存储路径

- OSS Bucket: `your-bucket`
- OSS Endpoint: `oss-cn-hangzhou.aliyuncs.com`
- 文件存储路径: `{year}-{month}/{uuid}-{filename}`

---

## 5. 配置项

通过环境变量或配置文件管理：

| 配置项 | 说明 |
|--------|------|
| OSS_ACCESS_KEY_ID | 阿里云 AccessKey |
| OSS_ACCESS_KEY_SECRET | 阿里云 Secret |
| OSS_BUCKET_NAME | Bucket 名称 |
| OSS_ENDPOINT | OSS 节点 |
| OSS_PUBLIC_HOST | 公网访问域名 |

---

## 6. 前后端改动清单

### 后端 (service/)

| 文件 | 改动 |
|------|------|
| `oss_uploader.py` (新建) | 阿里云 OSS 上传封装 |
| `vega.py` | 增加 `/upload` 接口；WebSocket 消息增加 `type=file` 处理 |
| `requirements.txt` (新建) | 依赖: `aliyun-python-sdk-core`, `aliyun-python-sdk-oss` |

### 前端 (service/templates/)

| 文件 | 改动 |
|------|------|
| `chats.html` | 增加文件上传按钮、拖拽支持、文件预览、消息渲染 |

---

## 7. 测试计划

- [ ] 单图片上传成功
- [ ] 单文档上传成功
- [ ] 多文件上传
- [ ] 大文件 (>10MB) 上传
- [ ] 不支持的文件类型提示错误
- [ ] 聊天中图片消息正常显示
- [ ] 聊天中文件消息显示文件名和图标
- [ ] AI 能正确接收文件 URL 并处理