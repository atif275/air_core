#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm;

#define NUM_SERVOS 4 // Total number of servos used
#define SERVO_DELAY 500 // Delay in milliseconds for both eyes

// Left Eye Settings
#define LEFT_EYE_0_MIN 330
#define LEFT_EYE_0_MAX 400
#define LEFT_EYE_1_MIN 380
#define LEFT_EYE_1_MAX 320
#define LEFT_STEPS 90 // Steps for left eye

// Right Eye Settings
#define RIGHT_EYE_0_MIN 420
#define RIGHT_EYE_0_MAX 350
#define RIGHT_EYE_1_MIN 280
#define RIGHT_EYE_1_MAX 350
#define RIGHT_STEPS 100 // Steps for right eye

int servoPins[NUM_SERVOS] = {0, 1, 2, 3}; // Assigning pins to servos

void setup() {
  Serial.begin(9600);
  Serial.println("Dual Eye Servo Test");
  pwm.begin();
  pwm.setPWMFreq(50);
  
  // Set initial positions
  pwm.setPWM(servoPins[0], 0, LEFT_EYE_0_MIN);
  pwm.setPWM(servoPins[1], 0, LEFT_EYE_1_MIN);
  pwm.setPWM(servoPins[2], 0, RIGHT_EYE_0_MIN);
  pwm.setPWM(servoPins[3], 0, RIGHT_EYE_1_MIN);
  delay(5000);
  // pwm.setPWM(servoPins[0], 0, LEFT_EYE_0_MAX);
  // pwm.setPWM(servoPins[1], 0, LEFT_EYE_1_MAX);
  // pwm.setPWM(servoPins[2], 0, RIGHT_EYE_0_MAX);
  // pwm.setPWM(servoPins[3], 0, RIGHT_EYE_1_MAX);
  
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
  // Left Eye Movement
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
  
  delay(3000); // Delay between cycles
}
