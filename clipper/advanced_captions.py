import json
import os
import math
from typing import List, Dict, Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)

class AdvancedCaptionStyleManager:
    """
    Advanced caption system with organized word display and Quso-style effects:
    - Elevate style with text reveal
    - Slide-in animations
    - Background changes
    - Single/two word modes
    - Word color changes and highlighting
    - Impactful word highlighting with color circles
    - Customizable color effects
    """

    ADVANCED_STYLES = {
        'elevate_style': {
            'name': 'Elevate Style',
            'font': 'Arial-Bold',
            'font_size': 32,
            'primary_color': 'white',
            'highlight_color': '#00FF88',  # Bright green
            'background_color': 'rgba(0,0,0,0.8)',
            'animation': 'text_reveal',
            'max_words_per_screen': 2,
            'reveal_effect': 'slide_up',
            'highlight_style': 'glow'
        },
        'slide_in_modern': {
            'name': 'Slide In Modern',
            'font': 'Helvetica-Bold',
            'font_size': 28,
            'primary_color': 'white',
            'highlight_color': '#FF6B35',  # Orange
            'background_color': 'linear-gradient(45deg, #667eea, #764ba2)',
            'animation': 'slide_in',
            'max_words_per_screen': 1,
            'slide_direction': 'left',
            'highlight_style': 'circle'
        },
        'word_pop': {
            'name': 'Word Pop',
            'font': 'Impact',
            'font_size': 36,
            'primary_color': 'white',
            'highlight_color': '#FF1744',  # Red
            'background_color': 'dynamic',  # Changes color
            'animation': 'scale_pop',
            'max_words_per_screen': 1,
            'scale_factor': 1.5,
            'highlight_style': 'outline_glow'
        },
        'two_word_flow': {
            'name': 'Two Word Flow',
            'font': 'Roboto-Bold',
            'font_size': 30,
            'primary_color': 'white',
            'highlight_color': '#9C27B0',  # Purple
            'background_color': 'rgba(25,25,25,0.9)',
            'animation': 'fade_reveal',
            'max_words_per_screen': 2,
            'word_spacing': 'wide',
            'highlight_style': 'underline_grow'
        },
        'impactful_highlight': {
            'name': 'Impactful Highlight',
            'font': 'Arial-Black',
            'font_size': 34,
            'primary_color': 'white',
            'highlight_color': '#FFD700',  # Gold
            'background_color': 'smart_blur',  # Blurs background
            'animation': 'impact_zoom',
            'max_words_per_screen': 1,
            'impact_words': ['amazing', 'incredible', 'wow', 'perfect', 'love', 'best'],
            'highlight_style': 'circle_burst',
            'special_effects': True
        }
    }

    # Color schemes for dynamic backgrounds
    COLOR_SCHEMES = [
        ['#FF6B6B', '#4ECDC4', '#45B7D1'],  # Red, Teal, Blue
        ['#96CEB4', '#FFEAA7', '#DDA0DD'],  # Green, Yellow, Purple
        ['#FF9FF3', '#54A0FF', '#5F27CD'],  # Pink, Blue, Purple
        ['#FFA726', '#66BB6A', '#EF5350'],  # Orange, Green, Red
        ['#42A5F5', '#AB47BC', '#FF7043']   # Blue, Purple, Orange
    ]

    # Impactful words that get special treatment
    IMPACT_WORDS = [
        'amazing', 'incredible', 'wow', 'perfect', 'love', 'best', 'awesome',
        'fantastic', 'brilliant', 'outstanding', 'phenomenal', 'spectacular',
        'magnificent', 'extraordinary', 'unbelievable', 'stunning', 'gorgeous',
        'beautiful', 'wonderful', 'excellent', 'superb', 'marvelous', 'great'
    ]

    def __init__(self, style_name: str = 'elevate_style'):
        self.style = self.ADVANCED_STYLES.get(style_name, self.ADVANCED_STYLES['elevate_style'])
        self.style_name = style_name
        self.current_color_index = 0

    def create_organized_subtitles(self, segments: List[Dict], output_path: str,
                                 max_words: int = None, enable_special_effects: bool = True) -> str:
        """
        Create organized subtitles with proper word grouping and advanced effects
        """
        try:
            max_words = max_words or self.style.get('max_words_per_screen', 2)

            # Process segments to create organized word groups
            organized_segments = self._organize_words_by_timing(segments, max_words)

            # Create ASS file with advanced styling
            ass_output_path = output_path.replace('.srt', '.ass')

            with open(ass_output_path, 'w', encoding='utf-8') as f:
                self._write_ass_header(f)
                self._write_ass_styles(f)

                f.write("[Events]\n")
                f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

                for segment in organized_segments:
                    text = segment["text"]
                    if not text.strip():
                        continue

                    start_time = self._format_ass_timestamp(segment["start"])
                    end_time = self._format_ass_timestamp(segment["end"])

                    # Apply advanced styling based on content
                    styled_text = self._apply_advanced_styling(
                        text,
                        segment.get("is_impactful", False),
                        enable_special_effects
                    )

                    # Add animation effects
                    effect = self._get_animation_effect(segment)

                    f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,{effect},{styled_text}\n")

            logger.info(f"Created advanced ASS subtitle file: {ass_output_path}")
            return ass_output_path

        except Exception as e:
            logger.error(f"Failed to create organized subtitles: {e}")
            raise

    def _organize_words_by_timing(self, segments: List[Dict], max_words: int) -> List[Dict]:
        """
        Organize words into properly timed groups based on max_words setting
        """
        organized = []

        for segment in segments:
            if "words" not in segment or not segment["words"]:
                # Fallback: split text manually if no word timing
                words = segment["text"].strip().split()
                word_groups = [words[i:i+max_words] for i in range(0, len(words), max_words)]

                segment_duration = segment["end"] - segment["start"]
                time_per_group = segment_duration / len(word_groups)

                for i, group in enumerate(word_groups):
                    group_start = segment["start"] + (i * time_per_group)
                    group_end = group_start + time_per_group

                    organized.append({
                        "start": group_start,
                        "end": group_end,
                        "text": " ".join(group),
                        "is_impactful": any(word.lower() in self.IMPACT_WORDS for word in group)
                    })
            else:
                # Use real word timing data
                words_data = segment["words"]
                word_groups = [words_data[i:i+max_words] for i in range(0, len(words_data), max_words)]

                for group in word_groups:
                    if not group:
                        continue

                    group_start = group[0]["start"]
                    group_end = group[-1]["end"]
                    group_text = " ".join([w["word"].strip() for w in group])

                    # Ensure minimum display time and prevent overlaps
                    min_display_time = 1.2  # Increased for better readability
                    if group_end - group_start < min_display_time:
                        group_end = group_start + min_display_time

                    # Add gap between subtitle groups to prevent overlap
                    if organized:
                        last_end = organized[-1]["end"]
                        if group_start < last_end + 0.3:  # 0.3 second gap
                            group_start = last_end + 0.3
                            group_end = group_start + min_display_time

                    # Check for impactful words
                    is_impactful = any(word["word"].lower().strip() in self.IMPACT_WORDS for word in group)

                    organized.append({
                        "start": group_start,
                        "end": group_end,
                        "text": group_text,
                        "is_impactful": is_impactful,
                        "words": group
                    })

        return organized

    def _apply_advanced_styling(self, text: str, is_impactful: bool, enable_effects: bool) -> str:
        """
        Apply advanced styling effects to text
        """
        if not enable_effects:
            return text

        # Check style-specific formatting
        if self.style_name == 'elevate_style':
            return self._apply_elevate_style(text, is_impactful)
        elif self.style_name == 'slide_in_modern':
            return self._apply_slide_in_style(text, is_impactful)
        elif self.style_name == 'word_pop':
            return self._apply_word_pop_style(text, is_impactful)
        elif self.style_name == 'two_word_flow':
            return self._apply_two_word_flow_style(text, is_impactful)
        elif self.style_name == 'impactful_highlight':
            return self._apply_impactful_highlight_style(text, is_impactful)
        else:
            return text

    def _apply_elevate_style(self, text: str, is_impactful: bool) -> str:
        """Elevate style with text reveal and glow effect"""
        if is_impactful:
            # Bright green with strong black outline for visibility
            return f'{{\\c&H00FF88&\\bord4\\shad2}}{text}'
        else:
            # Clean white text with strong black outline
            return f'{{\\c&HFFFFFF&\\bord3\\shad2}}{text}'

    def _apply_slide_in_style(self, text: str, is_impactful: bool) -> str:
        """Slide in modern with circle highlight"""
        if is_impactful:
            # Orange circle background effect
            return f'{{\\c&HFFFFFF&\\4c&HFF6B35&\\4a&H00&\\bord4}}{text}'
        else:
            return f'{{\\c&HFFFFFF&\\bord2}}{text}'

    def _apply_word_pop_style(self, text: str, is_impactful: bool) -> str:
        """Word pop with scaling and outline glow"""
        if is_impactful:
            # Scale up with red glow
            return f'{{\\fscx150\\fscy150\\c&HFFFFFF&\\3c&H1744FF&\\3a&H00&\\blur2\\bord3}}{text}'
        else:
            return f'{{\\c&HFFFFFF&\\bord2}}{text}'

    def _apply_two_word_flow_style(self, text: str, is_impactful: bool) -> str:
        """Two word flow with underline effects"""
        if is_impactful:
            # Purple underline that grows
            return f'{{\\c&H9C27B0&\\u1\\bord2}}{text}'
        else:
            return f'{{\\c&HFFFFFF&\\bord1}}{text}'

    def _apply_impactful_highlight_style(self, text: str, is_impactful: bool) -> str:
        """Impactful highlighting with circle burst effect"""
        if is_impactful:
            # Gold with circle burst (multiple border layers)
            return f'{{\\c&H00D7FF&\\3c&H00D7FF&\\4c&H00D7FF&\\3a&H40&\\4a&H40&\\blur2\\bord5}}{text}'
        else:
            return f'{{\\c&HFFFFFF&\\bord2}}{text}'

    def _get_animation_effect(self, segment: Dict) -> str:
        """
        Get animation effect string for ASS
        """
        animation = self.style.get('animation', '')

        if animation == 'text_reveal':
            return "Scroll up;y1:50;y2:0"
        elif animation == 'slide_in':
            direction = self.style.get('slide_direction', 'left')
            if direction == 'left':
                return "Scroll;x1:-50;x2:0"
            else:
                return "Scroll;x1:50;x2:0"
        elif animation == 'scale_pop':
            return "!"  # ASS effect for pop/scale
        elif animation == 'fade_reveal':
            return "Fad;150;150"
        elif animation == 'impact_zoom':
            return "Scroll up;y1:30;y2:0"

        return ""

    def _write_ass_header(self, f):
        """Write ASS file header"""
        f.write("[Script Info]\n")
        f.write("Title: Advanced Captions by Video Clipper\n")
        f.write("ScriptType: v4.00+\n")
        f.write("PlayDepth: 0\n")
        f.write("ScaledBorderAndShadow: yes\n\n")

    def _write_ass_styles(self, f):
        """Write ASS styles section"""
        f.write("[V4+ Styles]\n")
        f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")

        # Main style
        font_name = self.style['font'].replace('-Bold', '').replace('-Black', '')
        font_size = self.style['font_size']
        bold = 1 if 'Bold' in self.style['font'] or 'Black' in self.style['font'] else 0

        # Use large, visible font size and proper positioning
        visible_font_size = max(42, font_size)  # Ensure large, visible font
        f.write(f"Style: Default,{font_name},{visible_font_size},&HFFFFFF,&HFFFFFF,&H000000,&H80000000,{bold},0,0,0,100,100,0,0,1,4,2,2,20,20,25,1\n\n")

    def _format_ass_timestamp(self, seconds: float) -> str:
        """Convert seconds to ASS timestamp format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

    def create_background_effects(self, video_path: str, output_path: str, effect_type: str = 'blur') -> str:
        """
        Create background effects for enhanced visual appeal
        """
        effects = {
            'blur': 'boxblur=10:10',
            'dark_overlay': 'colorkey=0x000000:0.3:0.1,fade=t=in:st=0:d=0.5:alpha=1',
            'color_shift': 'hue=H=0.5*t',
            'zoom_blur': 'scale=1.1*iw:1.1*ih,boxblur=5:5'
        }

        if effect_type not in effects:
            return video_path

        # This would integrate with your existing FFmpeg pipeline
        # For now, return the original path
        return video_path

    def get_color_for_frame(self, frame_index: int) -> str:
        """
        Get dynamic color for frame-based background changes
        """
        scheme = self.COLOR_SCHEMES[self.current_color_index % len(self.COLOR_SCHEMES)]
        color = scheme[frame_index % len(scheme)]
        return color

def create_advanced_subtitles(segments: List[Dict], output_path: str,
                            style_name: str = 'elevate_style',
                            max_words: int = 2,
                            enable_effects: bool = True) -> str:
    """
    Create advanced organized subtitles with Quso-style effects
    """
    manager = AdvancedCaptionStyleManager(style_name)
    return manager.create_organized_subtitles(segments, output_path, max_words, enable_effects)

def get_available_advanced_styles() -> Dict[str, Dict]:
    """
    Return all available advanced caption styles
    """
    return AdvancedCaptionStyleManager.ADVANCED_STYLES