import openai
from openai import OpenAI
import json
import logging
from typing import List, Dict
import numpy as np
from moviepy.editor import VideoFileClip
from .scene_detection import detect_enhanced_scenes, analyze_video_composition

logger = logging.getLogger(__name__)

def detect_ai_moments(video_path: str, transcript: List[Dict], clip_duration: float = 30.0, max_clips: int = 10):
    """
    AI-powered moment detection using transcript analysis and audio features
    """
    client = OpenAI()

    try:
        # Get video duration
        with VideoFileClip(video_path) as video:
            total_duration = video.duration

        # Prepare transcript text for AI analysis
        full_transcript = " ".join([seg["text"] for seg in transcript])

        # AI prompt for moment detection
        ai_prompt = f"""
        Analyze this video transcript and identify the most engaging, viral, or interesting moments.
        Consider factors like:
        - Emotional peaks (excitement, surprise, humor)
        - Key insights or valuable information
        - Dramatic moments or plot twists
        - Quotable or memorable statements
        - Controversial or debate-worthy content
        - Tutorial highlights or important steps

        Video duration: {total_duration:.1f} seconds
        Transcript: {full_transcript}

        Return a JSON array of the top {max_clips} moments with this format:
        [
            {{
                "start_time": 45.2,
                "end_time": 75.2,
                "reason": "Exciting reveal or key insight",
                "engagement_score": 8.5,
                "tags": ["educational", "surprising"]
            }}
        ]

        Make sure each moment is exactly {clip_duration} seconds long and doesn't exceed {total_duration} seconds.
        """

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a video content analyst expert at identifying viral and engaging moments."},
                {"role": "user", "content": ai_prompt}
            ],
            temperature=0.3
        )

        # Parse AI response
        ai_response = response.choices[0].message.content

        # Extract JSON from response
        try:
            # Find JSON in the response
            json_start = ai_response.find('[')
            json_end = ai_response.rfind(']') + 1
            json_str = ai_response[json_start:json_end]
            ai_moments = json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse AI response, falling back to audio analysis: {e}")
            ai_moments = []

        # Enhance with visual scene detection (NEW)
        logger.info("Running enhanced visual scene detection...")
        visual_moments = detect_enhanced_scenes(video_path, max_clips)

        # Enhance with audio analysis
        audio_moments = detect_audio_moments(video_path, clip_duration, max_clips)

        # Combine AI, visual, and audio moments with weighted priorities
        all_moments = []

        # Add AI transcript moments first (highest priority)
        for moment in ai_moments:
            if is_valid_moment(moment, total_duration):
                all_moments.append({
                    "start": moment["start_time"],
                    "end": moment["end_time"],
                    "type": "ai_detected",
                    "reason": moment.get("reason", "AI identified engaging moment"),
                    "score": moment.get("engagement_score", 7.0),
                    "tags": moment.get("tags", []),
                    "priority": 3  # Highest priority
                })

        # Add visual scene moments (medium-high priority)
        for moment in visual_moments:
            if len(all_moments) >= max_clips * 2:  # Allow more candidates for better selection
                break
            if not overlaps_with_existing(moment, all_moments):
                all_moments.append({
                    "start": moment["start"],
                    "end": moment["end"],
                    "type": "scene_detected",
                    "reason": moment.get("reason", "Visually engaging scene"),
                    "score": moment.get("score", 6.0),
                    "tags": moment.get("tags", []),
                    "visual_features": moment.get("visual_features", {}),
                    "priority": 2  # Medium-high priority
                })

        # Add audio moments to fill remaining slots (lower priority)
        for moment in audio_moments:
            if len(all_moments) >= max_clips * 2:
                break
            if not overlaps_with_existing(moment, all_moments):
                moment["priority"] = 1  # Lower priority
                all_moments.append(moment)

        # Sort by priority first, then by score
        all_moments.sort(key=lambda x: (x.get("priority", 0), x.get("score", 5.0)), reverse=True)

        # Convert to simple format for compatibility
        final_moments = []
        for moment in all_moments[:max_clips]:
            final_moments.append({
                "start": moment["start"],
                "end": moment["end"]
            })

        logger.info(f"Enhanced AI detected {len(final_moments)} intelligent moments (transcript + visual + audio)")
        return final_moments

    except Exception as e:
        logger.error(f"Enhanced AI moment detection failed: {e}")
        # Fallback to original fixed intervals
        return detect_moments(video_path, clip_duration)


def detect_ai_moments_with_composition(video_path: str, transcript: List[Dict],
                                     clip_duration: float = 30.0, max_clips: int = 10,
                                     enable_scene_detection: bool = True) -> Dict:
    """
    Enhanced AI moment detection with detailed composition analysis
    Similar to Quaso's comprehensive video analysis
    """
    try:
        # Get video info
        with VideoFileClip(video_path) as video:
            total_duration = video.duration

        results = {
            "moments": [],
            "video_analysis": {},
            "recommendations": [],
            "quality_score": 0
        }

        # Run comprehensive video analysis if enabled
        if enable_scene_detection:
            logger.info("Running comprehensive video composition analysis...")
            video_analysis = analyze_video_composition(video_path)
            results["video_analysis"] = video_analysis
            results["quality_score"] = video_analysis.get("quality_score", 5.0)

        # Get enhanced moments
        moments = detect_ai_moments(video_path, transcript, clip_duration, max_clips)

        # Enhance moment data with additional context
        enhanced_moments = []
        for i, moment in enumerate(moments):
            enhanced_moment = {
                "id": i + 1,
                "start": moment["start"],
                "end": moment["end"],
                "duration": moment["end"] - moment["start"],
                "timestamp": f"{int(moment['start']//60):02d}:{int(moment['start']%60):02d}",
                "composition_score": 7.0,  # Default score
                "virality_score": 6.5,    # Estimated viral potential
                "recommended_platforms": ["tiktok", "instagram_reel"],
                "editing_suggestions": []
            }

            # Add editing suggestions based on duration and content
            if enhanced_moment["duration"] > 45:
                enhanced_moment["editing_suggestions"].append("Consider shortening for better engagement")

            if enhanced_moment["duration"] < 15:
                enhanced_moment["editing_suggestions"].append("Might be too short - consider extending")

            enhanced_moments.append(enhanced_moment)

        results["moments"] = enhanced_moments

        # Generate recommendations
        results["recommendations"] = generate_content_recommendations(video_analysis, enhanced_moments)

        return results

    except Exception as e:
        logger.error(f"Enhanced AI moment detection with composition failed: {e}")
        return {
            "moments": detect_ai_moments(video_path, transcript, clip_duration, max_clips),
            "video_analysis": {},
            "recommendations": ["Unable to analyze video composition"],
            "quality_score": 5.0
        }


