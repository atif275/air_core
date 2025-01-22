import serial
import time

# Establish a serial connection (COM port and baud rate should match the Arduino setup)
ser = serial.Serial('/dev/cu.usbmodem11101', 9600)  # Adjust 'COM3' to match your Arduino's connected port
time.sleep(2)  # Wait for the connection to establish

def move_jaw():
    ser.write(b's')  # Send the command byte 'm' to trigger jaw movement
    # while True:
    #     if ser.in_waiting > 0:
    #         line = ser.readline().decode('utf-8').strip()
    #         print(line)
    #         break
def stop_jaw_movement():
    ser.write(b'e')  # Command to stop jaw movement
    # while True:
    #     if ser.in_waiting > 0:
    #         line = ser.readline().decode('utf-8').strip()
    #         print(line)
    #         break

if __name__ == "__main__":
    # while True:
    #     move_jaw()
    #     time.sleep(2)
    #     stop_jaw_movement()

    move_jaw()
    input("Press Enter to stop jaw movement...")
    stop_jaw_movement()
    ser.close()

