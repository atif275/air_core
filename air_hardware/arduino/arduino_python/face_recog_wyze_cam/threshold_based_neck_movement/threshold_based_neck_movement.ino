// Motor driver pin assignments
const int IN3 = 5;
const int IN4 = 6;
const int ENB = 7; // PWM pin

// Motion tracking
int position = 0;                    // Center = 0
const int MAX_LEFT = -120;          // Fixed limit
const int MAX_RIGHT = 120;          // Fixed limit

// Motor behavior
const int motorSpeed = 200;         // PWM value (0–255)
const int stepSize = 5;             // Smaller step for smoother movement
const int moveDelay = 80;           // Shorter delay for smoother movement
const int rampStep = 10;            // PWM ramp increment
const int rampDelay = 10;           // Delay between ramp steps (ms)

void setup() {
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(ENB, OUTPUT);

  Serial.begin(9600);
  stopMotor();

  Serial.println("Motor Control Started.");
  Serial.println("Commands: 'L'=left, 'R'=right, 'M'=center, 'ML'=show MAX_LEFT, 'MR'=show MAX_RIGHT");
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input.equalsIgnoreCase("L")) {
      if (position - stepSize >= MAX_LEFT) {
        moveLeft();
      } else {
        Serial.println("Left limit reached.");
      }
    } else if (input.equalsIgnoreCase("R")) {
      if (position + stepSize <= MAX_RIGHT) {
        moveRight();
      } else {
        Serial.println("Right limit reached.");
      }
    } else if (input.equalsIgnoreCase("M")) {
      moveToCenter();
    } else if (input.equalsIgnoreCase("ML")) {
      Serial.println("MAX_LEFT = " + String(MAX_LEFT));
    } else if (input.equalsIgnoreCase("MR")) {
      Serial.println("MAX_RIGHT = " + String(MAX_RIGHT));
    } else {
      Serial.println("Unknown command: " + input);
    }

    printStatus();
  }
}

void rampMotor(int fromSpeed, int toSpeed, int directionPin1, int directionPin2) {
  int step = (toSpeed > fromSpeed) ? rampStep : -rampStep;
  for (int speed = fromSpeed; speed != toSpeed; speed += step) {
    digitalWrite(directionPin1, HIGH);
    digitalWrite(directionPin2, LOW);
    analogWrite(ENB, speed);
    delay(rampDelay);
  }
  analogWrite(ENB, toSpeed);
}

void moveLeft() {
  // Ramp up
  rampMotor(0, motorSpeed, IN3, IN4);
  delay(moveDelay);
  // Ramp down
  rampMotor(motorSpeed, 0, IN3, IN4);
  stopMotor();
  position -= stepSize;
  Serial.println("READY");
}

void moveRight() {
  // Ramp up
  rampMotor(0, motorSpeed, IN4, IN3);
  delay(moveDelay);
  // Ramp down
  rampMotor(motorSpeed, 0, IN4, IN3);
  stopMotor();
  position += stepSize;
  Serial.println("READY");
}

void moveToCenter() {
  Serial.println("Returning to center...");
  while (position != 0) {
    if (position > 0 && position - stepSize >= MAX_LEFT) {
      moveLeft();
    } else if (position < 0 && position + stepSize <= MAX_RIGHT) {
      moveRight();
    } else {
      break; // Safety: stop if thresholds would be exceeded
    }
  }
  Serial.println("Centered.");
  Serial.println("READY");
}

void stopMotor() {
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  analogWrite(ENB, 0);
}

void printStatus() {
  Serial.println("Current Position: " + String(position));
}
