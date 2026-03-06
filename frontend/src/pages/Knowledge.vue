<template>
  <div>
    <div class="card">
      <h2>知识库管理</h2>
      <div class="form-grid">
        <div>
          <label>标题</label>
          <input v-model="newItem.title" />
        </div>
        <div>
          <label>内容</label>
          <textarea v-model="newItem.content"></textarea>
        </div>
      </div>
      <div class="flex" style="margin-top: 12px;">
        <button @click="add" :disabled="adding">添加</button>
        <span v-if="message" class="notice">{{ message }}</span>
      </div>
    </div>

    <div class="card">
      <h2>检索</h2>
      <div class="flex">
        <input v-model="query" placeholder="请输入关键字" />
        <button @click="search" :disabled="searching">搜索</button>
      </div>
      <div v-if="searchResults.length" style="margin-top: 12px;">
        <table class="table">
          <thead>
            <tr>
              <th>内容</th>
              <th>相似度</th>
              <th>来源</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, idx) in searchResults" :key="idx">
              <td>{{ item.content }}</td>
              <td>{{ item.score }}</td>
              <td>{{ item.source }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <h2>全部条目</h2>
      <table class="table" v-if="items.length">
        <thead>
          <tr>
            <th>编号</th>
            <th>标题</th>
            <th>内容</th>
            <th>创建时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>{{ item.id }}</td>
            <td>{{ item.title }}</td>
            <td>{{ item.content }}</td>
            <td>{{ formatTime(item.created_at) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="notice">暂无知识条目。</div>
      <div v-if="error" class="notice error">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';
import { api } from '../api/endpoints';

const items = ref([]);
const searchResults = ref([]);
const query = ref('');
const message = ref('');
const error = ref('');
const adding = ref(false);
const searching = ref(false);

const newItem = reactive({
  title: '',
  content: ''
});

const formatTime = (value) => (value ? new Date(value).toLocaleString() : '');

async function load() {
  try {
    const data = await api.listKnowledge();
    items.value = data.knowledge_items || [];
  } catch (e) {
    error.value = e.message || '加载失败。';
  }
}

async function add() {
  if (!newItem.title.trim() || !newItem.content.trim()) {
    message.value = '标题和内容不能为空。';
    return;
  }
  adding.value = true;
  message.value = '';
  try {
    const data = await api.addKnowledge({ title: newItem.title, content: newItem.content });
    message.value = data.message || '添加成功。';
    newItem.title = '';
    newItem.content = '';
    await load();
  } catch (e) {
    message.value = e.message || '添加失败。';
  } finally {
    adding.value = false;
  }
}

async function search() {
  if (!query.value.trim()) return;
  searching.value = true;
  try {
    const data = await api.searchKnowledge({ query: query.value });
    searchResults.value = data.results || [];
  } catch (e) {
    message.value = e.message || '搜索失败。';
  } finally {
    searching.value = false;
  }
}

onMounted(load);
</script>
