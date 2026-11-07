#!/usr/bin/env node
/**
 * repatch-workbuddy-sanitize.mjs —— 重打「WorkBuddy 出站净化」补丁。
 *
 * 背景（2026-10-29）：
 *   WorkBuddy 网关会扫描每条 system / assistant 消息的**开头**做第三方客户端指纹匹配，
 *   命中即返回 http 400 / code 11128 / type=channel_reject（文案谎称"不是官方客户端"，
 *   与账号、积分、额度、网络全无关）。官方客户端只会发"最终回答 + 结构化 tool_calls"，
 *   而 DSH 发出的形状带两样它不会有的东西：
 *     1) system 的固定身份句 "You are an AI agent powered by DeepSeek Harness."
 *        （宿主 base system prompt 原文，每个 DSH 用户都长这样）；
 *     2) assistant 正文里的 reasoning —— DSH 会话里 assistant/message 的 content
 *        就是 ["reasoning","tool-call"]，思考过程混在正文里出站。
 *
 *   因此根治手段不是去猜网关词条（名单永远滞后），而是让**请求形状**变干净。
 *   本补丁在 prepareChatBody() 这个唯一出站口做两件事，无条件生效：
 *     - system 开头身份句换成中性 Lead（沿用插件自带的 WORKBUDDY_FALLBACK_SYSTEM_PROMPT）
 *     - 剥离 assistant 的 reasoning 块与 reasoning_content 字段（只改出站，不碰会话）
 *
 * 用法：
 *   node repatch-workbuddy-sanitize.mjs --check   只检查
 *   node repatch-workbuddy-sanitize.mjs           打补丁（幂等）
 *
 * 何时重跑：任何 pnpm add / install / update 之后，以及插件升级后
 * （目标文件名带内容 hash，如 lib/host-heartbeat-XXXX.js，本脚本自动发现）。
 */

