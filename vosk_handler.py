# -*- coding: utf-8 -*-
"""
Vosk Speech-to-Text handler for offline English transcription
"""
import os
import json
import wave
import subprocess
from vosk import Model, KaldiRecognizer

# Model path
MODEL_DIR = "vosk_model"
MODEL_NAME = "vosk-model-small-en-us-0.15"
MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"

model = None

def get_model_path():
    """Get the path to the Vosk model"""
    return os.path.join(MODEL_DIR, MODEL_NAME)

def check_model_exists():
    """Check if Vosk model exists"""
    model_path = get_model_path()
    return os.path.exists(model_path) and os.path.isdir(model_path)

def download_model():
    """Download Vosk English model if not exists"""
    import urllib.request
    import zipfile
    
    print(f"VOSK: Downloading model from {MODEL_URL}...")
    
    # Create model directory
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Download zip file
    zip_path = os.path.join(MODEL_DIR, f"{MODEL_NAME}.zip")
    
    try:
        urllib.request.urlretrieve(MODEL_URL, zip_path)
        print(f"VOSK: Model downloaded to {zip_path}")
        
        # Extract zip
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(MODEL_DIR)
        
        # Remove zip file
        os.remove(zip_path)
        
        print(f"VOSK: Model extracted to {get_model_path()}")
        return True
        
    except Exception as e:
        print(f"VOSK: Error downloading model: {e}")
        return False

def init_vosk():
    """Initialize Vosk model"""
    global model
    
    if model is not None:
        return model
    
    # Check if model exists, download if not
    if not check_model_exists():
        print("VOSK: Model not found, downloading...")
        if not download_model():
            print("VOSK: Failed to download model")
            return None
    
    model_path = get_model_path()
    
    try:
        model = Model(model_path)
        print(f"VOSK: Model loaded from {model_path}")
        return model
    except Exception as e:
        print(f"VOSK: Error loading model: {e}")
        return None

def convert_to_wav(audio_path):
    """Convert audio file to WAV format (mono, 16kHz)"""
    wav_path = audio_path.replace('.ogg', '.wav').replace('.oga', '.wav')
    
    try:
        # Use ffmpeg to convert
        subprocess.run([
            'ffmpeg', '-y', '-i', audio_path,
            '-ar', '16000', '-ac', '1', '-f', 'wav',
            wav_path
        ], check=True, capture_output=True)
        
        return wav_path
    except subprocess.CalledProcessError as e:
        print(f"VOSK: ffmpeg conversion error: {e}")
        return None
    except FileNotFoundError:
        print("VOSK: ffmpeg not found, trying pydub...")
        
        # Fallback to pydub
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(audio_path)
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(wav_path, format="wav")
            
            return wav_path
        except Exception as e:
            print(f"VOSK: pydub conversion error: {e}")
            return None

def transcribe_audio(audio_path):
    """
    Transcribe audio file using Vosk
    Returns transcribed text or None on error
    """
    print(f"VOSK: Transcribing {audio_path}")
    
    # Initialize model
    model = init_vosk()
    if model is None:
        print("VOSK: Model not available")
        return None
    
    # Convert to WAV if needed
    if not audio_path.endswith('.wav'):
        wav_path = convert_to_wav(audio_path)
        if wav_path is None:
            print("VOSK: Could not convert to WAV")
            return None
    else:
        wav_path = audio_path
    
    try:
        # Open WAV file
        wf = wave.open(wav_path, "rb")
        
        # Check format
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            print(f"VOSK: Audio format must be PCM WAV mono 16-bit")
            wf.close()
            return None
        
        # Create recognizer
        rec = KaldiRecognizer(model, wf.getframerate())
        
        # Process audio
        results = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                if result.get("text"):
                    results.append(result["text"])
        
        # Get final result
        final_result = json.loads(rec.FinalResult())
        if final_result.get("text"):
            results.append(final_result["text"])
        
        wf.close()
        
        # Combine all results
        transcribed_text = " ".join(results).strip()
        
        print(f"VOSK: Transcribed: '{transcribed_text}'")
        
        # Clean up temporary WAV file if we created one
        if wav_path != audio_path and os.path.exists(wav_path):
            os.remove(wav_path)
        
        return transcribed_text if transcribed_text else None
        
    except Exception as e:
        print(f"VOSK: Transcription error: {e}")
        
        # Clean up temporary WAV file if we created one
        if wav_path != audio_path and os.path.exists(wav_path):
            os.remove(wav_path)
        
        return None
