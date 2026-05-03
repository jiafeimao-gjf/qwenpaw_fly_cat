<template>
  <div class="message-bubble" :class="{ 'user': isUser, 'ai': !isUser }">
    <div class="bubble-content" v-html="renderedContent"></div>
    <div class="bubble-time">{{ time }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  content: String,
  isUser: Boolean,
  timestamp: Number
})

const time = computed(() => {
  if (!props.timestamp) return ''
  return new Date(props.timestamp * 1000).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})

const renderedContent = computed(() => {
  if (!props.content) return ''
  if (props.isUser) {
    return DOMPurify.sanitize(props.content)
  }
  const html = marked.parse(props.content)
  return DOMPurify.sanitize(html)
})
</script>

<style scoped>
.message-bubble {
  max-width: 70%;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  margin-bottom: 0.5rem;
}
.user {
  background: #4a90e2;
  color: white;
  margin-left: auto;
  border-bottom-right-radius: 4px;
}
.ai {
  background: #e8e8e8;
  color: #333;
  margin-right: auto;
  border-bottom-left-radius: 4px;
}
.bubble-content {
  line-height: 1.5;
  word-wrap: break-word;
}
.bubble-content :deep(code) {
  background: rgba(0,0,0,0.1);
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  font-family: monospace;
}
.bubble-content :deep(pre) {
  background: rgba(0,0,0,0.1);
  padding: 0.5rem;
  border-radius: 4px;
  overflow-x: auto;
  margin: 0.25rem 0;
}
.bubble-content :deep(p) {
  margin: 0.25rem 0;
}
.bubble-content :deep(ul), .bubble-content :deep(ol) {
  margin: 0.25rem 0;
  padding-left: 1.5rem;
}
.bubble-time {
  font-size: 0.625rem;
  margin-top: 0.25rem;
  opacity: 0.7;
  text-align: right;
}
</style>