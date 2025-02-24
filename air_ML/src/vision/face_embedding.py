from deepface import DeepFace

# Preload DeepFace models globally for performance
facenet_model = DeepFace.build_model("Facenet")

def get_face_embedding(face_roi):
    """Generates face embedding using DeepFace."""
    try:
        embeddings = DeepFace.represent(face_roi, model_name="Facenet", enforce_detection=False)
        return embeddings[0]['embedding']
    except Exception as e:
        print(f"Error generating face embedding: {e}", flush=True)
        return None

def analyze_person_attributes(face_roi):
    """Runs DeepFace model to analyze age, gender, emotion, and ethnicity."""
    try:
        analysis = DeepFace.analyze(face_roi, actions=["age", "gender", "emotion", "race"], enforce_detection=False)
        result = analysis[0]  # Extract results from DeepFace output

        print(f"[DEBUG] DeepFace Analysis Output: {result}", flush=True)  # 🚀 Debugging Line

        return {
            "age": result.get("age"),
            "gender": result.get("dominant_gender"),  # ✅ Ensure correct key
            "emotion": result.get("dominant_emotion"),  # ✅ Ensure correct key
            "ethnicity": result.get("dominant_race"),  # ✅ Ensure correct key
        }
    except Exception as e:
        print(f"Error analyzing person attributes: {e}", flush=True)
        return None
