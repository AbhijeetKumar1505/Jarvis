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
        
    def _check_camera_permission(self) -> bool:
        """Check if the application has permission to access the camera."""
        cap = None
        try:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use DirectShow for Windows
            if cap.isOpened():
                ret, _ = cap.read()
                return ret
            return False
        except Exception as e:
            print(f"Camera access error: {e}")
            return False
        finally:
            if cap is not None:
                cap.release()

    def _init_video_capture(self, max_retries: int = 3):
        """Initialize the video capture with retry logic.
        
        Args:
            max_retries: Maximum number of retry attempts
        """
        if self.cap is not None:
            self.cap.release()
            
        for attempt in range(max_retries):
            try:
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use DirectShow for Windows
                if self.cap.isOpened() and self._check_camera_permission():
                    # Set a reasonable resolution
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    return
                
                print(f"Camera initialization attempt {attempt + 1} failed")
                self.cap.release()
                time.sleep(1)  # Wait before retry
                
            except Exception as e:
                print(f"Error initializing camera: {e}")
                if self.cap is not None:
                    self.cap.release()
                    self.cap = None
                
        raise RuntimeError("Could not initialize camera after multiple attempts")
    
    def _save_image(self, frame: np.ndarray, emotion: str, confidence: float) -> str:
        """Save the captured frame with emotion data."""
        if not self.save_images:
            return ""
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join(self.save_dir, f"emotion_{emotion}_{confidence:.2f}_{timestamp}.jpg")
        cv2.imwrite(filename, frame)
        return filename
    
    def _get_test_image(self) -> np.ndarray:
        """Generate a test image when camera is not available."""
        # Create a simple test image with text
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, "Camera Not Available", (50, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        return img

    def _capture_frames(self):
        """Capture frames from the camera in a separate thread with error handling."""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.is_running:
            try:
                # Check if camera is still available
                if self.cap is None or not self.cap.isOpened():
                    print("Camera not available, attempting to reinitialize...")
                    try:
                        self._init_video_capture(max_retries=1)
                        consecutive_errors = 0
                    except Exception as e:
                        print(f"Failed to reinitialize camera: {e}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            # Fallback to test image if we can't recover
                            if not self.frame_queue.empty():
                                try:
                                    self.frame_queue.get_nowait()
                                except queue.Empty:
                                    pass
                            self.frame_queue.put(self._get_test_image())
                            time.sleep(1)  # Prevent tight loop
                        continue
                
                # Try to read a frame
                ret, frame = self.cap.read()
                if not ret:
                    print("Error reading from camera")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        self.cap.release()
                        self.cap = None
                    time.sleep(1)
                    continue
                
                # Reset error counter on successful frame capture
                consecutive_errors = 0
                
                # Put the frame in the queue, replacing any old frame
                if not self.frame_queue.empty():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.frame_queue.put(frame)
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                print(f"Error in capture thread: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors and self.cap is not None:
                    self.cap.release()
                    self.cap = None
                time.sleep(1)
                
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
