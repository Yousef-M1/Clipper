"""
Real Video Transcript Extractor
Extracts actual transcript from video processing subtitle files
"""

import glob
import re
import os
from typing import Dict, Optional


class VideoTranscriptExtractor:
    """Extract real transcript from video processing system"""

    def __init__(self):
        self.temp_subtitle_path = "/tmp"

    def extract_transcript_from_video_request(self, video_request) -> Dict[str, str]:
        """
        Extract full transcript from a video request's subtitle files

        Returns:
            Dict with transcript, title, and duration
        """
        try:
            video_id = video_request.id

            # Find all subtitle files for this video
            subtitle_pattern = f"{self.temp_subtitle_path}/clip_{video_id}_*.ass"
            subtitle_files = sorted(glob.glob(subtitle_pattern))

            if not subtitle_files:
                return self._fallback_transcript(video_request)

            # Extract text from all subtitle files
            all_transcript_parts = []
            total_duration = 0

            for subtitle_file in subtitle_files:
                transcript_part, duration = self._extract_text_from_ass_file(subtitle_file)
                if transcript_part:
                    all_transcript_parts.append(transcript_part)
                    total_duration += duration

            if not all_transcript_parts:
                return self._fallback_transcript(video_request)

            # Combine all parts into full transcript
            full_transcript = " ".join(all_transcript_parts)

            # Clean up the transcript
            full_transcript = self._clean_transcript(full_transcript)

            # Generate title from URL or content
            video_title = self._generate_title_from_url(video_request.url) or "Video Content"

            return {
                'transcript': full_transcript,
                'title': video_title,
                'duration': total_duration,
                'source': 'real_subtitles',
                'clips_processed': len(subtitle_files)
            }

        except Exception as e:
            print(f"Error extracting transcript: {e}")
            return self._fallback_transcript(video_request)

    def _extract_text_from_ass_file(self, file_path: str) -> tuple[str, float]:
        """Extract text from a single ASS subtitle file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            dialogue_lines = []
            start_times = []
            end_times = []

            for line in content.split('\n'):
                if line.startswith('Dialogue:'):
                    # ASS format: Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
                    parts = line.split(',', 9)
                    if len(parts) >= 10:
                        start_time = parts[1].strip()
                        end_time = parts[2].strip()
                        text = parts[9].strip()

                        # Remove ASS formatting tags
                        text = re.sub(r'\\{[^}]*\\}', '', text)
                        text = re.sub(r'\\[nN]', ' ', text)  # Replace line breaks
                        text = re.sub(r'\\c&h[^&]*&', '', text)  # Remove color tags
                        text = re.sub(r'\\bord\d+', '', text)  # Remove border tags
                        text = re.sub(r'\\shad\d+', '', text)  # Remove shadow tags
                        text = re.sub(r'\\blur\d+', '', text)  # Remove blur tags
                        text = re.sub(r'\\[a-zA-Z]+\d*', '', text)  # Remove other tags

                        if text and text not in dialogue_lines:
                            dialogue_lines.append(text)
                            start_times.append(start_time)
                            end_times.append(end_time)

            # Calculate duration
            duration = len(dialogue_lines) * 2  # Rough estimate

            return " ".join(dialogue_lines), duration

        except Exception as e:
            print(f"Error reading ASS file {file_path}: {e}")
            return "", 0

    def _clean_transcript(self, transcript: str) -> str:
        """Clean and improve transcript text"""
        # Remove all ASS formatting tags aggressively
        transcript = re.sub(r'{[^}]*}', '', transcript)  # Remove all {tags}
        transcript = re.sub(r'\\[a-zA-Z]+\d*', '', transcript)  # Remove \tags
        transcript = re.sub(r'&h[0-9a-fA-F]+&', '', transcript)  # Remove color codes
        transcript = re.sub(r'[{}\\&]', '', transcript)  # Remove remaining special chars

        # Remove extra whitespace
        transcript = re.sub(r'\s+', ' ', transcript)

        # Remove repeated phrases (common in auto-transcription)
        words = transcript.split()
        cleaned_words = []
        prev_word = ""

        for word in words:
            # Skip repeated words
            if word.lower() != prev_word.lower() and len(word) > 1:
                cleaned_words.append(word)
                prev_word = word

        # Capitalize sentences and add proper punctuation
        transcript = " ".join(cleaned_words)

        # Fix common transcription issues
        transcript = transcript.replace('  ', ' ')
        transcript = transcript.replace(' ,', ',')
        transcript = transcript.replace(' .', '.')

        # Capitalize first letter
        if transcript:
            transcript = transcript[0].upper() + transcript[1:] if len(transcript) > 1 else transcript.upper()

        return transcript.strip()

    def _generate_title_from_url(self, url: str) -> Optional[str]:
        """Generate a title from YouTube URL"""
        try:
            # Extract video ID and create generic title
            if 'youtube.com' in url or 'youtu.be' in url:
                if 'v=' in url:
                    video_id = url.split('v=')[1].split('&')[0]
                elif 'youtu.be/' in url:
                    video_id = url.split('youtu.be/')[1].split('?')[0]
                else:
                    video_id = "video"

                return f"Video Content - {video_id}"

            return "Video Content"

        except:
            return "Video Content"

    def _fallback_transcript(self, video_request) -> Dict[str, str]:
        """Fallback when no subtitle files found"""
        return {
            'transcript': f"Content from video: {video_request.url}. This video discusses various topics and provides insights for viewers interested in the subject matter.",
            'title': "Video Content",
            'duration': 180,
            'source': 'fallback',
            'clips_processed': 0
        }


# Convenience function for easy import
def extract_real_transcript(video_request) -> Dict[str, str]:
    """Extract real transcript from video request"""
    extractor = VideoTranscriptExtractor()
    return extractor.extract_transcript_from_video_request(video_request)