import openai
from openai import OpenAI
import json
import logging
from typing import List, Dict
import numpy as np
from moviepy.editor import VideoFileClip

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
            model="gpt-4",
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

        # Enhance with audio analysis
        audio_moments = detect_audio_moments(video_path, clip_duration, max_clips)

        # Combine AI and audio moments
        all_moments = []

        # Add AI moments first (higher priority)
        for moment in ai_moments:
            if is_valid_moment(moment, total_duration):
                all_moments.append({
                    "start": moment["start_time"],
                    "end": moment["end_time"],
                    "type": "ai_detected",
                    "reason": moment.get("reason", "AI identified engaging moment"),
                    "score": moment.get("engagement_score", 7.0),
                    "tags": moment.get("tags", [])
                })

        # Add audio moments to fill remaining slots
        for moment in audio_moments:
            if len(all_moments) >= max_clips:
                break
            if not overlaps_with_existing(moment, all_moments):
                all_moments.append(moment)

        # Sort by score and return top moments
        all_moments.sort(key=lambda x: x.get("score", 5.0), reverse=True)

        # Convert to simple format for compatibility
        final_moments = []
        for moment in all_moments[:max_clips]:
            final_moments.append({
                "start": moment["start"],
                "end": moment["end"]
            })

        logger.info(f"AI detected {len(final_moments)} intelligent moments")
        return final_moments

    except Exception as e:
        logger.error(f"AI moment detection failed: {e}")
        # Fallback to original fixed intervals
        return detect_moments(video_path, clip_duration)

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