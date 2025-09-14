"""
Enhanced Scene Detection System - CutMagic-like functionality
Provides visual scene analysis, automatic cuts, and smart composition detection
"""

import cv2
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional
from moviepy.editor import VideoFileClip
from sklearn.cluster import KMeans
from scipy import spatial
import json
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ShotType(Enum):
    """Shot composition types"""
    CLOSE_UP = "close_up"
    MEDIUM_SHOT = "medium_shot"
    WIDE_SHOT = "wide_shot"
    EXTREME_CLOSE_UP = "extreme_close_up"
    TALKING_HEAD = "talking_head"
    ACTION_SHOT = "action_shot"
    TRANSITION = "transition"


@dataclass
class SceneSegment:
    """Represents a detected scene segment"""
    start_time: float
    end_time: float
    shot_type: ShotType
    confidence: float
    visual_features: Dict
    composition_score: float
    motion_intensity: float
    color_dominance: List[Tuple[int, int, int]]  # RGB values
    face_count: int = 0
    text_detected: bool = False


@dataclass
class SceneTransition:
    """Represents a transition between scenes"""
    timestamp: float
    transition_type: str  # cut, fade, wipe, etc.
    intensity: float  # How dramatic the transition is
    before_scene: Optional[SceneSegment] = None
    after_scene: Optional[SceneSegment] = None


