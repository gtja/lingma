<template>
  <div>
    <div class="card">
      <h2>PRD 分析</h2>
      <input type="file" @change="onFile" accept=".docx" />
      <div class="flex" style="margin-top: 12px;">
        <button @click="analyse" :disabled="!file || loading">开始分析</button>
      </div>
      <div v-if="message" class="notice">{{ message }}</div>
      <div v-if="error" class="notice error">{{ error }}</div>
    </div>

    <div class="card" v-if="result">
      <h2>分析结果</h2>
      <template v-if="parsedResult">
        <div class="summary-grid" v-if="parsedResult.summary">
          <div class="summary-item">
            <div class="label">测试点总数</div>
            <div class="value">{{ parsedResult.summary.total_test_points }}</div>
          </div>
          <div class="summary-item">
            <div class="label">场景总数</div>
            <div class="value">{{ parsedResult.summary.total_test_scenarios }}</div>
          </div>
          <div class="summary-item">
            <div class="label">高优先级</div>
            <div class="value">{{ parsedResult.summary.high_priority_points }}</div>
          </div>
          <div class="summary-item">
            <div class="label">中优先级</div>
            <div class="value">{{ parsedResult.summary.medium_priority_points }}</div>
          </div>
          <div class="summary-item">
            <div class="label">低优先级</div>
            <div class="value">{{ parsedResult.summary.low_priority_points }}</div>
          </div>
        </div>

        <div class="points" v-if="parsedResult.test_points">
          <details v-for="tp in parsedResult.test_points" :key="tp.id" class="tp-item">
            <summary>
              <span class="tp-title">{{ tp.title }}</span>
              <span class="badge">{{ tp.id }}</span>
              <span class="badge" :class="priorityClass(tp.priority)">{{ tp.priority }}</span>
              <span class="muted">场景 {{ (tp.scenarios || []).length }}</span>
            </summary>
            <div class="tp-body">
              <div class="tp-desc">{{ tp.description }}</div>
              <div class="scenarios">
                <div v-for="sc in tp.scenarios" :key="sc.id" class="scenario">
                  <div class="scenario-header">
                    <span class="scenario-title">{{ sc.title }}</span>
                    <span class="badge">{{ sc.id }}</span>
                    <span class="tag">{{ sc.test_type }}</span>
                  </div>
                  <pre class="text-block">{{ sc.description }}</pre>
                </div>
              </div>
            </div>
          </details>
        </div>
      </template>
      <template v-else>
        <pre>{{ rawResult }}</pre>
      </template>
    </div>

    <div class="card" v-if="prdContent">
      <h2>PRD 内容</h2>
      <pre>{{ prdContent }}</pre>
    </div>

    <div class="card">
      <h2>历史记录</h2>
      <div v-if="loadingHistory" class="notice">加载中...</div>
      <div v-else-if="history.length === 0" class="muted">暂无记录</div>
      <div v-else class="history-list">
        <div class="history-item" v-for="item in history" :key="item.id">
          <div class="history-main">
            <div class="history-title">{{ item.file_name }}</div>
            <div class="muted">{{ formatTime(item.created_at) }}</div>
          </div>
          <div class="flex">
            <button @click="openDetail(item.id)">
              {{ detail && detail.id === item.id ? '收起' : '详情' }}
            </button>
            <button class="danger" @click="deleteHistory(item.id)">删除</button>
          </div>
        </div>
      </div>
      <div v-if="historyError" class="notice error">{{ historyError }}</div>
    </div>

    <div class="card" v-if="detail">
      <h2>记录详情</h2>
      <div class="detail-meta">
        <div class="detail-title">{{ detail.file_name }}</div>
        <div class="muted">{{ formatTime(detail.created_at) }}</div>
      </div>

      <div class="detail-section">
        <h3>PRD 内容</h3>
        <pre class="text-block">{{ detail.prd_content }}</pre>
      </div>

      <div class="detail-section">
        <h3>分析结果</h3>
        <template v-if="detailParsed">
          <div class="summary-grid" v-if="detailParsed.summary">
            <div class="summary-item">
              <div class="label">测试点总数</div>
              <div class="value">{{ detailParsed.summary.total_test_points }}</div>
            </div>
            <div class="summary-item">
              <div class="label">场景总数</div>
              <div class="value">{{ detailParsed.summary.total_test_scenarios }}</div>
            </div>
            <div class="summary-item">
              <div class="label">高优先级</div>
              <div class="value">{{ detailParsed.summary.high_priority_points }}</div>
            </div>
            <div class="summary-item">
              <div class="label">中优先级</div>
              <div class="value">{{ detailParsed.summary.medium_priority_points }}</div>
            </div>
            <div class="summary-item">
              <div class="label">低优先级</div>
              <div class="value">{{ detailParsed.summary.low_priority_points }}</div>
            </div>
          </div>

          <div class="points" v-if="detailParsed.test_points">
            <details v-for="tp in detailParsed.test_points" :key="tp.id" class="tp-item">
              <summary>
                <span class="tp-title">{{ tp.title }}</span>
                <span class="badge">{{ tp.id }}</span>
                <span class="badge" :class="priorityClass(tp.priority)">{{ tp.priority }}</span>
                <span class="muted">场景 {{ (tp.scenarios || []).length }}</span>
              </summary>
              <div class="tp-body">
                <div class="tp-desc">{{ tp.description }}</div>
                <div class="scenarios">
                  <div v-for="sc in tp.scenarios" :key="sc.id" class="scenario">
                    <div class="scenario-header">
                      <span class="scenario-title">{{ sc.title }}</span>
                      <span class="badge">{{ sc.id }}</span>
                      <span class="tag">{{ sc.test_type }}</span>
                    </div>
                    <pre class="text-block">{{ sc.description }}</pre>
                  </div>
                </div>
              </div>
            </details>
          </div>
        </template>
        <template v-else>
          <pre class="text-block">{{ detailRaw }}</pre>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { api } from '../api/endpoints';

