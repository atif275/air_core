#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm;

#define NUM_SERVOS 2 // Adjusted to control 2 servos
#define SERVO_0_MIN 420
#define SERVO_0_MAX 350
#define SERVO_1_MIN 290
#define SERVO_1_MAX 350
#define SERVO_DELAY 500 // Delay in milliseconds

int servoPins[NUM_SERVOS] = {0, 1, 2, 3};

void setup() {
  Serial.begin(9600);
  Serial.println("Alternate Servo Test");
  pwm.begin();
  pwm.setPWMFreq(50);
  pwm.setPWM(servoPins[0], 0, SERVO_0_MIN);
  pwm.setPWM(servoPins[1], 0, SERVO_1_MIN);
  pwm.setPWM(servoPins[2], 0, SERVO_0_MIN);
  pwm.setPWM(servoPins[3], 0, SERVO_1_MIN);
}

void moveServosSmoothly(int start0, int end0, int start1, int end1, int duration) {
  int steps = 100; // Number of steps for the smooth transition
  int stepDelay = duration / steps; 
  int stepSize0 = (end0 - start0) / steps;
  int stepSize1 = (end1 - start1) / steps;

  for (int i = 0; i <= steps; i++) {
    int newPos0 = start0 + (i * stepSize0);
    int newPos1 = start1 + (i * stepSize1);
    pwm.setPWM(servoPins[0], 0, newPos0);
    pwm.setPWM(servoPins[1], 0, newPos1);
    pwm.setPWM(servoPins[2], 0, newPos0);
    pwm.setPWM(servoPins[3], 0, newPos1);
    //delay(stepDelay/4);
  }
}

void loop() {
  // Move servos 0 and 1 smoothly from MIN to MAX and back to MIN
  delay(3000);
  moveServosSmoothly(SERVO_0_MIN, SERVO_0_MAX, SERVO_1_MIN, SERVO_1_MAX, SERVO_DELAY);
  moveServosSmoothly(SERVO_0_MAX, SERVO_0_MIN, SERVO_1_MAX, SERVO_1_MIN, SERVO_DELAY);

  // You can add more servos and their movements here
}