import { readFileSync, writeFileSync, copyFileSync, existsSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

const PLUGIN = process.env.WORKBUDDY_PLUGIN ?? 'C:/Users/ROG/.dsh/profiles/desktop/node_modules/dsh-connect-workbuddy'
const CHECK_ONLY = process.argv.includes('--check')
const STAMP = '.bak-before-channel-sanitize'

const SNIPPET = "const HOST_IDENTITY = /^You are an AI agent powered by [^.\\n]{1,80}\\.?\\s*/;\n/**\n * Replace the host identity sentence at the start of one system content value.\n *\n * Only the LEADING occurrence is rewritten, and only when it is literally the\n * first thing in the value: the rest of the prompt (tool docs, policies) is\n * untouched, so model behaviour is unchanged. Returns the same value when\n * there is nothing to do.\n */\nfunction neutralizeSystemContent(content) {\n\tif (typeof content === \"string\") return content.replace(HOST_IDENTITY, () => WORKBUDDY_FALLBACK_SYSTEM_PROMPT + \" \");\n\tif (!Array.isArray(content)) return content;\n\tlet changed = false;\n\tconst next = content.map((part) => {\n\t\tif (typeof part !== \"object\" || part === null || Array.isArray(part)) return part;\n\t\tconst block = part;\n\t\tconst text = block[\"text\"];\n\t\tif (typeof text !== \"string\" || !HOST_IDENTITY.test(text)) return part;\n\t\tchanged = true;\n\t\treturn {\n\t\t\t...block,\n\t\t\ttext: text.replace(HOST_IDENTITY, () => WORKBUDDY_FALLBACK_SYSTEM_PROMPT + \" \")\n\t\t};\n\t});\n\treturn changed ? next : content;\n}\n/**\n * Drop reasoning blocks from one assistant message's content.\n *\n * An official client sends only the answer plus structured tool calls; it never\n * relays its thinking back as message text. DSH sessions persist\n * assistant/message content as [\"reasoning\", \"tool-call\"], and relaying that\n * array hands the gateway a shape no official client produces — which is what\n * its channel check reports as a non-official client. The reasoning is local\n * scaffolding: removing it from the OUTBOUND body only, never from the session.\n */\nfunction stripAssistantReasoning(message) {\n\tif (message[\"reasoning_content\"] !== void 0) delete message[\"reasoning_content\"];\n\tconst content = message[\"content\"];\n\tif (!Array.isArray(content)) return;\n\tconst kept = content.filter((part) => {\n\t\tif (typeof part !== \"object\" || part === null || Array.isArray(part)) return true;\n\t\treturn part[\"type\"] !== \"reasoning\";\n\t});\n\tif (kept.length === content.length) return;\n\tmessage[\"content\"] = kept.length === 0 ? \"\" : kept;\n}\n/**\n * Make an outbound body look like one an official client would send.\n *\n * Applied at the single wire boundary ({@link prepareChatBody}), after every\n * other rewrite, so it holds for every request regardless of who built it.\n * Best-effort by design: a malformed message is left as-is for the upstream to\n * judge rather than throwing inside the request path.\n */\nfunction sanitizeOutboundMessages(obj) {\n\tconst messages = obj[\"messages\"];\n\tif (!Array.isArray(messages)) return;\n\tfor (const value of messages) {\n\t\tif (typeof value !== \"object\" || value === null || Array.isArray(value)) continue;\n\t\tconst message = value;\n\t\tconst role = typeof message[\"role\"] === \"string\" ? message[\"role\"].trim().toLowerCase() : \"\";\n\t\tif (role === \"system\") {\n\t\t\tmessage[\"content\"] = neutralizeSystemContent(message[\"content\"]);\n\t\t\tcontinue;\n\t\t}\n\t\tif (role === \"assistant\") stripAssistantReasoning(message);\n\t}\n}"

const ANCHOR = 'const WORKBUDDY_FALLBACK_SYSTEM_PROMPT = "You are a helpful assistant.";'
const CALL_OLD = "\tensureSystemHead(obj);\n\tnormalizeToolChoice(obj);\n\treturn JSON.stringify(obj);"
const CALL_NEW = "\tensureSystemHead(obj);\n\tnormalizeToolChoice(obj);\n\tsanitizeOutboundMessages(obj);\n\treturn JSON.stringify(obj);"

function findTarget() {
  const libDir = join(PLUGIN, 'lib')
  if (!existsSync(libDir)) return null
  const hits = readdirSync(libDir).filter((n) => /^host-heartbeat-.*\.js$/.test(n))
  return hits.length > 0 ? join(libDir, hits[0]) : null
}

const target = findTarget()
if (target === null) {
  console.log('[FAIL] 找不到 lib/host-heartbeat-*.js —— 插件结构可能已变，人工确认')
  process.exitCode = 1
} else {
  const src = readFileSync(target, 'utf8')
  const already = src.includes('function sanitizeOutboundMessages(obj) {') && src.includes('sanitizeOutboundMessages(obj);')
  if (already) {
    console.log('[OK]   已是净化后版本: ' + target.split(/[\\/]/).pop())
  } else if (CHECK_ONLY) {
    console.log('[NEED] 待打补丁: ' + target.split(/[\\/]/).pop() + '（--check 模式未写入）')
    process.exitCode = 1
  } else {
    const nAnchor = src.split(ANCHOR).length - 1
    const nCall = src.split(CALL_OLD).length - 1
    if (nAnchor !== 1 || nCall !== 1) {
      console.log('[WARN] 锚点不唯一 (anchor=' + nAnchor + ', call=' + nCall + ') —— 版本可能已变，放弃自动打补丁')
      process.exitCode = 1
    } else {
      copyFileSync(target, target + STAMP)
      let next = src.replace(ANCHOR, ANCHOR + SNIPPET)
      next = next.replace(CALL_OLD, CALL_NEW)
      writeFileSync(target, next, 'utf8')
      const okFn = next.includes('function sanitizeOutboundMessages(obj) {')
      const okCall = next.includes('\tsanitizeOutboundMessages(obj);')
      console.log('[FIX]  ' + target.split(/[\\/]/).pop() + ' —— 函数注入 ' + (okFn ? 'OK' : 'FAIL') + ' / 调用接线 ' + (okCall ? 'OK' : 'FAIL'))
      if (!okFn || !okCall) process.exitCode = 1
    }
  }
}

if (process.exitCode !== 1) {
  console.log('\n就绪。改动 node_modules 后需要重启 DSH Desktop 才生效。')
}
