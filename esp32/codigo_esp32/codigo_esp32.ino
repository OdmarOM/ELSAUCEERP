#include <WiFi.h>
#include <HTTPClient.h>
#include <HardwareSerial.h>
#include "secrets.h"

// --- CONFIGURACIÓN DE RED ---
// Las credenciales ahora están en secrets.h

// --- CONFIGURACIÓN BÁSCULA RHINO ---
#define RX_PIN 16 
#define TX_PIN 17
HardwareSerial MyScale(2);

// --- VARIABLES DE LÓGICA ---
float pesoActual = 0.0;
unsigned long ultimoEnvio = 0;
const unsigned long INTERVALO_ENVIO = 400; // Enviar cada 400ms para fluidez extrema

void setup() {
  Serial.begin(115200);
  
  // Iniciar lectura de la Rhino
  MyScale.begin(9600, SERIAL_8N1, RX_PIN, TX_PIN);
  MyScale.setTimeout(50);
  
  // Conectar a Wi-Fi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Conectando a Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) { 
    delay(500); 
    Serial.print("."); 
  }
  Serial.println("\n✅ Conectado a Wi-Fi local");
}

void loop() {
  // 1. Leer el buffer serial SIEMPRE a máxima velocidad
  // Esto vacía los datos que manda la Rhino continuamente
  while (MyScale.available()) {
    String trama = MyScale.readStringUntil('\n');
    trama.trim();
    if (trama.length() > 0) {
      pesoActual = trama.toFloat();
    }
  }

  // 2. Temporizador no bloqueante: Manda a FastAPI cada 400ms
  if (millis() - ultimoEnvio >= INTERVALO_ENVIO) {
    ultimoEnvio = millis();
    enviarPesoFastAPI(pesoActual);
  }
}

void enviarPesoFastAPI(float peso) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ Error: Sin Wi-Fi, intentando reconectar...");
    WiFi.reconnect();
    return;
  }

  HTTPClient http;
  
  // Conexión rápida por HTTP normal
  http.begin(String(API_URL));
  http.addHeader("Content-Type", "application/json"); 
  http.setTimeout(5000); // Timeout de 5 segundos
  
  // Armamos el JSON {"peso": 150.50}
  String jsonPayload = "{\"peso\":" + String(peso, 2) + "}";
  
  // Disparamos el POST
  int httpCode = http.POST(jsonPayload); 
  
  if (httpCode > 0) {
    // Si quieres ver en la consola cómo se envía, descomenta la siguiente línea:
    // Serial.println("✅ Enviado: " + String(peso) + " kg");
  } else {
    Serial.println("❌ Error enviando a ERP: " + http.errorToString(httpCode));
  }
  
  http.end();
}