<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <h1>AiCase</h1>
        <button class="theme-toggle" @click="cycleTheme">主题：{{ themeLabel }}</button>
      </div>
      <nav class="nav">
        <RouterLink to="/">看板</RouterLink>
        <RouterLink to="/generate">用例生成</RouterLink>
        <RouterLink to="/plane-generate">Plane 一键生成</RouterLink>
        <RouterLink to="/review">用例评审</RouterLink>
        <RouterLink to="/upload">知识库上传</RouterLink>
        <RouterLink to="/analyser">PRD 分析</RouterLink>
        <RouterLink to="/api-case-generate">接口用例生成</RouterLink>
        <RouterLink to="/knowledge">知识库管理</RouterLink>
      </nav>
    </aside>
    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { RouterLink, RouterView } from 'vue-router';

const themes = ['default', 'ocean', 'sunset'];
const themeNameMap = {
  default: '默认',
  ocean: '海洋',
  sunset: '暖阳'
};
const themeLabel = ref(themeNameMap.default);

function applyTheme(value) {
  if (value === 'default') {
    document.documentElement.removeAttribute('data-theme');
  } else {
    document.documentElement.setAttribute('data-theme', value);
  }
  themeLabel.value = themeNameMap[value] || value;
  localStorage.setItem('theme', value);
}

function cycleTheme() {
  const current = localStorage.getItem('theme') || 'default';
  const idx = themes.indexOf(current);
  const next = themes[(idx + 1) % themes.length];
  applyTheme(next);
}

onMounted(() => {
  const saved = localStorage.getItem('theme') || 'default';
  applyTheme(saved);
});
</script>
