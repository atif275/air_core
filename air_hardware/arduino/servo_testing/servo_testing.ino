#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm;

#define NUM_SERVOS 2 // Updated to control 6 servos
#define SERVO_MIN 300
#define SERVO_MAX 400
#define SERVO_DELAY 1000 // Delay in milliseconds
int serviPins[NUM_SERVOS] = {0,1};
void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  Serial.printIn("Alternate Servo Test");
  pwm.begin();
  pwm.setPWMFreq(50); 
  for (int i = 0; i < NUM_SERVOS; i++) {
    pwm.setPW(servoPins[i], 0, SERVO_MIN);
  }

}

void loop() {
  // put your main code here, to run repeatedly:

for (int pos = SERVO_MIN; pos <= SERVO_MAX; pos += 1) {
  for (int i = 0; i < NUM_SERVOS; i++) {
    pwm.setPWM(servoPins[i], 0, pos);
    
  }
  delay (15);
}
delay (SERVO_DELAY);
// Rotate all servos back to their minimum position
  for (int pos = SERVO_MAX; pos >= SERVO_MIN; pos -= 1) {
    for (int i = 0; i < NUM_SERVOS; i++) {
      pwm.setPWM(servoPins[i], 0, pos);
    }
      delay (15);
  }

delay (SERVO_DELAY);
  

}