class EnhancedSceneDetector:
    """Advanced scene detection with visual analysis"""

    def __init__(self):
        self.frame_skip = 15  # Analyze every 15th frame for performance
        self.scene_threshold = 0.3  # Scene change sensitivity
        self.face_cascade = None
        self._load_models()

    def _load_models(self):
        """Load OpenCV models for face detection"""
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            logger.info("Face detection model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load face detection model: {e}")

    def detect_scenes(self, video_path: str, max_scenes: int = 50) -> List[SceneSegment]:
        """
        Detect visual scenes using computer vision techniques
        Similar to Quaso's CutMagic scene detection
        """
        scenes = []

        try:
            # Open video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Cannot open video file: {video_path}")
                return scenes

            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps

            logger.info(f"Analyzing video: {duration:.1f}s, {fps:.1f} fps, {total_frames} frames")

            # Extract keyframes for analysis
            keyframes = self._extract_keyframes(cap, fps)

            # Detect scene boundaries
            scene_boundaries = self._detect_scene_boundaries(keyframes)

            # Analyze each scene segment
            scenes = self._analyze_scene_segments(keyframes, scene_boundaries, fps, duration)

            cap.release()

            # Sort scenes by composition score and limit to max_scenes
            scenes.sort(key=lambda x: x.composition_score, reverse=True)
            return scenes[:max_scenes]

        except Exception as e:
            logger.error(f"Error in scene detection: {e}")
            return scenes

    def _extract_keyframes(self, cap: cv2.VideoCapture, fps: float) -> List[Dict]:
        """Extract keyframes with visual features"""
        keyframes = []
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Skip frames for performance
            if frame_count % self.frame_skip != 0:
                frame_count += 1
                continue

            timestamp = frame_count / fps

            # Extract visual features
            features = self._extract_frame_features(frame)

            keyframes.append({
                'timestamp': timestamp,
                'frame': frame,
                'features': features,
                'frame_number': frame_count
            })

            frame_count += 1

            # Limit keyframes for memory efficiency
            if len(keyframes) > 1000:  # ~16 minutes at 1 keyframe per second
                break

        return keyframes

    def _extract_frame_features(self, frame: np.ndarray) -> Dict:
        """Extract comprehensive visual features from a frame"""
        features = {}

        try:
            # Resize for consistent analysis
            frame_resized = cv2.resize(frame, (320, 240))

            # Color histogram
            hist_b = cv2.calcHist([frame_resized], [0], None, [16], [0, 256])
            hist_g = cv2.calcHist([frame_resized], [1], None, [16], [0, 256])
            hist_r = cv2.calcHist([frame_resized], [2], None, [16], [0, 256])
            features['color_hist'] = np.concatenate([hist_b.flatten(), hist_g.flatten(), hist_r.flatten()])

            # Dominant colors
            features['dominant_colors'] = self._get_dominant_colors(frame_resized)

            # Edge density (indicates visual complexity)
            gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            features['edge_density'] = np.sum(edges) / (320 * 240 * 255)

            # Brightness and contrast
            features['brightness'] = np.mean(gray)
            features['contrast'] = np.std(gray)

            # Face detection
            if self.face_cascade is not None:
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
                features['face_count'] = len(faces)
                features['faces'] = faces
            else:
                features['face_count'] = 0
                features['faces'] = []

            # Motion estimation (optical flow if previous frame available)
            features['motion_vectors'] = []

            # Text detection (simple method)
            features['text_detected'] = self._detect_text_regions(gray)

        except Exception as e:
            logger.warning(f"Error extracting frame features: {e}")
            features = self._get_default_features()

        return features

    def _get_dominant_colors(self, frame: np.ndarray, k: int = 5) -> List[Tuple[int, int, int]]:
        """Extract dominant colors using K-means clustering"""
        try:
            # Reshape frame to be a list of pixels
            data = frame.reshape((-1, 3))
            data = np.float32(data)

            # Apply K-means
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, labels, centers = cv2.kmeans(data, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

            # Convert centers to integers and return
            centers = np.uint8(centers)
            return [tuple(center) for center in centers]

        except Exception:
            return [(128, 128, 128)]  # Default gray

    def _detect_text_regions(self, gray_frame: np.ndarray) -> bool:
        """Simple text detection using edge analysis"""
        try:
            # Apply morphological operations to detect text-like regions
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 18))
            grad = cv2.morphologyEx(gray_frame, cv2.MORPH_GRADIENT, kernel)

            # Threshold and find contours
            _, thresh = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Check if we have text-like rectangular contours
            text_regions = 0
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                area = cv2.contourArea(contour)

                # Text typically has specific aspect ratios and sizes
                if 0.2 < aspect_ratio < 10 and area > 100:
                    text_regions += 1

            return text_regions > 3  # Multiple text regions indicate text presence

        except Exception:
            return False

    def _detect_scene_boundaries(self, keyframes: List[Dict]) -> List[float]:
        """Detect scene boundaries using visual similarity"""
        boundaries = [0.0]  # Always include start

        if len(keyframes) < 2:
            return boundaries

        for i in range(1, len(keyframes)):
            current_features = keyframes[i]['features']
            previous_features = keyframes[i-1]['features']

            # Calculate visual similarity
            similarity = self._calculate_visual_similarity(current_features, previous_features)

            # If similarity is below threshold, it's a scene change
            if similarity < self.scene_threshold:
                boundaries.append(keyframes[i]['timestamp'])

        # Always include end
        if boundaries[-1] != keyframes[-1]['timestamp']:
            boundaries.append(keyframes[-1]['timestamp'])

        return boundaries

    def _calculate_visual_similarity(self, features1: Dict, features2: Dict) -> float:
        """Calculate similarity between two frames"""
        try:
            # Color histogram similarity
            hist1 = features1.get('color_hist', np.array([]))
            hist2 = features2.get('color_hist', np.array([]))

            if len(hist1) > 0 and len(hist2) > 0:
                color_sim = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            else:
                color_sim = 0.5

            # Edge density similarity
            edge1 = features1.get('edge_density', 0)
            edge2 = features2.get('edge_density', 0)
            edge_sim = 1 - abs(edge1 - edge2)

            # Brightness similarity
            bright1 = features1.get('brightness', 128)
            bright2 = features2.get('brightness', 128)
            bright_sim = 1 - abs(bright1 - bright2) / 255

            # Combined similarity score
            similarity = (color_sim * 0.6 + edge_sim * 0.25 + bright_sim * 0.15)
            return max(0, min(1, similarity))

        except Exception as e:
            logger.warning(f"Error calculating similarity: {e}")
            return 0.5

    def _analyze_scene_segments(self, keyframes: List[Dict], boundaries: List[float], fps: float, duration: float) -> List[SceneSegment]:
        """Analyze each scene segment for composition and quality"""
        scenes = []

        for i in range(len(boundaries) - 1):
            start_time = boundaries[i]
            end_time = boundaries[i + 1]

            # Find keyframes in this segment
            segment_frames = [
                kf for kf in keyframes
                if start_time <= kf['timestamp'] <= end_time
            ]

            if not segment_frames:
                continue

            # Analyze segment
            scene = self._create_scene_segment(segment_frames, start_time, end_time)
            scenes.append(scene)

        return scenes

    def _create_scene_segment(self, frames: List[Dict], start_time: float, end_time: float) -> SceneSegment:
        """Create a scene segment with analysis"""

        # Aggregate features from all frames in segment
        avg_features = self._aggregate_frame_features(frames)

        # Determine shot type
        shot_type = self._classify_shot_type(avg_features)

        # Calculate composition score
        composition_score = self._calculate_composition_score(avg_features, shot_type)

        # Extract dominant colors
        dominant_colors = avg_features.get('dominant_colors', [(128, 128, 128)])

        return SceneSegment(
            start_time=start_time,
            end_time=end_time,
            shot_type=shot_type,
            confidence=0.8,  # Base confidence
            visual_features=avg_features,
            composition_score=composition_score,
            motion_intensity=avg_features.get('motion_intensity', 0.5),
            color_dominance=dominant_colors,
            face_count=avg_features.get('face_count', 0),
            text_detected=avg_features.get('text_detected', False)
        )

    def _aggregate_frame_features(self, frames: List[Dict]) -> Dict:
        """Aggregate features across multiple frames"""
        if not frames:
            return self._get_default_features()

        features = {}

        # Average numerical features
        numerical_features = ['edge_density', 'brightness', 'contrast', 'face_count']
        for feature in numerical_features:
            values = [f['features'].get(feature, 0) for f in frames]
            features[feature] = np.mean(values) if values else 0

        # Aggregate dominant colors (take from middle frame)
        middle_frame = frames[len(frames) // 2]
        features['dominant_colors'] = middle_frame['features'].get('dominant_colors', [(128, 128, 128)])

        # Text detection (any frame with text)
        features['text_detected'] = any(f['features'].get('text_detected', False) for f in frames)

        # Motion intensity (estimated from edge density variation)
        edge_values = [f['features'].get('edge_density', 0) for f in frames]
        features['motion_intensity'] = np.std(edge_values) if len(edge_values) > 1 else 0.5

        return features

    def _classify_shot_type(self, features: Dict) -> ShotType:
        """Classify the shot type based on visual features"""
        face_count = features.get('face_count', 0)
        edge_density = features.get('edge_density', 0)
        motion_intensity = features.get('motion_intensity', 0)

        # Rules-based classification
        if face_count >= 1 and edge_density < 0.1:
            if face_count == 1:
                return ShotType.TALKING_HEAD
            else:
                return ShotType.MEDIUM_SHOT
        elif edge_density > 0.3:
            return ShotType.WIDE_SHOT
        elif motion_intensity > 0.4:
            return ShotType.ACTION_SHOT
        elif edge_density < 0.05:
            return ShotType.CLOSE_UP
        else:
            return ShotType.MEDIUM_SHOT

    def _calculate_composition_score(self, features: Dict, shot_type: ShotType) -> float:
        """Calculate how well-composed the scene is"""
        score = 0.5  # Base score

        # Face presence bonus
        face_count = features.get('face_count', 0)
        if face_count == 1:
            score += 0.2  # Single face is usually good
        elif face_count == 2:
            score += 0.15  # Two faces can be good for conversations
        elif face_count > 2:
            score += 0.1  # Multiple faces might be crowded

        # Shot type bonuses
        shot_bonuses = {
            ShotType.TALKING_HEAD: 0.25,
            ShotType.CLOSE_UP: 0.15,
            ShotType.MEDIUM_SHOT: 0.2,
            ShotType.ACTION_SHOT: 0.3,
            ShotType.WIDE_SHOT: 0.1,
            ShotType.TRANSITION: -0.1
        }
        score += shot_bonuses.get(shot_type, 0)

        # Contrast bonus (well-lit scenes)
        contrast = features.get('contrast', 0)
        if 50 < contrast < 150:  # Good contrast range
            score += 0.1

        # Text presence bonus
        if features.get('text_detected', False):
            score += 0.1

        # Motion bonus (but not too much)
        motion = features.get('motion_intensity', 0)
        if 0.2 < motion < 0.6:  # Moderate motion is good
            score += 0.1

        return max(0, min(1, score))

    def _get_default_features(self) -> Dict:
        """Return default features for error cases"""
        return {
            'color_hist': np.zeros(48),
            'dominant_colors': [(128, 128, 128)],
            'edge_density': 0.1,
            'brightness': 128,
            'contrast': 50,
            'face_count': 0,
            'faces': [],
            'text_detected': False,
            'motion_intensity': 0.5
        }


def detect_enhanced_scenes(video_path: str, max_scenes: int = 20) -> List[Dict]:
    """
    Main function for enhanced scene detection
    Returns scenes in the format expected by the existing system
    """
    detector = EnhancedSceneDetector()
    scenes = detector.detect_scenes(video_path, max_scenes)

    # Convert to format compatible with existing AI moments system
    enhanced_moments = []
    for scene in scenes:
        moment = {
            "start": scene.start_time,
            "end": scene.end_time,
            "type": "scene_detected",
            "reason": f"{scene.shot_type.value.replace('_', ' ').title()} - Visual analysis",
            "score": scene.composition_score * 10,  # Convert to 1-10 scale
            "tags": [scene.shot_type.value, f"faces_{scene.face_count}"],
            "visual_features": {
                "shot_type": scene.shot_type.value,
                "face_count": scene.face_count,
                "motion_intensity": scene.motion_intensity,
                "text_detected": scene.text_detected,
                "dominant_colors": scene.color_dominance
            }
        }
        enhanced_moments.append(moment)

    return enhanced_moments


def analyze_video_composition(video_path: str) -> Dict:
    """
    Analyze overall video composition and provide insights
    Similar to Quaso's video analysis features
    """
    detector = EnhancedSceneDetector()
    scenes = detector.detect_scenes(video_path, 100)  # Analyze more scenes for comprehensive analysis

    if not scenes:
        return {"error": "No scenes detected"}

    # Calculate overall metrics
    total_duration = max(scene.end_time for scene in scenes)
    avg_scene_length = np.mean([scene.end_time - scene.start_time for scene in scenes])

    # Shot type distribution
    shot_types = {}
    for scene in scenes:
        shot_type = scene.shot_type.value
        shot_types[shot_type] = shot_types.get(shot_type, 0) + 1

    # Face analysis
    face_scenes = [s for s in scenes if s.face_count > 0]
    avg_faces = np.mean([s.face_count for s in face_scenes]) if face_scenes else 0

    # Color analysis
    all_colors = []
    for scene in scenes:
        all_colors.extend(scene.color_dominance)

    # Motion analysis
    high_motion_scenes = [s for s in scenes if s.motion_intensity > 0.6]
    motion_percentage = len(high_motion_scenes) / len(scenes) * 100

    return {
        "total_scenes": len(scenes),
        "total_duration": total_duration,
        "average_scene_length": avg_scene_length,
        "shot_type_distribution": shot_types,
        "face_analysis": {
            "scenes_with_faces": len(face_scenes),
            "average_faces_per_scene": avg_faces,
            "face_coverage_percentage": len(face_scenes) / len(scenes) * 100
        },
        "motion_analysis": {
            "high_motion_scenes": len(high_motion_scenes),
            "motion_percentage": motion_percentage
        },
        "text_scenes": len([s for s in scenes if s.text_detected]),
        "top_scenes": sorted(scenes, key=lambda x: x.composition_score, reverse=True)[:5],
        "quality_score": np.mean([s.composition_score for s in scenes]) * 10
    }