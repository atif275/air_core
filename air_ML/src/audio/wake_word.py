import pvporcupine
import sounddevice as sd
import numpy as np
from src.config.settings import load_porcupine_api_key

# Load Porcupine wake word model
def detect_wake_word():
    try:
        porcupine = pvporcupine.create(
            access_key=load_porcupine_api_key(),  # Replace with your valid access key
            keyword_paths=["./models/wake_word/Hello-AIR_en_windows_v3_0_0.ppn"]
        )

        print("[INFO] Waiting for wake word...")

        # Open audio stream with correct parameters
        with sd.InputStream(
            samplerate=porcupine.sample_rate,  # Use the correct sampling rate from Porcupine
            channels=1,
            dtype="int16",
            blocksize=porcupine.frame_length  # Ensure blocksize matches expected frame length
        ) as stream:

            print("Listening for wake word...")

            while True:
                pcm = np.frombuffer(stream.read(porcupine.frame_length)[0], dtype=np.int16)

                keyword_index = porcupine.process(pcm)

                if keyword_index >= 0:
                    print("[INFO] Wake word detected!")
                    break

        # Cleanup
        porcupine.delete()
    
    except pvporcupine.PorcupineInvalidArgumentError as e:
        print(f"[ERROR] Invalid argument error: {e}")
    except pvporcupine.PorcupineActivationError as e:
        print(f"[ERROR] Activation error: {e}")
    except pvporcupine.PorcupineActivationLimitError as e:
        print(f"[ERROR] Activation limit reached: {e}")
    except pvporcupine.PorcupineRuntimeError as e:
        print(f"[ERROR] Runtime error: {e}")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")

if __name__ == "__main__":
    detect_wake_word()
