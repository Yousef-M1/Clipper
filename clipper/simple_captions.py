"""
Simple, reliable caption system that creates clearly visible subtitles
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def create_simple_visible_subtitles(segments: List[Dict], output_path: str, max_words: int = 2, style: str = 'modern_purple', output_format: str = 'horizontal') -> str:
    """
    Create simple, highly visible subtitles that definitely work
    """
    try:
        # DEBUG: Log what segments we're working with
        logger.info(f"Processing {len(segments)} segments for subtitles")
        for i, seg in enumerate(segments[:3]):  # Log first 3 segments
            logger.info(f"  Segment {i+1}: {seg['start']:.1f}-{seg['end']:.1f}s -> '{seg['text'][:50]}'")
            if 'words' in seg:
                logger.info(f"    Has {len(seg['words'])} words")
        # Create ASS output path
        ass_output_path = output_path.replace('.srt', '.ass')

        with open(ass_output_path, 'w', encoding='utf-8') as f:
            # Write ASS header
            f.write("[Script Info]\n")
            f.write("Title: Simple Visible Captions\n")
            f.write("ScriptType: v4.00+\n")
            f.write("PlayDepth: 0\n")
            f.write("ScaledBorderAndShadow: yes\n\n")

            # Write style based on output format and style
            f.write("[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")

            # Adjust font size based on format
            if output_format == 'vertical':
                font_size = 18  # Smaller for vertical videos
            else:
                font_size = 24  # Standard for horizontal

            # White text with black border, bottom center alignment (alignment=2)
            # Use consistent margins and positioning to prevent line stacking
            f.write(f"Style: Default,Arial,{font_size},&HFFFFFF,&HFFFFFF,&H000000,&H000000,1,0,0,0,100,100,0,0,1,3,2,2,0,0,30,1\n")
            # Style for highlighted words (purple) - same exact positioning
            f.write(f"Style: Highlight,Arial,{font_size},&HF65C8B,&HF65C8B,&H000000,&H000000,1,0,0,0,100,100,0,0,1,3,2,2,0,0,30,1\n\n")

            # Write events
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

            # Use segment-level subtitles with optional purple highlighting
            for segment in segments:
                text = segment["text"].strip()
                if not text:
                    continue

                start_time = format_ass_timestamp(segment["start"])
                end_time = format_ass_timestamp(segment["end"])

                # Add purple highlighting if modern_purple style and word data exists
                if style == 'modern_purple' and "words" in segment and segment["words"]:
                    highlighted_text = create_simple_purple_highlight(segment, max_words)
                    f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,30,,{highlighted_text}\n")
                else:
                    # Simple white text with consistent positioning
                    f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,30,,{text}\n")

        logger.info(f"Created simple visible ASS subtitle file: {ass_output_path}")
        return ass_output_path

    except Exception as e:
        logger.error(f"Failed to create simple subtitles: {e}")
        # Fallback to SRT format
        return create_simple_srt_subtitles(segments, output_path, max_words)

def create_simple_srt_subtitles(segments: List[Dict], output_path: str, max_words: int = 2) -> str:
    """
    Create simple SRT subtitles as fallback
    """
    try:
        srt_output_path = output_path.replace('.ass', '.srt')

        with open(srt_output_path, 'w', encoding='utf-8') as f:
            organized = organize_words_for_visibility(segments, max_words)

            for i, segment in enumerate(organized):
                text = segment["text"].strip()
                if not text:
                    continue

                start_time = format_srt_timestamp(segment["start"])
                end_time = format_srt_timestamp(segment["end"])

                f.write(f"{i + 1}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")

        logger.info(f"Created simple SRT subtitle file: {srt_output_path}")
        return srt_output_path

    except Exception as e:
        logger.error(f"Failed to create SRT subtitles: {e}")
        raise

def organize_words_for_visibility(segments: List[Dict], max_words: int) -> List[Dict]:
    """
    Organize words into readable groups with proper timing
    """
    organized = []

    for segment in segments:
        if "words" not in segment or not segment["words"]:
            # Fallback: split text manually
            words = segment["text"].strip().split()
            word_groups = [words[i:i+max_words] for i in range(0, len(words), max_words)]

            segment_duration = segment["end"] - segment["start"]
            time_per_group = segment_duration / len(word_groups)

            for i, group in enumerate(word_groups):
                if not group:
                    continue

                group_start = segment["start"] + (i * time_per_group)
                group_end = group_start + time_per_group  # Use natural timing

                organized.append({
                    "start": group_start,
                    "end": group_end,
                    "text": " ".join(group).upper()  # ALL CAPS for visibility
                })
        else:
            # Use word timing data
            words_data = segment["words"]
            word_groups = [words_data[i:i+max_words] for i in range(0, len(words_data), max_words)]

            for group in word_groups:
                if not group:
                    continue

                group_start = group[0]["start"]
                group_end = group[-1]["end"]
                group_text = " ".join([w["word"].strip() for w in group])

                # PRESERVE ORIGINAL TIMING - don't modify transcript timing!
                # The transcript already has perfect timing from Whisper
                # Don't add artificial delays or minimum times

                organized.append({
                    "start": group_start,
                    "end": group_end,
                    "text": group_text.upper()  # ALL CAPS for visibility
                })

    return organized

def create_simple_purple_highlight(segment, max_words: int) -> str:
    """
    Create simple purple highlighting within a single segment - no duplicates
    Uses ASS karaoke timing with proper color transitions
    """
    words_data = segment["words"]

    # Use ALL words - don't limit to max_words to prevent missing text
    karaoke_parts = []

    for i, word_data in enumerate(words_data):
        word = word_data["word"].strip()
        if not word:
            continue

        # Calculate accurate timing in centiseconds for ASS karaoke
        word_duration = word_data["end"] - word_data["start"]
        # Use more accurate timing - remove minimum to match audio better
        centiseconds = max(20, int(word_duration * 100))  # Reduced minimum for faster timing

        # ASS karaoke with proper color transition
        # First set all text to white, then highlight current word purple
        if i == 0:
            # First word: start white, turn purple
            karaoke_part = f"{{\\c&HFFFFFF&}}{{\\k{centiseconds}\\c&HF65C8B&}}{word}"
        else:
            # Other words: previous word becomes white, current becomes purple
            karaoke_part = f"{{\\k{centiseconds}\\c&HF65C8B&}}{word}"

        karaoke_parts.append(karaoke_part)

    # Final reset to white for all remaining text
    return " ".join(karaoke_parts) + "{\\c&HFFFFFF&}"

def create_word_highlighted_subtitles(file_handle, segments: List[Dict], max_words: int):
    """
    Create word-level highlighted subtitles with purple highlighting (single phrase approach)
    """
    for segment in segments:
        if "words" not in segment or not segment["words"]:
            # Fallback to simple display
            text = segment["text"].strip()
            if text:
                start_time = format_ass_timestamp(segment["start"])
                end_time = format_ass_timestamp(segment["end"])
                file_handle.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,30,,{text}\n")
            continue

        words_data = segment["words"]

        # Group words by max_words
        word_groups = [words_data[i:i+max_words] for i in range(0, len(words_data), max_words)]

        for group in word_groups:
            if not group:
                continue

            all_words = [w["word"].strip() for w in group]
            group_start = group[0]["start"]
            group_end = group[-1]["end"]

            # Create a SINGLE subtitle entry for the entire phrase duration
            # This will show the complete phrase the whole time with karaoke-style highlighting
            start_time = format_ass_timestamp(group_start)
            end_time = format_ass_timestamp(group_end)

            # Create karaoke-style timing for word highlighting
            karaoke_text = create_karaoke_phrase(group)

            # Use Layer 0 and fixed positioning to ensure all subtitles appear in exact same location
            # MarginL=0, MarginR=0, MarginV=30 ensures consistent bottom positioning
            file_handle.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,30,,{karaoke_text}\n")

def create_karaoke_phrase(word_group) -> str:
    """
    Create karaoke-style ASS phrase with timing-based purple highlighting
    """
    karaoke_parts = []

    for i, word_data in enumerate(word_group):
        word = word_data["word"].strip()
        if not word:
            continue

        # Calculate timing in centiseconds (ASS karaoke format)
        word_duration = word_data["end"] - word_data["start"]
        centiseconds = int(word_duration * 100)

        # Add karaoke timing with purple highlighting
        # {\k} = karaoke timing, {\c} = color change
        karaoke_part = f"{{\\k{centiseconds}\\c&HF65C8B&}}{word}{{\\c&HFFFFFF&}}"
        karaoke_parts.append(karaoke_part)

    return " ".join(karaoke_parts)

def create_highlighted_phrase(words: List[str], highlight_index: int) -> str:
    """
    Create phrase with one word highlighted in purple (legacy function)
    """
    result_words = []

    for i, word in enumerate(words):
        if i == highlight_index:
            # Highlight current word in purple using ASS color tags
            highlighted_word = f'{{\\c&HF65C8B&\\b1}}{word}{{\\c&HFFFFFF&\\b0}}'
            result_words.append(highlighted_word)
        else:
            # Normal white words
            result_words.append(word)

    return " ".join(result_words)

def format_ass_timestamp(seconds: float) -> str:
    """Convert seconds to ASS timestamp format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

def format_srt_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"