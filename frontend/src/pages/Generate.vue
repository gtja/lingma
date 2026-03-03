<template>
  <div>
    <div class="card">
      <h2>用例生成</h2>
      <div class="form-grid">
        <div>
          <label>模型选择</label>
          <select v-model="form.llm_provider">
            <option v-for="p in providers" :key="p.key" :value="p.key">
              {{ p.name }}
            </option>
          </select>
        </div>
      </div>

      <div style="margin-top: 12px;">
        <label>需求描述</label>
        <textarea v-model="form.requirements" placeholder="请输入需求描述"></textarea>
      </div>

      <div class="flex" style="margin-top: 12px;">
        <button @click="generate" :disabled="loading">开始生成</button>
        <button class="secondary" @click="reset" :disabled="loading">重置</button>
      </div>

      <div v-if="loading" class="notice">生成中...</div>
      <div v-if="error" class="notice error">{{ error }}</div>
    </div>

    <div class="card" v-if="testCases.length">
      <h2>生成结果</h2>
      <table class="table">
        <thead>
          <tr>
            <th>#</th>
            <th>描述</th>
            <th>步骤</th>
            <th>预期</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(tc, idx) in testCases" :key="idx">
            <td>{{ idx + 1 }}</td>
            <td>{{ tc.description }}</td>
            <td>
              <div v-for="(s, sidx) in tc.test_steps" :key="sidx">{{ s }}</div>
            </td>
            <td>
              <div v-for="(r, ridx) in tc.expected_results" :key="ridx">{{ r }}</div>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="flex" style="margin-top: 12px;">
        <button @click="save" :disabled="saving">保存到数据库</button>
        <span v-if="saveMessage" class="notice">{{ saveMessage }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';
import { api } from '../api/endpoints';

const providers = ref([]);
const loading = ref(false);
const saving = ref(false);
const error = ref('');
const saveMessage = ref('');
const testCases = ref([]);

const form = reactive({
  llm_provider: 'deepseek',
  requirements: '',
  case_design_methods: [],
  case_categories: [],
  case_count: 100
});

const designMethods = [
  { value: 'equivalence_partitioning', label: '等价类划分' },
  { value: 'boundary_value', label: '边界值分析' },
  { value: 'decision_table', label: '判定表' },
  { value: 'cause_effect', label: '因果图' },
  { value: 'orthogonal_array', label: '正交分析' },
  { value: 'scenario', label: '场景法' }
];

const caseCategories = [
  { value: 'functional', label: '功能测试' },
  { value: 'performance', label: '性能测试' },
  { value: 'compatibility', label: '兼容性测试' },
  { value: 'security', label: '安全测试' }
];

const mapLabels = (values, options) => {
  const map = new Map(options.map((o) => [o.value, o.label]));
  return values.map((v) => map.get(v) || v);
};

onMounted(async () => {
  try {
    const data = await api.getProviders();
    providers.value = data.providers || [];
    const hasQwen = providers.value.some((p) => p.key === 'qwen');
    if (hasQwen) {
      form.llm_provider = 'qwen';
    } else if (data.default_provider) {
      form.llm_provider = data.default_provider;
    }
  } catch (e) {
    error.value = e.message || '加载模型失败。';
  }
});

async function generate() {
  error.value = '';
  saveMessage.value = '';
  if (!form.requirements.trim()) {
    error.value = '需求描述不能为空。';
    return;
  }
  loading.value = true;
  try {
    const data = await api.generateCases({
      requirements: form.requirements,
      llm_provider: form.llm_provider,
      case_design_methods: mapLabels(designMethods.map((m) => m.value), designMethods),
      case_categories: mapLabels(caseCategories.map((c) => c.value), caseCategories),
      case_count: form.case_count
    });
    testCases.value = data.test_cases || [];
  } catch (e) {
    error.value = e.message || '生成失败。';
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!testCases.value.length) return;
  saving.value = true;
  saveMessage.value = '';
  try {
    const data = await api.saveCases({
      requirement: form.requirements,
      test_cases: testCases.value,
      llm_provider: form.llm_provider
    });
    saveMessage.value = data.message || '保存成功。';
  } catch (e) {
    saveMessage.value = e.message || '保存失败。';
  } finally {
    saving.value = false;
  }
}

function reset() {
  form.requirements = '';
  form.case_design_methods = [];
  form.case_categories = [];
  form.case_count = 100;
  testCases.value = [];
  error.value = '';
  saveMessage.value = '';
}
</script>
