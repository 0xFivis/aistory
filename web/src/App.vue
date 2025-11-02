<template>
  <el-config-provider :locale="zhCn">
    <div class="app-shell">
      <header class="app-header">
        <router-link to="/" class="app-brand">
          <span class="app-brand__title">AI Story 工作流</span>
        </router-link>
        <nav class="app-nav">
          <router-link to="/" class="app-nav__link" active-class="is-active">任务列表</router-link>
          <router-link to="/style-presets" class="app-nav__link" active-class="is-active">风格管理</router-link>
          <router-link to="/runninghub/workflows" class="app-nav__link" active-class="is-active">RH 配置</router-link>
          <router-link to="/assets" class="app-nav__link" active-class="is-active">素材库</router-link>
          <router-link to="/gemini-console" class="app-nav__link" active-class="is-active">Gemini 控制台</router-link>
          <router-link to="/service-config" class="app-nav__link" active-class="is-active">服务配置</router-link>
        </nav>
      </header>
      <main class="app-main">
        <router-view />
      </main>
    </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
</script>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-background-page);
  color: var(--color-neutral-900);
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-6);
  height: var(--layout-header-height);
  background: linear-gradient(135deg, #111827, #1f2937);
  box-shadow: var(--shadow-subtle);
}

.app-brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  text-decoration: none;
}

.app-brand__title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: #ffffff;
  letter-spacing: 0.02em;
}

.app-nav {
  display: flex;
  gap: var(--space-3);
  margin-left: var(--space-6);
}

.app-nav__link {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2) var(--space-3);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: rgba(255, 255, 255, 0.75);
  border-radius: var(--radius-pill);
  transition: background-color 0.18s ease, color 0.18s ease;
}

.app-nav__link:hover {
  color: #ffffff;
  background-color: rgba(255, 255, 255, 0.16);
}

.app-nav__link.is-active {
  color: #ffffff;
  background-color: rgba(255, 255, 255, 0.22);
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

@media (max-width: 960px) {
  .app-header {
    flex-wrap: wrap;
    gap: var(--space-3);
    padding: var(--space-4);
  }

  .app-nav {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
    gap: var(--space-2);
    margin-left: 0;
  }

  .app-nav__link {
    padding: var(--space-1) var(--space-2);
  }
}
</style>