import cv2
import google.generativeai as genai
from PIL import Image
import io
import os
import glob
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()

# Set your Google AI Studio API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize Google AI Studio
genai.configure(api_key=GOOGLE_API_KEY)

DEFAULT_VISION_MODEL = os.getenv("GOOGLE_VISION_MODEL", "gemini-flash-latest")

def get_latest_frame():
    """ Gets the latest image from the frames folder. """
    # Get the path to the frames folder
    frames_folder = os.path.join(os.getcwd(), "frames")
    
    # Check if frames folder exists
    if not os.path.exists(frames_folder):
        print(f"❌ Error: Frames folder not found at {frames_folder}")
        print("Creating frames folder...")
        try:
            os.makedirs(frames_folder)
            print("✅ Created frames folder successfully")
        except Exception as e:
            print(f"❌ Error creating frames folder: {str(e)}")
        return None
    
    # List all image files in the frames folder
    image_files = glob.glob(os.path.join(frames_folder, "*.jpg")) + \
                  glob.glob(os.path.join(frames_folder, "*.jpeg")) + \
                  glob.glob(os.path.join(frames_folder, "*.png"))
    
    if not image_files:
        print(f"❌ Error: No image files found in the frames folder at {frames_folder}")
        print("Please add some image files (jpg, jpeg, or png) to the frames folder")
        return None
    
    # Sort files by modification time (newest first)
    latest_image = max(image_files, key=os.path.getmtime)
    print(f"📷 Using image: {os.path.basename(latest_image)} from {frames_folder}")
    
    # Read the image using OpenCV
    frame = cv2.imread(latest_image)
    
    if frame is None:
        print(f"❌ Error: Could not read image {latest_image}")
        return None
        
    return frame

def process_frame(frame):
    """ Converts the frame to a format compatible with Google AI. """
    if frame is None:
        return None

    # Convert OpenCV image (BGR) to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Convert to PIL Image
    pil_image = Image.fromarray(frame_rgb)

    # Convert PIL image to bytes
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format="JPEG")
    img_byte_arr = img_byte_arr.getvalue()

    return img_byte_arr

def detect_objects(user_question: str) -> str:
    """ Sends the latest frame & user question to Google AI Studio for analysis.
    
    Args:
        user_question: The question or prompt about what to look for in the image.
        
    Returns:
        str: A conversational response describing what was detected in the image.
    """
    print(f"\n🔍 Processing vision query: {user_question}")
    
    # Check if GOOGLE_API_KEY is set
    if not GOOGLE_API_KEY:
        return "I apologize, but I don't have access to my vision capabilities at the moment. Could you please make sure my API key is set up correctly?"
    
    # Get the latest frame from the frames folder
    frame = get_latest_frame()
    
    if frame is None:
        return "I'd love to help you with that, but I don't see any images to look at. Could you make sure there are some images in the 'frames' folder?"
    
    # Process the frame
    print("🖼️ Processing image...")
    image_data = process_frame(frame)
    
    if image_data is None:
        return "I'm having trouble processing the image you want me to look at. Could you try sharing it again?"

    try:
        print("🤖 Sending to Google AI Studio...")
        model = genai.GenerativeModel(DEFAULT_VISION_MODEL)
        
        # Enhance the prompt to encourage more conversational responses
        enhanced_prompt = f"""
        Please respond in a natural, conversational way, as if we're having a face-to-face chat. 
        Treat this as a friendly conversation where I'm asking you about what you see.
        Question: {user_question}
        """
        
        response = model.generate_content([
            {"text": enhanced_prompt},  # Send the enhanced prompt
            {"mime_type": "image/jpeg", "data": image_data}  # Send the image
        ])

        if response and response.text:
            print("✅ Received response from Google AI Studio")
            
            # Post-process the response to make it more conversational if needed
            text = response.text
            
            # Remove common non-conversational patterns
            text = text.replace("The image shows", "I can see")
            text = text.replace("In this image", "Looking at this")
            text = text.replace("I observe", "I notice")
            text = text.replace("It appears to be", "It looks like")
            
            # Add conversational elements
            conversation_starters = [
                "Well, ",
                "Hmm, ",
                "Oh, ",
                "You know what? ",
                "Let me take a look... ",
                "Interesting! "
            ]
            
            # Randomly add a conversation starter 50% of the time
            if random.random() < 0.5:
                text = random.choice(conversation_starters) + text
                
            return text
        else:
            print("❌ No response received from Google AI Studio")
            return "I'm looking at the image, but I'm having trouble putting my thoughts into words. Could you ask me about something specific in the image?"

    except Exception as e:
        error_text = str(e)
        print(f"❌ Error in Google AI Studio processing: {error_text}")
        if "404" in error_text and DEFAULT_VISION_MODEL in error_text:
            return (
                "I'm having trouble analyzing the image because the configured vision model "
                f"'{DEFAULT_VISION_MODEL}' isn't available. You can set a supported model in the "
                "`GOOGLE_VISION_MODEL` environment variable (run `python -c \"import google.generativeai "
                "as genai; genai.configure(api_key=...'`)."
            )
        return (
            "I'm having some trouble analyzing the image right now. "
            f"The specific issue is: {error_text}. Could you try again in a moment?"
        )

def chatbot():
    """ Runs the chatbot interface for object detection queries. """
    print("\n🤖 Vision Chatbot Started! Type 'exit' to quit.")
    print("📁 Using images from the 'frames' folder. Make sure to add images there.")

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() == "exit":
            print("👋 Exiting chatbot.")
            break

        print("🤖 Bot:", detect_objects(user_input))  # Pass question to AI

# Run the chatbot
if __name__ == "__main__":
    chatbot()