const file = ref(null);
const loading = ref(false);
const message = ref('');
const error = ref('');
const result = ref('');
const prdContent = ref('');
const history = ref([]);
const loadingHistory = ref(false);
const historyError = ref('');
const detail = ref(null);
function parseResult(value) {
  if (!value) return null;
  if (typeof value === 'object') return value;
  try {
    return JSON.parse(value);
  } catch (e) {
    return null;
  }
}

function toRaw(value) {
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch (e) {
    return String(value);
  }
}

const parsedResult = computed(() => parseResult(result.value));
const rawResult = computed(() => toRaw(result.value));
const detailParsed = computed(() => parseResult(detail.value?.analysis_result));
const detailRaw = computed(() => toRaw(detail.value?.analysis_result));

function priorityClass(priority) {
  if (priority === '高') return 'priority-high';
  if (priority === '中') return 'priority-medium';
  if (priority === '低') return 'priority-low';
  return '';
}

function formatTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

async function loadHistory() {
  loadingHistory.value = true;
  historyError.value = '';
  try {
    const data = await api.listPrdAnalyses();
    history.value = data.items || [];
  } catch (e) {
    historyError.value = e.message || '获取历史记录失败。';
  } finally {
    loadingHistory.value = false;
  }
}

async function openDetail(id) {
  if (detail.value && detail.value.id === id) {
    detail.value = null;
    return;
  }
  try {
    const data = await api.getPrdAnalysisDetail(id);
    if (data.success) {
      detail.value = data.item;
    }
  } catch (e) {
    historyError.value = e.message || '获取详情失败。';
  }
}

async function deleteHistory(id) {
  if (!window.confirm('确认删除该 PRD 分析记录吗？')) return;
  try {
    const data = await api.deletePrdAnalysis(id);
    if (data.success) {
      if (detail.value && detail.value.id === id) {
        detail.value = null;
      }
      await loadHistory();
      message.value = data.message || '删除成功。';
    } else {
      historyError.value = data.message || '删除失败。';
    }
  } catch (e) {
    historyError.value = e.message || '删除失败。';
  }
}

function onFile(e) {
  file.value = e.target.files[0] || null;
}

async function analyse() {
  if (!file.value) return;
  loading.value = true;
  message.value = '';
  error.value = '';
  result.value = '';
  prdContent.value = '';
  try {
    const form = new FormData();
    form.append('single_file', file.value);
    const data = await api.analysePrd(form);
    if (data.success) {
      result.value = data.result || '';
      prdContent.value = data.prd_content || '';
      await loadHistory();
      if (data.prd_id) {
        await openDetail(data.prd_id);
      }
    } else {
      error.value = data.error || '分析失败。';
    }
  } catch (e) {
    error.value = e.message || '分析失败。';
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadHistory();
});
</script>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-item {
  background: #fff7f2;
  border: 1px solid #ffe4d1;
  border-radius: 12px;
  padding: 10px 12px;
}

.summary-item .label {
  color: #7a5b46;
  font-size: 12px;
  margin-bottom: 6px;
}

.summary-item .value {
  font-size: 20px;
  font-weight: 700;
  color: #3b2a20;
}

.points {
  display: grid;
  gap: 12px;
}

.tp-item {
  border: 1px solid #f2e3d7;
  border-radius: 12px;
  padding: 10px 12px;
  background: #fff;
}

.tp-item > summary {
  cursor: pointer;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  list-style: none;
  font-weight: 600;
}

.tp-item > summary::-webkit-details-marker {
  display: none;
}

.tp-title {
  font-size: 16px;
  color: #2e1f18;
}

.tp-body {
  margin-top: 8px;
}

.tp-desc {
  color: #6b5749;
  margin-bottom: 10px;
}

.scenarios {
  display: grid;
  gap: 10px;
}

.scenario {
  border: 1px solid #f3ebe5;
  border-radius: 10px;
  padding: 10px;
  background: #fffaf7;
}

.scenario-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.scenario-title {
  font-weight: 600;
  color: #2e1f18;
}

.badge {
  font-size: 12px;
  background: #f1f3f5;
  border-radius: 999px;
  padding: 2px 8px;
  color: #4d4d4d;
}

.tag {
  font-size: 12px;
  background: #ffe9d6;
  color: #9a4d00;
  border-radius: 999px;
  padding: 2px 8px;
}

.priority-high {
  background: #ffe3e3;
  color: #c92a2a;
}

.priority-medium {
  background: #fff3bf;
  color: #b08900;
}

.priority-low {
  background: #d3f9d8;
  color: #2b8a3e;
}

.muted {
  color: #8a7a6d;
  font-size: 12px;
}

.text-block {
  background: #f6f7f9;
  border-radius: 8px;
  padding: 8px;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.5;
}

.history-list {
  display: grid;
  gap: 10px;
}

.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid #f0e6dc;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fff;
}

.history-main {
  display: grid;
  gap: 4px;
}

.history-title {
  font-weight: 600;
  color: #2e1f18;
}

.detail-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.detail-title {
  font-weight: 700;
  color: #2e1f18;
}

.detail-section {
  margin-top: 12px;
}
</style>
