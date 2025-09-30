import { createRouter, createWebHistory } from '@ionic/vue-router'
import Home from '@/components/Home.vue'
import Insights from '@/components/Insights.vue'

const routes = [
  { path: '/', redirect: '/home' },
  { path: '/home', component: Home },
  { path: '/insights', component: Insights },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router
