import cv2
import numpy as np
from fer import FER
import os
import threading
import time
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime
import queue

@dataclass
class EmotionResult:
    emotion: str
    confidence: float
    timestamp: str
    image_path: Optional[str] = None

class EmotionDetector:
    def __init__(self, save_images: bool = False, save_dir: str = 'emotion_data'):
        """
        Initialize the emotion detector.
        
        Args:
            save_images: Whether to save captured frames with emotion data
            save_dir: Directory to save captured images (if save_images is True)
        """
        self.detector = FER(mtcnn=True)
        self.save_images = save_images
        self.save_dir = save_dir
        self.is_running = False
        self.current_emotion: Optional[EmotionResult] = None
        self.lock = threading.Lock()
        self.cap = None
        self.frame_queue = queue.Queue(maxsize=1)  # Queue to hold the latest frame
        
        if save_images and not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        # Initialize video capture
        self._init_video_capture()
        
    def _init_video_capture(self):
        """Initialize the video capture."""
        if self.cap is not None:
            self.cap.release()
            
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("Could not open video device")
            
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_frames, daemon=True)
        self.capture_thread.start()
    
    def _save_image(self, frame: np.ndarray, emotion: str, confidence: float) -> str:
        """Save the captured frame with emotion data."""
        if not self.save_images:
            return ""
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(self.save_dir, f"emotion_{emotion}_{confidence:.2f}_{timestamp}.jpg")
        cv2.imwrite(filename, frame)
        return filename
    
    def _capture_frames(self):
        """Continuously capture frames from the webcam."""
        while self.is_running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)  # Small delay if frame read fails
                continue
                
            # Convert BGR to RGB (FER expects RGB)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Update the frame in the queue
            if not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()  # Discard old frame
                except queue.Empty:
                    pass
            self.frame_queue.put(rgb_frame)
            
    def _process_frame(self, frame: np.ndarray) -> Optional[EmotionResult]:
        """
        Process a single frame to detect emotions.
        
        Args:
            frame: RGB image as a numpy array
            
        Returns:
            EmotionResult if emotion detected, None otherwise
        """
        try:
            # Detect emotions in the frame
            emotions = self.detector.detect_emotions(frame)
            
            if not emotions:
                return None
                
            # Get the most prominent emotion
            emotion_data = emotions[0]['emotions']
            emotion = max(emotion_data.items(), key=lambda x: x[1])
            
            # Create result
            result = EmotionResult(
                emotion=emotion[0],
                confidence=float(emotion[1]),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            # Save image if enabled
            if self.save_images:
                # Convert back to BGR for saving
                bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                result.image_path = self._save_image(bgr_frame, result.emotion, result.confidence)
                
            return result
            
        except Exception as e:
            print(f"Error processing frame: {e}")
            return None
    
    def start(self, camera_index: int = 0):
        """Start the emotion detection in a background thread."""
        if self.is_running:
            return
            
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError("Could not open camera")
            
        self.is_running = True
        self.thread = threading.Thread(target=self._run_detection, daemon=True)
        self.thread.start()
    
    def _run_detection(self):
        """Main detection loop to run in a separate thread."""
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                continue
                
            result = self._process_frame(frame)
            if result:
                with self.lock:
                    self.current_emotion = result
            
            # Limit processing to ~5 FPS to reduce CPU usage
            time.sleep(0.2)
    
    def get_emotion(self) -> Optional[EmotionResult]:
        """
        Get the current emotion detection result.
        
        Returns:
            EmotionResult object containing the detected emotion and confidence,
            or None if no emotion was detected.
        """
        try:
            # Get the latest frame from the queue
            frame = self.frame_queue.get_nowait()
            
            # Process the frame
            result = self._process_frame(frame)
            
            # Update the current emotion
            with self.lock:
                self.current_emotion = result
                
            return result
            
        except queue.Empty:
            with self.lock:
                return self.current_emotion
    
    def stop(self):
        """Stop the emotion detector and release resources."""
        self.is_running = False
        
        # Stop the capture thread
        if hasattr(self, 'capture_thread') and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)
            
        # Stop the detection thread if it exists
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        # Release the video capture
        if self.cap is not None:
            self.cap.release()
            self.cap = None
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

# Global emotion detector instance
emotion_detector = EmotionDetector(save_images=True)
