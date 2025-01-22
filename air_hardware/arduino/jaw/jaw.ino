#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define SERVO_PIN 4  // The PWM pin the servo is attached to
#define PWM_FREQ 50 // Frequency in Hz suitable for servo control

// Define variables for servo control
uint16_t PULSE_START = 800; // Start pulse length (e.g., slow speed in one direction)
uint16_t PULSE_END = 1050;   // End pulse length (e.g., slow speed in the opposite direction)
uint16_t PULSE_STOP = 1500;  // Neutral pulse length for stopping the servo

// Converts pulse length in microseconds to 12-bit PWM value
uint16_t pulseLengthToPWM(uint16_t microseconds) {
    return map(microseconds, 0, 20000, 0, 4096);
}

void setup() {
  Serial.begin(9600);
  pwm.begin();
  pwm.setPWMFreq(PWM_FREQ);
  pwm.setPWM(SERVO_PIN, 0, pulseLengthToPWM(PULSE_START));
  Serial.println("Setup complete.");
}

void loop() {
   if (Serial.available() > 0) {
    char command = Serial.read(); // Read the incoming command
    Serial.print("Received command: "); Serial.println(command); // Debug print

    if (command == 's') { // Start movement
      Serial.println("Starting jaw movement...");
      while (true) {
        // Check for stop command continuously within the loop
        if (Serial.available() > 0) {
          char innerCommand = Serial.read();
          Serial.print("Received inner command: "); Serial.println(innerCommand); // Debug print
          if (innerCommand == 'e') {
            Serial.println("Stopping jaw movement...");
            break; // Exit inner loop
          }
        }
        
        pwm.setPWM(SERVO_PIN, 0, pulseLengthToPWM(PULSE_END));
        delay(250);
        pwm.setPWM(SERVO_PIN, 0, pulseLengthToPWM(PULSE_START));
        delay(250);
      }
      pwm.setPWM(SERVO_PIN, 0, pulseLengthToPWM(PULSE_START)); // Return to initial position
      Serial.println("Jaw movement stopped.");
    }
  }
}
