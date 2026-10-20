// Standalone RG1602A diagnostic -- nothing else on the node runs in this build (no RFID,
// LoRa, fingerprint, acoustic). Flash with `pio run -e lcd-diagnostic -t upload`, then
// `pio device monitor -e lcd-diagnostic`.
//
// Purpose: isolate "is this the Lcd1602 driver" from "is this wiring/power/contrast" --
// the two halves below are independent of each other.
#include <Arduino.h>
#include "Lcd1602.h"

#ifndef FOREST_LCD_RS_PIN
#define FOREST_LCD_RS_PIN 2
#endif
#ifndef FOREST_LCD_EN_PIN
#define FOREST_LCD_EN_PIN 15
#endif
#ifndef FOREST_LCD_D4_PIN
#define FOREST_LCD_D4_PIN 41
#endif
#ifndef FOREST_LCD_D5_PIN
#define FOREST_LCD_D5_PIN 42
#endif
#ifndef FOREST_LCD_D6_PIN
#define FOREST_LCD_D6_PIN 47
#endif
#ifndef FOREST_LCD_D7_PIN
#define FOREST_LCD_D7_PIN 21
#endif

ForestSensors::Lcd1602 lcd;

static void printChecklist() {
  Serial.println();
  Serial.println("==================================================");
  Serial.println("  RG1602A LCD DIAGNOSTIC");
  Serial.println("==================================================");
  Serial.printf("Pins: RS=%d EN=%d D4=%d D5=%d D6=%d D7=%d\n", FOREST_LCD_RS_PIN, FOREST_LCD_EN_PIN,
                FOREST_LCD_D4_PIN, FOREST_LCD_D5_PIN, FOREST_LCD_D6_PIN, FOREST_LCD_D7_PIN);
  Serial.println("Before assuming the code is wrong, verify on the LCD module itself:");
  Serial.println("  1. VSS -> GND, VDD -> 5V (or 3.3V -- dimmer but usually works)");
  Serial.println("  2. VO (contrast) -> wiper of a ~10k pot between VDD and GND.");
  Serial.println("     This is the #1 cause of \"nothing visible\": with VO left");
  Serial.println("     floating or at the wrong end of the pot, the screen shows");
  Serial.println("     either nothing or solid black blocks on every cell. Turn the");
  Serial.println("     pot through its FULL range while a pattern is being written --");
  Serial.println("     do not assume one fixed setting.");
  Serial.println("  3. RW -> GND (this driver never reads, so RW must be grounded,");
  Serial.println("     not left floating and not wired to a GPIO).");
  Serial.println("  4. A/K (backlight) -> VDD/GND (through the module's own resistor");
  Serial.println("     if it has one) if you want the backlight on at all.");
  Serial.println("  5. D4-D7/RS/EN each actually land on the GPIO numbers above, not");
  Serial.println("     swapped or off-by-one on the header.");
  Serial.println("==================================================");
  Serial.println("Serial commands: p = raw pin wiggle (bypasses the driver class),");
  Serial.println("                 d = driver test pattern again");
  Serial.println("==================================================\n");
}

// Bypasses Lcd1602 entirely: drives the six pins directly so a logic probe/LED can
// confirm each one is actually toggling, independent of whether the HD44780 protocol
// in Lcd1602.cpp is right. If these pins don't move, the problem is wiring/pin
// numbers/board damage, not the driver.
static void rawPinWiggle() {
  const int pins[6] = {FOREST_LCD_RS_PIN, FOREST_LCD_EN_PIN, FOREST_LCD_D4_PIN,
                       FOREST_LCD_D5_PIN, FOREST_LCD_D6_PIN, FOREST_LCD_D7_PIN};
  const char* names[6] = {"RS", "EN", "D4", "D5", "D6", "D7"};
  for (int pin : pins) pinMode(pin, OUTPUT);
  Serial.println("[RAW] Toggling each pin HIGH for 1s, one at a time -- probe with a meter/LED.");
  for (int i = 0; i < 6; ++i) {
    Serial.printf("[RAW] %s (GPIO%d) -> HIGH\n", names[i], pins[i]);
    digitalWrite(pins[i], HIGH);
    delay(1000);
    digitalWrite(pins[i], LOW);
    Serial.printf("[RAW] %s (GPIO%d) -> LOW\n", names[i], pins[i]);
    delay(200);
  }
  Serial.println("[RAW] Done. Re-running lcd.begin() to restore the driver's pin modes.\n");
  lcd.begin(FOREST_LCD_RS_PIN, FOREST_LCD_EN_PIN, FOREST_LCD_D4_PIN, FOREST_LCD_D5_PIN,
           FOREST_LCD_D6_PIN, FOREST_LCD_D7_PIN);
}

static void driverPatternTest() {
  Serial.println("[DRIVER] clear()");
  lcd.clear();
  delay(1000);

  Serial.println("[DRIVER] Full-block fill both rows (visible even with contrast off-center)");
  lcd.setLine(0, "################");
  lcd.setLine(1, "################");
  delay(3000);

  Serial.println("[DRIVER] Per-row addressing check");
  lcd.setLine(0, "LINE0 0123456789");
  lcd.setLine(1, "LINE1 ABCDEFGHIJ");
  delay(3000);

  Serial.println("[DRIVER] Short text, as main.cpp would show it");
  lcd.setLine(0, "Ready");
  lcd.setLine(1, "Tap card");
  delay(3000);
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  printChecklist();
  lcd.begin(FOREST_LCD_RS_PIN, FOREST_LCD_EN_PIN, FOREST_LCD_D4_PIN, FOREST_LCD_D5_PIN,
           FOREST_LCD_D6_PIN, FOREST_LCD_D7_PIN);
  driverPatternTest();
}

void loop() {
  if (Serial.available() > 0) {
    const int c = Serial.read();
    if (c == 'p') rawPinWiggle();
    else if (c == 'd') driverPatternTest();
  }
  // Repeats the pattern test every 10s even with no serial input, so a logic
  // analyzer/scope on EN can be left to free-run and compare against the serial log.
  static uint32_t lastMs = 0;
  if (millis() - lastMs > 10000U) {
    lastMs = millis();
    driverPatternTest();
  }
}
