#include <WiFi.h>
#include <HTTPClient.h>

// --- CONFIGURACIÓN DE RED ---
const char* ssid = "Star_Telecomm01984";
const char* password = "Kj9E6Nd5";

// ¡IMPORTANTE! Cambia la X por la IP de la computadora donde corre FastAPI
const String API_URL = "http://192.168.101.9:8000/api/bascula/leer";

// --- VARIABLES DE LÓGICA Y SIMULACIÓN ---
float pesoSimulado = 150.0; // Empezamos con una base de 150 kg
unsigned long ultimoEnvio = 0;
const unsigned long INTERVALO_ENVIO = 400; // Enviar cada 400ms para fluidez

void setup() {
  Serial.begin(115200);
  
  // Conectar a Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Conectando a Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) { 
    delay(1000); 
    Serial.print("."); 
  }
  Serial.println("\n✅ Conectado a Wi-Fi local");
}

void loop() {
  // 1. Lógica de Simulación de Peso
  // Creamos una fluctuación aleatoria para que se vea real en la pantalla (-1.5 a +1.5 kg)
  float variacion = random(-15, 16) / 10.0; 
  pesoSimulado += variacion;

  // Evitamos que baje de cero o se vaya a números absurdos
  if (pesoSimulado <= 0) pesoSimulado = 10.0;
  if (pesoSimulado > 3000.0) pesoSimulado = 150.0; // Si sube mucho, la "reseteamos"

  // 2. Temporizador no bloqueante: Manda a FastAPI cada 400ms
  if (millis() - ultimoEnvio >= INTERVALO_ENVIO) {
    ultimoEnvio = millis();
    enviarPesoFastAPI(pesoSimulado);
  }
  
  // Un pequeñísimo delay para no sobrecargar el procesador del ESP32
  delay(10);
}

void enviarPesoFastAPI(float peso) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ Error: Sin Wi-Fi");
    return;
  }

  HTTPClient http;
  
  // Conexión rápida por HTTP normal
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json"); 
  
  // Armamos el JSON {"peso": 150.50}
  String jsonPayload = "{\"peso\":" + String(peso, 2) + "}";
  
  // Disparamos el POST
  int httpCode = http.POST(jsonPayload); 
  
  if (httpCode > 0) {
    // Imprime en la consola para que veas qué está mandando exactamente
    Serial.println("✅ Simulación enviada: " + String(peso, 2) + " kg");
  } else {
    Serial.println("❌ Error enviando a ERP: " + http.errorToString(httpCode));
  }
  
  http.end();
}