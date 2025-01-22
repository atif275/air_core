#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define Right_Eye_brow_PIN 7 

#define Left_Eye_brow_PIN 6 // The PWM pin the servo is attached to

#define PWM_FREQ 50 // Frequency in Hz suitable for servo control

// Define variables for servo control
uint16_t PULSE_TOP = 1000; // Start pulse length (e.g., slow speed in one direction)
uint16_t PULSE_BOTTOM = 600;   // End pulse length (e.g., slow speed in the opposite direction)
uint16_t PULSE_STOP = 800;  // Neutral pulse length for stopping the servo

// Converts pulse length in microseconds to 12-bit PWM value
uint16_t pulseLengthToPWM(uint16_t microseconds) {
    return map(microseconds, 0, 20000, 0, 4096);
}

void setup() {
  Serial.begin(9600);
  pwm.begin();
  pwm.setPWMFreq(PWM_FREQ);
  pwm.setPWM(Right_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_STOP));
  pwm.setPWM(Left_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_STOP));
  delay(2000);
  //up
  // pwm.setPWM(Right_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_TOP));
  // pwm.setPWM(Left_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_BOTTOM));
  // delay(2000);
  // //down
  // pwm.setPWM(Right_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_BOTTOM));
  // pwm.setPWM(Left_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_TOP));
  Serial.println("Setup complete.");
}

void loop() {
   if (Serial.available() > 0) {
    char command = Serial.read(); // Read the incoming command
    Serial.print("Received command: "); Serial.println(command); // Debug print
    if (command == 'u') {
      //up
      pwm.setPWM(Right_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_TOP));
      pwm.setPWM(Left_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_BOTTOM));
      Serial.println("up complete.");
    }
    else if(command == 'd'){
      //down
      pwm.setPWM(Right_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_BOTTOM));
      pwm.setPWM(Left_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_TOP));
      Serial.println("down complete.");

    }
    else if(command =='s'){
      pwm.setPWM(Right_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_STOP));
      pwm.setPWM(Left_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_STOP));
      Serial.println("stop complete.");
    }

  }
}
