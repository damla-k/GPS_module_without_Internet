#include <TinyGPS++.h>
#include <HardwareSerial.h>

// GPS Module
HardwareSerial SerialGPS(1); // Use UART 1 for GPS
TinyGPSPlus gps;

void setup() {
  // Start Serial Monitor
  Serial.begin(115200);

  // Start GPS Serial
  SerialGPS.begin(9600, SERIAL_8N1, 16, 17); // RX=16, TX=17
}

void loop() {
  // Process GPS data
  while (SerialGPS.available() > 0) {
    char c = SerialGPS.read();
    Serial.write(c);  // Print raw GPS data to Serial Monitor
    gps.encode(c);
  }

  if (gps.location.isValid()) {
    // Prepare GPS data as JSON
    String gpsJson = "{\"latitude\":" + String(gps.location.lat(), 6) +
                     ",\"longitude\":" + String(gps.location.lng(), 6) +
                     ",\"altitude\":" + String(gps.altitude.meters()) +
                     ",\"speed\":" + String(gps.speed.kmph()) +
                     ",\"satellites\":" + String(gps.satellites.value()) + "}";

    // Send GPS data over Serial
    Serial.println(gpsJson);
  }

  delay(1000); // Send data every second
}
