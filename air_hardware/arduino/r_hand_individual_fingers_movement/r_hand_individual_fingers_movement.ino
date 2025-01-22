#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Create an instance of the PCA9685
Adafruit_PWMServoDriver pca9685 = Adafruit_PWMServoDriver();

// Define servo channels for each finger
#define PINKY_CHANNEL 0
#define RING_CHANNEL 1
#define MIDDLE_CHANNEL 2
#define INDEX_CHANNEL 3
#define THUMB_CHANNEL 4

// Servo parameters
#define SERVOMIN 150  // Min pulse length
#define SERVOMAX 600  // Max pulse length

int pinkyAngle = 0;
int ringAngle = 0;
int middleAngle = 0;
int indexAngle = 0;
int thumbAngle = 0;
const int upperLimit = 120;
const int lowerLimit = 0;
const int stepSize = 20; // Step size for increment/decrement

void setup() {
  Serial.begin(9600); // Start serial communication for reading keypresses
  pca9685.begin();
  pca9685.setPWMFreq(50); // Set frequency to 50Hz (common for servos)

  // Initialize all fingers to 0 degrees
  setServoAngle(PINKY_CHANNEL, pinkyAngle);
  setServoAngle(RING_CHANNEL, ringAngle);
  setServoAngle(MIDDLE_CHANNEL, middleAngle);
  setServoAngle(INDEX_CHANNEL, indexAngle);
  setServoAngle(THUMB_CHANNEL, thumbAngle);

  Serial.println("Control fingers using keys:");
  Serial.println("'q/a' for pinky, 'w/s' for ring, 'e/d' for middle, 'r/f' for index, 't/g' for thumb.");
  Serial.println("'o' to set all to 0 degrees, 'p' to set all to 120 degrees.");
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();

    switch (command) {
      case 'q':
        pinkyAngle = constrain(pinkyAngle + stepSize, lowerLimit, upperLimit);
        setServoAngle(PINKY_CHANNEL, pinkyAngle);
        break;
      case 'a':
        pinkyAngle = constrain(pinkyAngle - stepSize, lowerLimit, upperLimit);
        setServoAngle(PINKY_CHANNEL, pinkyAngle);
        break;
      case 'w':
        ringAngle = constrain(ringAngle + stepSize, lowerLimit, upperLimit);
        setServoAngle(RING_CHANNEL, ringAngle);
        break;
      case 's':
        ringAngle = constrain(ringAngle - stepSize, lowerLimit, upperLimit);
        setServoAngle(RING_CHANNEL, ringAngle);
        break;
      case 'e':
        middleAngle = constrain(middleAngle + stepSize, lowerLimit, upperLimit);
        setServoAngle(MIDDLE_CHANNEL, middleAngle);
        break;
      case 'd':
        middleAngle = constrain(middleAngle - stepSize, lowerLimit, upperLimit);
        setServoAngle(MIDDLE_CHANNEL, middleAngle);
        break;
      case 'r':
        indexAngle = constrain(indexAngle + stepSize, lowerLimit, upperLimit);
        setServoAngle(INDEX_CHANNEL, indexAngle);
        break;
      case 'f':
        indexAngle = constrain(indexAngle - stepSize, lowerLimit, upperLimit);
        setServoAngle(INDEX_CHANNEL, indexAngle);
        break;
      case 't':
        thumbAngle = constrain(thumbAngle + stepSize, lowerLimit, upperLimit);
        setServoAngle(THUMB_CHANNEL, thumbAngle);
        break;
      case 'g':
        thumbAngle = constrain(thumbAngle - stepSize, lowerLimit, upperLimit);
        setServoAngle(THUMB_CHANNEL, thumbAngle);
        break;
      case 'o':
        setAllFingersAngle(0);
        break;
      case 'p':
        setAllFingersAngle(120);
        break;
      default:
        Serial.println("Invalid command.");
        break;
    }

    printAngles();
  }
}

// Function to write a specific angle to a servo
void setServoAngle(uint8_t channel, uint16_t angle) {
  uint16_t pulse = map(angle, 0, 180, SERVOMIN, SERVOMAX);
  pca9685.setPWM(channel, 0, pulse);
}

// Function to set all fingers to the same angle
void setAllFingersAngle(int angle) {
  pinkyAngle = constrain(angle, lowerLimit, upperLimit);
  ringAngle = constrain(angle, lowerLimit, upperLimit);
  middleAngle = constrain(angle, lowerLimit, upperLimit);
  indexAngle = constrain(angle, lowerLimit, upperLimit);
  thumbAngle = constrain(angle, lowerLimit, upperLimit);

  setServoAngle(PINKY_CHANNEL, pinkyAngle);
  setServoAngle(RING_CHANNEL, ringAngle);
  setServoAngle(MIDDLE_CHANNEL, middleAngle);
  setServoAngle(INDEX_CHANNEL, indexAngle);
  setServoAngle(THUMB_CHANNEL, thumbAngle);
}

// Function to print the angles of all fingers
void printAngles() {
  Serial.print("Pinky: "); Serial.print(pinkyAngle);
  Serial.print(" | Ring: "); Serial.print(ringAngle);
  Serial.print(" | Middle: "); Serial.print(middleAngle);
  Serial.print(" | Index: "); Serial.print(indexAngle);
  Serial.print(" | Thumb: "); Serial.println(thumbAngle);
}
