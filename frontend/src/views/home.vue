<template>
  <div class="h-screen bg-gray-50 flex flex-col items-center justify-center p-6">
    <div class="text-center mb-12">
      <h1 class="text-5xl font-light text-gray-800 mb-4">El Sauce <span class="font-bold text-emerald-500">ERP</span></h1>
      <p class="text-gray-500 text-xl">Selecciona tu módulo de trabajo</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-8 w-full max-w-4xl">
      <router-link to="/bascula" class="group bg-white p-10 rounded-3xl shadow-sm border border-gray-100 hover:shadow-xl hover:border-emerald-200 transition-all cursor-pointer text-center flex flex-col items-center">
        <div class="w-24 h-24 bg-emerald-50 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
          <span class="text-5xl">⚖️</span>
        </div>
        <h2 class="text-3xl font-bold text-gray-800 mb-2">Zona A</h2>
        <p class="text-gray-500 text-lg">Báscula, Recepción y Registro de Tarimas</p>
      </router-link>

      <router-link to="/admin" class="group bg-sauce-dark p-10 rounded-3xl shadow-sm hover:shadow-xl hover:shadow-emerald-900/20 transition-all cursor-pointer text-center flex flex-col items-center">
        <div class="w-24 h-24 bg-gray-800 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
          <span class="text-5xl">📊</span>
        </div>
        <h2 class="text-3xl font-bold text-white mb-2">Zona B</h2>
        <p class="text-gray-400 text-lg">Administración, Notas, Conciliación y Pagos</p>
      </router-link>
    </div>
  </div>
</template>