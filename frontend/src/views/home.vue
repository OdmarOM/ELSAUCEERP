<template>
  <div class="min-h-screen bg-gray-50 flex flex-col items-center py-12 px-6">
    <div class="text-center mb-16">
      <h1 class="text-5xl font-light text-gray-800 mb-4">El Sauce <span class="font-bold text-emerald-500">ERP</span></h1>
      <p class="text-gray-500 text-xl">Selecciona tu perfil de trabajo</p>
    </div>

    <!-- Perfil Báscula -->
    <div class="w-full max-w-6xl mb-12">
      <h2 class="text-2xl font-bold text-gray-700 mb-6 border-b pb-2">Perfil Operativo (Báscula)</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-8">
        <router-link to="/bascula" class="group bg-white p-10 rounded-3xl shadow-sm border border-gray-100 hover:shadow-xl hover:border-emerald-200 transition-all cursor-pointer text-center flex flex-col items-center">
          <div class="w-24 h-24 bg-emerald-50 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
            <span class="text-5xl">⚖️</span>
          </div>
          <h2 class="text-3xl font-bold text-gray-800 mb-2">Báscula</h2>
          <p class="text-gray-500 text-lg">Entradas, Cuarto Frío y Salidas Físicas</p>
        </router-link>
      </div>
    </div>

    <!-- Perfil Oficina -->
    <div class="w-full max-w-6xl">
      <h2 class="text-2xl font-bold text-gray-700 mb-6 border-b pb-2">Perfil Administrativo (Oficina)</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        <router-link to="/admin" class="group bg-sauce-dark p-10 rounded-3xl shadow-sm hover:shadow-xl hover:shadow-emerald-900/20 transition-all cursor-pointer text-center flex flex-col items-center">
          <div class="w-24 h-24 bg-gray-800 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
            <span class="text-5xl">📊</span>
          </div>
          <h2 class="text-3xl font-bold text-white mb-2">Oficina</h2>
          <p class="text-gray-400 text-lg">Administración, Notas, Planeación y Conciliación</p>
        </router-link>

        <router-link to="/cuentas-cobrar" class="group bg-white p-10 rounded-3xl shadow-sm border border-gray-100 hover:shadow-xl hover:border-blue-200 transition-all cursor-pointer text-center flex flex-col items-center">
          <div class="w-24 h-24 bg-blue-50 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
            <span class="text-5xl">💰</span>
          </div>
          <h2 class="text-3xl font-bold text-gray-800 mb-2">Cobros</h2>
          <p class="text-gray-500 text-lg">Cuentas por Cobrar a Clientes</p>
        </router-link>

        <router-link to="/cuentas-pagar" class="group bg-white p-10 rounded-3xl shadow-sm border border-gray-100 hover:shadow-xl hover:border-red-200 transition-all cursor-pointer text-center flex flex-col items-center">
          <div class="w-24 h-24 bg-red-50 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
            <span class="text-5xl">🧾</span>
          </div>
          <h2 class="text-3xl font-bold text-gray-800 mb-2">Pagos</h2>
          <p class="text-gray-500 text-lg">Cuentas por Pagar (Acopiadores)</p>
        </router-link>

        <router-link to="/dashboard" class="group bg-white p-10 rounded-3xl shadow-sm border border-gray-100 hover:shadow-xl hover:border-blue-200 transition-all cursor-pointer text-center flex flex-col items-center lg:col-span-3">
          <div class="w-24 h-24 bg-blue-50 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
            <span class="text-5xl">📈</span>
          </div>
          <h2 class="text-3xl font-bold text-gray-800 mb-2">Dashboard</h2>
          <p class="text-gray-500 text-lg">Métricas y Reportes Generales</p>
        </router-link>
      </div>
    </div>
  </div>
</template>