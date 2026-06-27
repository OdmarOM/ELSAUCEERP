<!-- Card.vue - Componente de tarjeta reutilizable -->
<template>
  <div 
    class="rounded-3xl shadow-sm border transition-all duration-200"
    :class="[variantClass, paddingClass, hoverClass]"
  >
    <div v-if="$slots.header" class="border-b pb-4 mb-4">
      <slot name="header"></slot>
    </div>
    
    <div :class="contentClass">
      <slot></slot>
    </div>
    
    <div v-if="$slots.footer" class="border-t pt-4 mt-4">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'white', 'gray', 'blue', 'emerald', 'orange', 'red'].includes(value)
  },
  padding: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg', 'xl'].includes(value)
  },
  hoverable: {
    type: Boolean,
    default: false
  }
})

const variantClass = computed(() => {
  const variants = {
    default: 'bg-white border-gray-200',
    white: 'bg-white border-gray-200',
    gray: 'bg-gray-50 border-gray-200',
    blue: 'bg-blue-50 border-blue-200',
    emerald: 'bg-emerald-50 border-emerald-200',
    orange: 'bg-orange-50 border-orange-200',
    red: 'bg-red-50 border-red-200'
  }
  return variants[props.variant]
})

const paddingClass = computed(() => {
  const paddings = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
    xl: 'p-10'
  }
  return paddings[props.padding]
})

const contentClass = computed(() => {
  return props.padding === 'sm' ? '' : 'space-y-4'
})

const hoverClass = computed(() => {
  return props.hoverable ? 'hover:shadow-md hover:border-gray-300 cursor-pointer' : ''
})
</script>
