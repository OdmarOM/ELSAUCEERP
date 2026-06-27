<!-- LoadingSpinner.vue - Componente de carga reutilizable -->
<template>
  <div class="flex flex-col items-center justify-center" :class="sizeClass">
    <div 
      class="rounded-full border-4 border-emerald-500 border-t-transparent animate-spin"
      :class="spinnerClass"
    ></div>
    <span v-if="text" class="mt-3 text-gray-700 font-medium" :class="textClass">{{ text }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg', 'xl'].includes(value)
  },
  text: {
    type: String,
    default: ''
  },
  color: {
    type: String,
    default: 'emerald',
    validator: (value) => ['emerald', 'blue', 'orange', 'red', 'purple'].includes(value)
  }
})

const sizeClass = computed(() => {
  const sizes = {
    sm: 'scale-75',
    md: 'scale-100',
    lg: 'scale-125',
    xl: 'scale-150'
  }
  return sizes[props.size]
})

const spinnerClass = computed(() => {
  const sizes = {
    sm: 'w-6 h-6',
    md: 'w-10 h-10',
    lg: 'w-14 h-14',
    xl: 'w-20 h-20'
  }
  const colors = {
    emerald: 'border-emerald-500',
    blue: 'border-blue-500',
    orange: 'border-orange-500',
    red: 'border-red-500',
    purple: 'border-purple-500'
  }
  return `${sizes[props.size]} ${colors[props.color]}`
})

const textClass = computed(() => {
  const sizes = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
    xl: 'text-lg'
  }
  return sizes[props.size]
})
</script>
