import { createRouter, createWebHistory } from 'vue-router'
import AssetLibraryView from '@/views/AssetLibraryView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue')
    },
    {
      path: '/tasks/:id',
      name: 'task-detail',
      component: () => import('../views/TaskDetailView.vue'),
      props: true
    },
    {
      path: '/style-presets',
      name: 'style-presets',
      component: () => import('../views/StylePresetView.vue')
    },
    {
      path: '/subtitle-styles',
      name: 'subtitle-styles',
      component: () => import('../views/SubtitleStyleView.vue')
    },
    {
      path: '/subtitle-styles/create',
      name: 'subtitle-style-create',
      component: () => import('../views/SubtitleStyleEditorView.vue')
    },
    {
      path: '/subtitle-styles/:id/edit',
      name: 'subtitle-style-edit',
      component: () => import('../views/SubtitleStyleEditorView.vue'),
      props: true
    },
    {
      path: '/runninghub/workflows',
      name: 'runninghub-workflows',
      component: () => import('../views/RunningHubWorkflowView.vue')
    },
    {
      path: '/assets',
      name: 'assets',
      component: AssetLibraryView
    },
    {
      path: '/service-config',
      name: 'service-config',
      component: () => import('../views/ServiceConfigView.vue')
    },
    {
      path: '/service-config/gemini-keys',
      name: 'gemini-keys',
      component: () => import('../views/GeminiKeysView.vue')
    },
    {
      path: '/gemini-console',
      name: 'gemini-console',
      component: () => import('../views/GeminiConsoleView.vue')
    }
  ]
})

export default router