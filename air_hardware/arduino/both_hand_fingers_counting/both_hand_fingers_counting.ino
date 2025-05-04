#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Initialize the PCA9685
Adafruit_PWMServoDriver pca9685 = Adafruit_PWMServoDriver();

// Channels for Right Hand
#define R_PINKY    0
#define R_RING     1
#define R_MIDDLE   2
#define R_INDEX    3
#define R_THUMB    4

// Channels for Left Hand
#define L_PINKY    10
#define L_RING     9
#define L_MIDDLE   8
#define L_INDEX    7
#define L_THUMB    6

// Servo limits
#define SERVOMIN 150
#define SERVOMAX 600

// Open and close angles
#define ANGLE_OPEN   0
#define ANGLE_CLOSED 120

void setup() {
  Serial.begin(9600);
  pca9685.begin();
  pca9685.setPWMFreq(50);

  // Set all to open initially
  setAllFingersRight(ANGLE_OPEN);
  setAllFingersLeft(ANGLE_OPEN);

  Serial.println("Enter 0-10 for RIGHT hand or l0-l10 for LEFT hand:");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input.startsWith("l")) {
      int val = input.substring(1).toInt();
      applyGestureLeft(val);
    } else {
      int val = input.toInt();
      applyGestureRight(val);
    }
  }
}

// ==================== RIGHT HAND GESTURES ====================
void applyGestureRight(int val) {
  switch (val) {
    case 0: 
      setFingersRight(ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED);
      break;

    case 1:
      setFingersRight(ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_OPEN, ANGLE_CLOSED);
      break;
    case 2:
      setFingersRight(ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_OPEN, ANGLE_OPEN, ANGLE_CLOSED);
      break;
    case 3:
      setFingersRight(ANGLE_CLOSED, ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN, ANGLE_CLOSED);
      break;
    case 4:
      setFingersRight(ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN, ANGLE_CLOSED);
      break;
    case 5:
    case 10:
      setAllFingersRight(ANGLE_OPEN);
      break;
    case 6:
      setFingersRight(ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_OPEN);
      break;
    case 7:
      setFingersRight(ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_OPEN, ANGLE_OPEN);
      break;
    case 8:
      setFingersRight(ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN);
      break;
    case 9:
      setFingersRight(ANGLE_CLOSED, ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN);
      break;
    default:
      Serial.println("Invalid input for right hand.");
      break;
  }
}

// ==================== LEFT HAND GESTURES ====================
void applyGestureLeft(int val) {
  switch (val) {
    case 0:
      setFingersLeft(ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED);
      break;
    case 1:
      setFingersLeft(ANGLE_CLOSED, ANGLE_OPEN, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED);
      break;
    case 2:
     // new order: thumb, index, middle, ring, pinky
      setFingersLeft(ANGLE_CLOSED, ANGLE_OPEN, ANGLE_OPEN, ANGLE_CLOSED, ANGLE_CLOSED);
      break;
    case 3:
      setFingersLeft(ANGLE_CLOSED, ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN, ANGLE_CLOSED);
      break;
    case 4:
      setFingersLeft(ANGLE_CLOSED, ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN);
      break;
    case 5:
    case 10:
      setAllFingersLeft(ANGLE_OPEN);
      break;
    case 6:
      setFingersLeft(ANGLE_OPEN, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED);
      break;
    case 7:
      setFingersLeft(ANGLE_OPEN, ANGLE_OPEN, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED);

      break;
    case 8:
      setFingersLeft(ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN, ANGLE_CLOSED, ANGLE_CLOSED);
      break;
    case 9:
      setFingersLeft(ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN, ANGLE_CLOSED);
      break;
    default:
      Serial.println("Invalid input for left hand.");
      break;
  }
}

// ==================== HELPER FUNCTIONS ====================

void setServoAngle(uint8_t channel, uint16_t angle) {
  uint16_t pulse = map(angle, 0, 180, SERVOMIN, SERVOMAX);

  pca9685.setPWM(channel, 0, pulse);
}
void setFingersRight(int pinky, int ring, int middle, int index, int thumb) {
  setServoAngle(R_PINKY, pinky);
  setServoAngle(R_RING, ring);
  setServoAngle(R_MIDDLE, middle);
  setServoAngle(R_INDEX, index);
  setServoAngle(R_THUMB, thumb);
}

void setFingersLeft(int thumb, int index, int middle, int ring, int pinky) {
  setServoAngle(L_THUMB, thumb);
  setServoAngle(L_INDEX, index);
  setServoAngle(L_MIDDLE, middle);
  setServoAngle(L_RING, ring);
  setServoAngle(L_PINKY, pinky);
}

void setAllFingersRight(int angle) {
  setFingersRight(angle, angle, angle, angle, angle);
}

void setAllFingersLeft(int angle) {
  setFingersLeft(angle, angle, angle, angle, angle);
}

