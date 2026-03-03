<template>
  <div>
    <div class="card">
      <h2>知识库上传</h2>
      <input type="file" @change="onFile" />
      <div class="flex" style="margin-top: 12px;">
        <button @click="upload" :disabled="!file || loading">上传</button>
        <span v-if="message" class="notice">{{ message }}</span>
      </div>
      <div v-if="error" class="notice error">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { api } from '../api/endpoints';

const file = ref(null);
const loading = ref(false);
const message = ref('');
const error = ref('');

function onFile(e) {
  file.value = e.target.files[0] || null;
}

async function upload() {
  if (!file.value) return;
  loading.value = true;
  message.value = '';
  error.value = '';
  try {
    const form = new FormData();
    form.append('single_file', file.value);
    const data = await api.uploadKnowledgeFile(form);
    message.value = data.message || `上传成功。数量: ${data.count || 0}`;
  } catch (e) {
    error.value = e.message || '上传失败。';
  } finally {
    loading.value = false;
  }
}
</script>
