#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define SERVO_DELAY 500 // Delay in milliseconds for eye movements

// Jaw Settings
#define JAW_SERVO_PIN 4
#define PULSE_START 1250
#define PULSE_END 1400
#define PULSE_STOP 1500

// Eye Settings
#define NUM_SERVOS 6 // Total number of servos used, including the jaw
int servoPins[NUM_SERVOS] = {0, 1, 2, 3, 4, 5}; // Assigning pins to servos, adjust as needed

// Left Eye Settings
#define LEFT_EYE_0_MIN 330
#define LEFT_EYE_0_MAX 400
#define LEFT_EYE_1_MIN 380
#define LEFT_EYE_1_MAX 320
#define LEFT_STEPS 90 // Steps for left eye movement

// Right Eye Settings
#define RIGHT_EYE_0_MIN 420
#define RIGHT_EYE_0_MAX 350
#define RIGHT_EYE_1_MIN 280
#define RIGHT_EYE_1_MAX 350
#define RIGHT_STEPS 100 // Steps for right eye movement
uint16_t pulseLengthToPWM(uint16_t microseconds) {
    return map(microseconds, 0, 20000, 0, 4096);
}
void setup() {
  Serial.begin(9600);
  pwm.begin();
  pwm.setPWMFreq(50); // Set the frequency for all servos

  // Initialize servos to their starting positions
 pwm.setPWM(4, 0, pulseLengthToPWM(PULSE_END));
  pwm.setPWM(servoPins[0], 0, LEFT_EYE_0_MIN);
  pwm.setPWM(servoPins[1], 0, LEFT_EYE_1_MIN);
  pwm.setPWM(servoPins[2], 0, RIGHT_EYE_0_MIN);
  pwm.setPWM(servoPins[3], 0, RIGHT_EYE_1_MIN);
  delay(5000);
  pwm.setPWM(servoPins[0], 0, LEFT_EYE_0_MAX);
  pwm.setPWM(servoPins[1], 0, LEFT_EYE_1_MAX);
  pwm.setPWM(servoPins[2], 0, RIGHT_EYE_0_MAX);
  pwm.setPWM(servoPins[3], 0, RIGHT_EYE_1_MAX);
}

void moveServosSmoothly(int pin, int start, int end, int steps, int duration) {
  int stepSize = (end - start) / steps;

  for (int i = 0; i <= steps; i++) {
    // if (pin <= 1) {
    //   i += 2; // Increment by 2 for left eye as per original left eye code
    // }
    i+=3;
    int newPos = start + (i * stepSize);
    pwm.setPWM(pin, 0, newPos);
  }
}

void loop() {
  // Eye Movement - executed continuously
  moveServosSmoothly(servoPins[0], LEFT_EYE_0_MIN, LEFT_EYE_0_MAX, LEFT_STEPS, SERVO_DELAY);
  moveServosSmoothly(servoPins[1], LEFT_EYE_1_MIN, LEFT_EYE_1_MAX, LEFT_STEPS, SERVO_DELAY);

  // Right Eye Movement
  moveServosSmoothly(servoPins[2], RIGHT_EYE_0_MIN, RIGHT_EYE_0_MAX, RIGHT_STEPS, SERVO_DELAY);
  moveServosSmoothly(servoPins[3], RIGHT_EYE_1_MIN, RIGHT_EYE_1_MAX, RIGHT_STEPS, SERVO_DELAY);

  // Return to initial positions
  moveServosSmoothly(servoPins[0], LEFT_EYE_0_MAX, LEFT_EYE_0_MIN, LEFT_STEPS, SERVO_DELAY);
  moveServosSmoothly(servoPins[1], LEFT_EYE_1_MAX, LEFT_EYE_1_MIN, LEFT_STEPS, SERVO_DELAY);
  moveServosSmoothly(servoPins[2], RIGHT_EYE_0_MAX, RIGHT_EYE_0_MIN, RIGHT_STEPS, SERVO_DELAY);
  moveServosSmoothly(servoPins[3], RIGHT_EYE_1_MAX, RIGHT_EYE_1_MIN, RIGHT_STEPS, SERVO_DELAY);

  // // Jaw Movement - check for serial command without blocking
  if (Serial.available() > 0) {
    char command = Serial.read();
    switch(command) {
        case 's': // Start jaw movement
          pwm.setPWM(JAW_SERVO_PIN, 0, PULSE_END);
          delay(250);
          pwm.setPWM(JAW_SERVO_PIN, 0, PULSE_START);
          delay(250);
          break;
        case 'e': // Stop jaw movement immediately
          pwm.setPWM(JAW_SERVO_PIN, 0, PULSE_START);
          Serial.println("Jaw movement stopped.");
          break;
    }
  }
  else{
    delay(3000);
  }
}
