<template>
  <div>
    <div class="card">
      <h2>用例详情</h2>
      <div v-if="loading" class="notice">加载中...</div>
      <div v-if="error" class="notice error">{{ error }}</div>
      <div v-if="testCase" class="form-grid">
        <div>
          <label>编号</label>
          <input :value="testCase.id" disabled />
        </div>
        <div>
          <label>状态</label>
          <select v-model="testCase.status">
            <option value="pending">待评审</option>
            <option value="approved">已通过</option>
            <option value="rejected">未通过</option>
          </select>
        </div>
      </div>
      <div v-if="testCase" style="margin-top: 12px;">
        <label>描述</label>
        <textarea v-model="testCase.description"></textarea>
      </div>
      <div v-if="testCase" class="form-grid" style="margin-top: 12px;">
        <div>
          <label>测试步骤</label>
          <textarea v-model="testCase.test_steps"></textarea>
        </div>
        <div>
          <label>预期结果</label>
          <textarea v-model="testCase.expected_results"></textarea>
        </div>
      </div>
      <div class="flex" style="margin-top: 12px;" v-if="testCase">
        <button @click="save" :disabled="saving">保存</button>
        <button class="secondary" @click="runReview" :disabled="reviewing">AI 评审</button>
        <span v-if="message" class="notice">{{ message }}</span>
      </div>
    </div>

    <div class="card" v-if="reviewResult">
      <h2>AI 评审结果</h2>
      <div v-if="parsedReview" class="form-grid" style="margin-bottom: 12px;">
        <div>
          <label>评分</label>
          <div class="badge">{{ parsedReview.score ?? '-' }}</div>
        </div>
        <div>
          <label>结论</label>
          <div class="badge" :class="parsedReview.recommendation === '通过' ? 'status-approved' : 'status-rejected'">
            {{ parsedReview.recommendation || '未知' }}
          </div>
        </div>
      </div>

      <div v-if="parsedReview" class="form-grid">
        <div>
          <label>优点</label>
          <ul>
            <li v-for="(item, idx) in parsedReview.strengths || []" :key="`s-${idx}`">{{ item }}</li>
          </ul>
        </div>
        <div>
          <label>不足</label>
          <ul>
            <li v-for="(item, idx) in parsedReview.weaknesses || []" :key="`w-${idx}`">{{ item }}</li>
          </ul>
        </div>
      </div>

      <div v-if="parsedReview" class="form-grid" style="margin-top: 12px;">
        <div>
          <label>改进建议</label>
          <ul>
            <li v-for="(item, idx) in parsedReview.suggestions || []" :key="`g-${idx}`">{{ item }}</li>
          </ul>
        </div>
        <div>
          <label>缺失场景</label>
          <ul>
            <li v-for="(item, idx) in parsedReview.missing_scenarios || []" :key="`m-${idx}`">{{ item }}</li>
          </ul>
        </div>
      </div>

      <div v-if="parsedReview" style="margin-top: 12px;">
        <label>评审意见</label>
        <div class="notice">{{ parsedReview.comments || '-' }}</div>
      </div>

      <div v-if="!parsedReview">
        <pre>{{ reviewResult }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { api } from '../api/endpoints';

const props = defineProps({
  id: { type: String, required: true }
});

const loading = ref(false);
const saving = ref(false);
const reviewing = ref(false);
const error = ref('');
const message = ref('');
const testCase = ref(null);
const reviewResult = ref('');
const parsedReview = computed(() => {
  if (!reviewResult.value) return null;
  if (typeof reviewResult.value === 'object') return reviewResult.value;
  try {
    return JSON.parse(reviewResult.value);
  } catch (e) {
    return null;
  }
});

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const data = await api.getTestCase(props.id);
    testCase.value = { ...data };
    if (data.ai_review && data.ai_review.raw_result) {
      reviewResult.value = data.ai_review.raw_result;
    }
  } catch (e) {
    error.value = e.message || '加载失败。';
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!testCase.value) return;
  saving.value = true;
  message.value = '';
  try {
    const payload = {
      test_case_id: testCase.value.id,
      status: testCase.value.status,
      description: testCase.value.description,
      test_steps: testCase.value.test_steps,
      expected_results: testCase.value.expected_results
    };
    const data = await api.updateTestCase(payload);
    message.value = data.success ? '保存成功。' : (data.message || '保存失败。');
  } catch (e) {
    message.value = e.message || '保存失败。';
  } finally {
    saving.value = false;
  }
}

async function runReview() {
  if (!testCase.value) return;
  reviewing.value = true;
  try {
    const data = await api.reviewTestCase({ test_case_id: testCase.value.id });
    reviewResult.value = data.review_result || '';
  } catch (e) {
    reviewResult.value = e.message || '评审失败。';
  } finally {
    reviewing.value = false;
  }
}

onMounted(load);
</script>
