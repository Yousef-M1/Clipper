import json
import os
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class CaptionStyleManager:
    """
    Manages different caption styles and word-by-word highlighting effects
    """

    CAPTION_STYLES = {
        'modern_purple': {
            'name': 'Modern Purple',
            'font': 'Arial-Bold',
            'font_size': 24,
            'primary_color': 'white',
            'highlight_color': '#8B5CF6',  # Purple
            'outline_color': 'black',
            'outline_width': 2,
            'position': 'bottom',
            'animation': 'word_highlight',
            'background': 'semi_transparent'
        },
        'tiktok_style': {
            'name': 'TikTok Style',
            'font': 'Arial-Black',
            'font_size': 28,
            'primary_color': 'white',
            'highlight_color': '#FF6B6B',  # Red/Pink
            'outline_color': 'black',
            'outline_width': 3,
            'position': 'center',
            'animation': 'bounce_highlight',
            'background': 'none'
        },
        'youtube_style': {
            'name': 'YouTube Style',
            'font': 'Roboto-Bold',
            'font_size': 22,
            'primary_color': 'white',
            'highlight_color': '#FFD700',  # Gold
            'outline_color': 'black',
            'outline_width': 1,
            'position': 'bottom',
            'animation': 'fade_highlight',
            'background': 'black_box'
        },
        'instagram_story': {
            'name': 'Instagram Story',
            'font': 'Helvetica-Bold',
            'font_size': 26,
            'primary_color': 'white',
            'highlight_color': '#E91E63',  # Pink
            'outline_color': 'none',
            'outline_width': 0,
            'position': 'center',
            'animation': 'scale_highlight',
            'background': 'gradient_box'
        },
        'podcast_style': {
            'name': 'Podcast Style',
            'font': 'Georgia',
            'font_size': 20,
            'primary_color': 'white',
            'highlight_color': '#4CAF50',  # Green
            'outline_color': 'black',
            'outline_width': 1,
            'position': 'bottom',
            'animation': 'underline_highlight',
            'background': 'dark_semi_transparent'
        }
    }

    def __init__(self, style_name: str = 'modern_purple'):
        self.style = self.CAPTION_STYLES.get(style_name, self.CAPTION_STYLES['modern_purple'])
        self.style_name = style_name

    def create_word_level_srt(self, segments: List[Dict], output_path: str) -> str:
        """
        Create SRT file with word-level timing for highlighting effects
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                subtitle_index = 1

                for segment in segments:
                    words = segment["text"].strip().split()
                    segment_duration = segment["end"] - segment["start"]

                    if not words:
                        continue

                    # Calculate approximate word timing
                    word_duration = segment_duration / len(words)

                    for i, word in enumerate(words):
                        word_start = segment["start"] + (i * word_duration)
                        word_end = word_start + word_duration

                        # Format timestamps
                        start_time = self._format_timestamp(word_start)
                        end_time = self._format_timestamp(word_end)

                        # Create highlighted text based on style
                        highlighted_text = self._create_highlighted_text(words, i)

                        # Write SRT entry
                        f.write(f"{subtitle_index}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{highlighted_text}\n\n")

                        subtitle_index += 1

            logger.info(f"Created word-level SRT with {self.style_name} style: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create word-level SRT: {e}")
            raise

    def _create_highlighted_text(self, words: List[str], highlight_index: int) -> str:
        """
        Create text with the current word highlighted based on selected style
        """
        result_words = []

        for i, word in enumerate(words):
            if i == highlight_index:
                # Highlight current word based on style
                if self.style['animation'] == 'word_highlight':
                    highlighted_word = f'<font color="{self.style["highlight_color"]}">{word}</font>'
                elif self.style['animation'] == 'bounce_highlight':
                    highlighted_word = f'<font color="{self.style["highlight_color"]}" size="+2">{word}</font>'
                elif self.style['animation'] == 'fade_highlight':
                    highlighted_word = f'<font color="{self.style["highlight_color"]}">{word}</font>'
                elif self.style['animation'] == 'scale_highlight':
                    highlighted_word = f'<font color="{self.style["highlight_color"]}" size="+1"><b>{word}</b></font>'
                elif self.style['animation'] == 'underline_highlight':
                    highlighted_word = f'<u><font color="{self.style["highlight_color"]}">{word}</font></u>'
                else:
                    highlighted_word = f'<font color="{self.style["highlight_color"]}">{word}</font>'

                result_words.append(highlighted_word)
            else:
                # Non-highlighted words
                result_words.append(f'<font color="{self.style["primary_color"]}">{word}</font>')

        return " ".join(result_words)

    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def get_ffmpeg_subtitle_filter(self) -> str:
        """
        Generate FFmpeg subtitle filter with style settings
        """
        style_settings = []

        # Font settings
        style_settings.append(f"FontName={self.style['font']}")
        style_settings.append(f"FontSize={self.style['font_size']}")

        # Colors (convert hex to BGR for FFmpeg)
        primary_color = self._hex_to_bgr(self.style['primary_color'])
        if primary_color:
            style_settings.append(f"PrimaryColour={primary_color}")

        # Outline
        if self.style['outline_width'] > 0:
            outline_color = self._hex_to_bgr(self.style['outline_color'])
            if outline_color:
                style_settings.append(f"OutlineColour={outline_color}")
                style_settings.append(f"Outline={self.style['outline_width']}")

        # Position
        if self.style['position'] == 'center':
            style_settings.append("Alignment=2")  # Center
        elif self.style['position'] == 'bottom':
            style_settings.append("Alignment=2")  # Bottom center
            style_settings.append("MarginV=30")

        # Background
        if self.style['background'] == 'black_box':
            style_settings.append("BackColour=&H80000000")
            style_settings.append("BorderStyle=4")
        elif self.style['background'] == 'semi_transparent':
            style_settings.append("BackColour=&H80000000")
            style_settings.append("BorderStyle=3")

        return ",".join(style_settings)

    def _hex_to_bgr(self, hex_color: str) -> Optional[str]:
        """Convert hex color to BGR format for FFmpeg"""
        try:
            if hex_color == 'white':
                return "&HFFFFFF"
            elif hex_color == 'black':
                return "&H000000"
            elif hex_color == 'none':
                return None
            elif hex_color.startswith('#'):
                # Remove # and convert to BGR
                hex_val = hex_color[1:]
                if len(hex_val) == 6:
                    r = int(hex_val[0:2], 16)
                    g = int(hex_val[2:4], 16)
                    b = int(hex_val[4:6], 16)
                    return f"&H{b:02X}{g:02X}{r:02X}"
            return None
        except:
            return None

def create_styled_subtitles(segments: List[Dict], output_path: str, style_name: str = 'modern_purple') -> str:
    """
    Create stylized subtitles with word-by-word highlighting
    """
    style_manager = CaptionStyleManager(style_name)
    return style_manager.create_word_level_srt(segments, output_path)

def get_available_caption_styles() -> Dict[str, Dict]:
    """
    Return all available caption styles
    """
    return CaptionStyleManager.CAPTION_STYLES

# Example usage in your tasks.py
def write_styled_clip_srt(segments: List[Dict], srt_path: str, style: str = 'modern_purple'):
    """
    Enhanced version of write_clip_srt with styling support
    """
    # Clamp negative times and filter out invalid segments
    valid_segments = []
    for seg in segments:
        start = max(0, seg["start"])
        end = max(0, seg["end"])
        if end > start and seg["text"].strip():
            valid_segments.append({
                "start": start,
                "end": end,
                "text": seg["text"].strip()
            })

    if not valid_segments:
        logger.warning(f"No valid segments for styled SRT file: {srt_path}")
        return None

    # Create styled subtitles
    create_styled_subtitles(valid_segments, srt_path, style)

    if not os.path.isfile(srt_path):
        raise FileNotFoundError(f"Styled SRT file not found: {srt_path}")

    return srt_path