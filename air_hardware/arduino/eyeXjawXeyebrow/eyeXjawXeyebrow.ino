#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm;
int temp =0;
#define NUM_SERVOS 4 // Total number of servos used
#define SERVO_DELAY 500 // Delay in milliseconds for both eyes

#define SERVO_PIN 4
#define Right_Eye_brow_PIN 7 
#define Left_Eye_brow_PIN 6 // The PWM pin the servo is attached to
#define PWM_FREQ 50 // Frequency in Hz suitable for servo control
//eye brow
uint16_t PULSE_TOP = 1000; // Start pulse length (e.g., slow speed in one direction)
uint16_t PULSE_BOTTOM = 600;   // End pulse length (e.g., slow speed in the opposite direction)
uint16_t PULSE_STOP = 800;  // Neutral pulse length for stopping the servo

//jaw
uint16_t PULSE_START = 800; // Start pulse length (e.g., slow speed in one direction)
uint16_t PULSE_END = 1050;   // End pulse length (e.g., slow speed in the opposite direction)

// Left Eye Settings
#define LEFT_EYE_0_MIN 330
#define LEFT_EYE_0_MAX 400
#define LEFT_EYE_1_MIN 380
#define LEFT_EYE_1_MAX 320
#define LEFT_STEPS 90 // Steps for left eye
uint16_t pulseLengthToPWM(uint16_t microseconds) {
    return map(microseconds, 0, 20000, 0, 4096);
}

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
  pwm.setPWM(Right_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_STOP));
  pwm.setPWM(Left_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_STOP));
  pwm.setPWM(SERVO_PIN, 0, pulseLengthToPWM(PULSE_START));
  delay(5000);
  Serial.println("Setup complete.");
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
  if(temp==2){
      //up
      pwm.setPWM(Right_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_TOP));
      pwm.setPWM(Left_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_BOTTOM));
      pwm.setPWM(SERVO_PIN, 0, pulseLengthToPWM(PULSE_END));
      Serial.println("up complete.");
  }
  else if(temp==4){
      //stop

      pwm.setPWM(SERVO_PIN, 0, pulseLengthToPWM(PULSE_START));
      pwm.setPWM(Right_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_STOP));
      pwm.setPWM(Left_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_STOP));
      Serial.println("stop complete.");
  }
  else if(temp==6){
      //down
      pwm.setPWM(Right_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_BOTTOM));
      pwm.setPWM(Left_Eye_brow_PIN, 0, pulseLengthToPWM(PULSE_TOP));
      Serial.println("down complete.");
      temp=0;
  }
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
  
  delay(2000); // Delay between cycles
  temp++;
  if (Serial.available() > 0) {
    char command = Serial.read(); // Read the incoming command
    Serial.print("Received command: "); Serial.println(command); // Debug print

    if (command == 's') { // Start movement
      moveServosSmoothly(servoPins[0], LEFT_EYE_0_MAX, LEFT_EYE_0_MIN, LEFT_STEPS, SERVO_DELAY);
      moveServosSmoothly(servoPins[1], LEFT_EYE_1_MAX, LEFT_EYE_1_MIN, LEFT_STEPS, SERVO_DELAY);
      moveServosSmoothly(servoPins[2], RIGHT_EYE_0_MAX, RIGHT_EYE_0_MIN, RIGHT_STEPS, SERVO_DELAY);
      moveServosSmoothly(servoPins[3], RIGHT_EYE_1_MAX, RIGHT_EYE_1_MIN, RIGHT_STEPS, SERVO_DELAY);

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
