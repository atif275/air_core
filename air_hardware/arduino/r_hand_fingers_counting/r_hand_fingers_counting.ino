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

// Constants for angles
const int ANGLE_OPEN = 0;    // Open position
const int ANGLE_CLOSED = 120; // Closed position

void setup() {
  Serial.begin(9600); // Start serial communication
  pca9685.begin();
  pca9685.setPWMFreq(50); // Set frequency to 50Hz

  // Initialize all fingers to open position
  setAllFingersAngle(ANGLE_OPEN);

  Serial.println("Enter a number between 1 and 10:");
}

void loop() {
  if (Serial.available() > 0) {
    int command = Serial.parseInt(); // Read the number entered

    switch (command) {
      case 1:
        setFingers(ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_OPEN, ANGLE_CLOSED); // Close all except index
        break;
      case 2:
        setFingers(ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_OPEN, ANGLE_OPEN, ANGLE_CLOSED); // Close all except index and middle
        break;
      case 3:
        setFingers(ANGLE_CLOSED, ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN, ANGLE_CLOSED); // Close thumb and pinky
        break;
      case 4:
        setFingers(ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN, ANGLE_CLOSED); // Close thumb only
        break;
      case 5:
        setAllFingersAngle(ANGLE_OPEN); // Open all fingers
        break;
      case 6:
        setFingers(ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_OPEN); // Close all except thumb
        break;
      case 7:
        setFingers(ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_OPEN, ANGLE_OPEN); // Open thumb and index
        break;
      case 8:
        setFingers(ANGLE_CLOSED, ANGLE_CLOSED, ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN); // Open thumb, index, and middle
        break;
      case 9:
        setFingers(ANGLE_CLOSED, ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN, ANGLE_OPEN); // Open all except pinky
        break;
      case 10:
        setAllFingersAngle(ANGLE_OPEN); // Open all fingers
        break;
      default:
        Serial.println("Invalid command. Enter a number between 1 and 10.");
        break;
    }

    printAngles();
  }
}

// Function to set specific angles for all fingers
void setFingers(int pinky, int ring, int middle, int index, int thumb) {
  setServoAngle(PINKY_CHANNEL, pinky);
  setServoAngle(RING_CHANNEL, ring);
  setServoAngle(MIDDLE_CHANNEL, middle);
  setServoAngle(INDEX_CHANNEL, index);
  setServoAngle(THUMB_CHANNEL, thumb);
}

// Function to set all fingers to the same angle
void setAllFingersAngle(int angle) {
  setFingers(angle, angle, angle, angle, angle);
}

// Function to write a specific angle to a servo
void setServoAngle(uint8_t channel, uint16_t angle) {
  uint16_t pulse = map(angle, 0, 180, SERVOMIN, SERVOMAX);
  pca9685.setPWM(channel, 0, pulse);
}

// Function to print the current angles of all fingers
void printAngles() {
  Serial.println("Finger positions updated.");
}
