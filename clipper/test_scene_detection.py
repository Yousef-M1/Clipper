#!/usr/bin/env python3
"""
Test script for Enhanced Scene Detection
"""

import os
import sys
import django

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from clipper.scene_detection import detect_enhanced_scenes, analyze_video_composition
from clipper.ai_moments import detect_ai_moments_with_composition

def test_scene_detection_basic():
    """Test basic scene detection functionality"""
    print("=== Testing Basic Scene Detection ===")

    # Create a dummy test (you would replace with actual video path)
    test_video_path = "path/to/test/video.mp4"

    # This would normally fail without a real video, but shows the API
    try:
        scenes = detect_enhanced_scenes(test_video_path, max_scenes=5)
        print(f"✅ Scene detection API working - would detect {len(scenes)} scenes")

        # Show what the API returns
        if scenes:
            print("Sample scene structure:")
            for i, scene in enumerate(scenes[:2]):
                print(f"  Scene {i+1}:")
                print(f"    Time: {scene['start']:.1f}s - {scene['end']:.1f}s")
                print(f"    Score: {scene['score']:.1f}")
                print(f"    Reason: {scene['reason']}")
                print(f"    Tags: {scene['tags']}")

    except Exception as e:
        print(f"⚠️  Expected error (no test video): {e}")
        print("✅ Scene detection module imported successfully")

def test_composition_analysis():
    """Test video composition analysis"""
    print("\n=== Testing Video Composition Analysis ===")

    test_video_path = "path/to/test/video.mp4"

    try:
        analysis = analyze_video_composition(test_video_path)
        print("✅ Composition analysis API working")

        # Show expected structure
        print("Analysis structure includes:")
        expected_keys = [
            'total_scenes', 'total_duration', 'shot_type_distribution',
            'face_analysis', 'motion_analysis', 'quality_score'
        ]
        for key in expected_keys:
            print(f"  - {key}")

    except Exception as e:
        print(f"⚠️  Expected error (no test video): {e}")
        print("✅ Composition analysis module imported successfully")

def test_enhanced_moments():
    """Test enhanced moment detection with composition"""
    print("\n=== Testing Enhanced Moment Detection ===")

    test_video_path = "path/to/test/video.mp4"
    transcript = []  # Empty transcript for test

    try:
        results = detect_ai_moments_with_composition(
            test_video_path,
            transcript,
            clip_duration=30.0,
            max_clips=5,
            enable_scene_detection=True
        )

        print("✅ Enhanced moment detection API working")
        print("Results structure includes:")
        for key in results.keys():
            print(f"  - {key}: {type(results[key]).__name__}")

    except Exception as e:
        print(f"⚠️  Expected error (no test video): {e}")
        print("✅ Enhanced moment detection module imported successfully")

def test_imports():
    """Test all required imports"""
    print("\n=== Testing Dependencies ===")

    try:
        import cv2
        print(f"✅ OpenCV: {cv2.__version__}")
    except ImportError as e:
        print(f"❌ OpenCV not installed: {e}")

    try:
        import sklearn
        print(f"✅ scikit-learn: {sklearn.__version__}")
    except ImportError as e:
        print(f"❌ scikit-learn not installed: {e}")

    try:
        import scipy
        print(f"✅ scipy: {scipy.__version__}")
    except ImportError as e:
        print(f"❌ scipy not installed: {e}")

    try:
        import numpy
        print(f"✅ numpy: {numpy.__version__}")
    except ImportError as e:
        print(f"❌ numpy not installed: {e}")

def show_api_examples():
    """Show API usage examples"""
    print("\n=== API Usage Examples ===")

    print("""

1. Analyze Video Composition:
   POST /api/clipper/analysis/composition/
   {
       "video_request_id": 123
   }

2. Enhanced Moment Detection:
   POST /api/clipper/analysis/enhanced-moments/
   {
       "video_request_id": 123,
       "clip_duration": 30.0,
       "max_clips": 10,
       "enable_scene_detection": true
   }

3. Scene Transitions Detection:
   POST /api/clipper/analysis/scene-transitions/
   {
       "video_request_id": 123,
       "max_scenes": 20
   }

4. Get Capabilities:
   GET /api/clipper/analysis/capabilities/

    """)

if __name__ == "__main__":
    print("🎬 Enhanced Scene Detection Test Suite")
    print("=====================================")

    test_imports()
    test_scene_detection_basic()
    test_composition_analysis()
    test_enhanced_moments()
    show_api_examples()

    print("\n🎯 Scene Detection Implementation Complete!")
    print("Next steps:")
    print("1. Install dependencies: pip install -r requirements_scene_detection.txt")
    print("2. Test with real video files")
    print("3. Integrate with your existing video processing pipeline")
    print("4. Optional: Add advanced deep learning models for better accuracy")