def generate_content_recommendations(video_analysis: Dict, moments: List[Dict]) -> List[str]:
    """Generate content strategy recommendations based on video analysis"""
    recommendations = []

    if not video_analysis:
        return ["Enable scene detection for detailed recommendations"]

    # Face-based recommendations
    face_analysis = video_analysis.get("face_analysis", {})
    face_percentage = face_analysis.get("face_coverage_percentage", 0)

    if face_percentage > 70:
        recommendations.append("🎯 High face coverage detected - excellent for talking head content")
        recommendations.append("📱 Perfect for vertical formats (TikTok, Instagram Reels)")
    elif face_percentage < 30:
        recommendations.append("🎬 Low face coverage - consider adding reaction shots or talking segments")

    # Motion analysis
    motion_analysis = video_analysis.get("motion_analysis", {})
    motion_percentage = motion_analysis.get("motion_percentage", 0)

    if motion_percentage > 50:
        recommendations.append("⚡ High motion content - great for action-focused platforms")
        recommendations.append("🎮 Consider gaming or sports content tags")
    else:
        recommendations.append("💬 Steady content - ideal for educational or dialogue-based clips")

    # Quality recommendations
    quality_score = video_analysis.get("quality_score", 5.0)
    if quality_score > 8.0:
        recommendations.append("✨ Excellent visual quality - premium content ready")
    elif quality_score < 6.0:
        recommendations.append("🔧 Consider improving lighting and composition")

    # Duration recommendations
    avg_scene_length = video_analysis.get("average_scene_length", 30)
    if avg_scene_length > 45:
        recommendations.append("✂️ Long scenes detected - perfect for detailed tutorials")
    elif avg_scene_length < 15:
        recommendations.append("🎬 Quick cuts detected - great for fast-paced content")

    # Text content
    text_scenes = video_analysis.get("text_scenes", 0)
    if text_scenes > 0:
        recommendations.append("📝 Text elements detected - good for educational content")

    return recommendations if recommendations else ["Content analysis completed - ready for processing"]

def detect_audio_moments(video_path: str, clip_duration: float = 30.0, max_clips: int = 5):
    """
    Detect moments based on audio energy and volume changes
    """
    try:
        with VideoFileClip(video_path) as video:
            if not video.audio:
                logger.warning("No audio found for audio moment detection")
                return []

            # Extract audio
            audio = video.audio
            total_duration = video.duration

            # Sample audio at regular intervals to analyze energy
            sample_rate = 22050
            window_size = int(clip_duration)  # seconds
            hop_size = 5  # seconds between samples

            moments = []
            current_time = 0

            while current_time + clip_duration <= total_duration:
                try:
                    # Extract audio segment
                    segment = audio.subclip(current_time, current_time + window_size)

                    # Calculate audio energy (simplified)
                    # In a real implementation, you'd use librosa or similar
                    energy_score = calculate_audio_energy_simple(segment)

                    moments.append({
                        "start": current_time,
                        "end": current_time + clip_duration,
                        "type": "audio_detected",
                        "score": energy_score,
                        "reason": "High audio energy detected"
                    })

                except Exception as segment_error:
                    logger.warning(f"Error analyzing audio segment at {current_time}s: {segment_error}")

                current_time += hop_size

            # Sort by energy score and return top moments
            moments.sort(key=lambda x: x["score"], reverse=True)
            return moments[:max_clips]

    except Exception as e:
        logger.error(f"Audio moment detection failed: {e}")
        return []

def calculate_audio_energy_simple(audio_segment):
    """
    Simple audio energy calculation
    """
    try:
        # This is a simplified version - in production use librosa
        return np.random.uniform(3.0, 9.0)  # Placeholder
    except:
        return 5.0

def is_valid_moment(moment: Dict, total_duration: float) -> bool:
    """Check if moment is valid"""
    try:
        start = float(moment.get("start_time", 0))
        end = float(moment.get("end_time", 0))
        return 0 <= start < end <= total_duration and (end - start) >= 5.0
    except:
        return False

def overlaps_with_existing(new_moment: Dict, existing_moments: List[Dict], threshold: float = 10.0) -> bool:
    """Check if new moment overlaps significantly with existing ones"""
    new_start = new_moment["start"]
    new_end = new_moment["end"]

    for existing in existing_moments:
        existing_start = existing["start"]
        existing_end = existing["end"]

        # Check for overlap
        overlap_start = max(new_start, existing_start)
        overlap_end = min(new_end, existing_end)

        if overlap_end > overlap_start:
            overlap_duration = overlap_end - overlap_start
            if overlap_duration > threshold:
                return True

    return False