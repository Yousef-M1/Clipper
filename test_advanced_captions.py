#!/usr/bin/env python3
"""
Test script for advanced caption system improvements
"""

import os
import sys
import django
import tempfile
import json

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from clipper.advanced_captions import AdvancedCaptionStyleManager, create_advanced_subtitles

def test_advanced_caption_styles():
    """Test all advanced caption styles with sample data"""

    # Sample transcript segments with word-level timing (similar to Whisper output)
    sample_segments = [
        {
            "start": 0.0,
            "end": 3.5,
            "text": "This is absolutely amazing content",
            "words": [
                {"word": "This", "start": 0.0, "end": 0.3},
                {"word": "is", "start": 0.3, "end": 0.5},
                {"word": "absolutely", "start": 0.5, "end": 1.2},
                {"word": "amazing", "start": 1.2, "end": 1.8},
                {"word": "content", "start": 1.8, "end": 2.3}
            ]
        },
        {
            "start": 3.5,
            "end": 7.0,
            "text": "Let me show you something incredible",
            "words": [
                {"word": "Let", "start": 3.5, "end": 3.7},
                {"word": "me", "start": 3.7, "end": 3.9},
                {"word": "show", "start": 3.9, "end": 4.3},
                {"word": "you", "start": 4.3, "end": 4.5},
                {"word": "something", "start": 4.5, "end": 5.1},
                {"word": "incredible", "start": 5.1, "end": 5.9}
            ]
        },
        {
            "start": 7.0,
            "end": 10.5,
            "text": "The results are perfect and stunning",
            "words": [
                {"word": "The", "start": 7.0, "end": 7.2},
                {"word": "results", "start": 7.2, "end": 7.7},
                {"word": "are", "start": 7.7, "end": 7.9},
                {"word": "perfect", "start": 7.9, "end": 8.4},
                {"word": "and", "start": 8.4, "end": 8.6},
                {"word": "stunning", "start": 8.6, "end": 9.2}
            ]
        }
    ]

    styles_to_test = [
        ('elevate_style', 2),
        ('slide_in_modern', 1),
        ('word_pop', 1),
        ('two_word_flow', 2),
        ('impactful_highlight', 1)
    ]

    print("🎬 Testing Advanced Caption System")
    print("=" * 50)

    for style_name, max_words in styles_to_test:
        print(f"\n🎨 Testing style: {style_name} (max words: {max_words})")

        try:
            # Create temporary output file
            with tempfile.NamedTemporaryFile(suffix='.ass', delete=False) as temp_file:
                output_path = temp_file.name

            # Create advanced subtitles
            result_path = create_advanced_subtitles(
                sample_segments,
                output_path,
                style_name=style_name,
                max_words=max_words,
                enable_effects=True
            )

            # Read and display sample output
            with open(result_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Show style info
            manager = AdvancedCaptionStyleManager(style_name)
            style_info = manager.style

            print(f"   ✅ Style: {style_info['name']}")
            print(f"   📝 Font: {style_info['font']} ({style_info['font_size']}px)")
            print(f"   🎨 Colors: {style_info['primary_color']} / {style_info['highlight_color']}")
            print(f"   🎭 Animation: {style_info['animation']}")
            print(f"   📏 Max words per screen: {max_words}")

            # Count dialogue lines to show organization
            dialogue_lines = [line for line in content.split('\n') if line.startswith('Dialogue:')]
            print(f"   📊 Generated {len(dialogue_lines)} organized subtitle entries")

            # Show sample dialogue line
            if dialogue_lines:
                sample_line = dialogue_lines[0]
                print(f"   💬 Sample: {sample_line[:80]}...")

            # Cleanup
            os.unlink(result_path)
            print(f"   ✅ Successfully created {style_name} subtitles!")

        except Exception as e:
            print(f"   ❌ Error testing {style_name}: {e}")

    print("\n" + "=" * 50)
    print("🌟 Advanced Caption Features:")
    print("   • Organized word display (1-5 words per screen)")
    print("   • Impactful word detection and highlighting")
    print("   • Text reveal and slide-in animations")
    print("   • Dynamic color effects and backgrounds")
    print("   • Word-level timing precision")
    print("   • Multiple visual styles (Quso-inspired)")
    print("   • Special effects for engaging words")

def test_word_organization():
    """Test word organization with different max_words settings"""

    print("\n🔤 Testing Word Organization")
    print("=" * 30)

    # Long sentence to test organization
    long_segment = {
        "start": 0.0,
        "end": 8.0,
        "text": "This is a really long sentence that should be broken down into smaller organized chunks",
        "words": [
            {"word": "This", "start": 0.0, "end": 0.3},
            {"word": "is", "start": 0.3, "end": 0.5},
            {"word": "a", "start": 0.5, "end": 0.6},
            {"word": "really", "start": 0.6, "end": 1.0},
            {"word": "long", "start": 1.0, "end": 1.3},
            {"word": "sentence", "start": 1.3, "end": 1.9},
            {"word": "that", "start": 1.9, "end": 2.1},
            {"word": "should", "start": 2.1, "end": 2.5},
            {"word": "be", "start": 2.5, "end": 2.7},
            {"word": "broken", "start": 2.7, "end": 3.2},
            {"word": "down", "start": 3.2, "end": 3.5},
            {"word": "into", "start": 3.5, "end": 3.8},
            {"word": "smaller", "start": 3.8, "end": 4.3},
            {"word": "organized", "start": 4.3, "end": 4.9},
            {"word": "chunks", "start": 4.9, "end": 5.4}
        ]
    }

    for max_words in [1, 2, 3, 4]:
        print(f"\n📝 Testing with max_words = {max_words}")

        manager = AdvancedCaptionStyleManager('elevate_style')
        organized = manager._organize_words_by_timing([long_segment], max_words)

        print(f"   Original: 15 words in 1 segment")
        print(f"   Organized: {len(organized)} segments with max {max_words} words each")

        for i, seg in enumerate(organized[:3]):  # Show first 3
            print(f"   Segment {i+1}: \"{seg['text']}\" ({seg['start']:.1f}s - {seg['end']:.1f}s)")

def main():
    """Run all caption system tests"""
    print("🚀 Advanced Caption System Test Suite")
    print("=" * 50)

    test_advanced_caption_styles()
    test_word_organization()

    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("\nThe new caption system provides:")
    print("• ✨ Organized word display (no more overflow)")
    print("• 🎨 5 new advanced styles with animations")
    print("• 🎯 Impactful word detection and highlighting")
    print("• 🔄 Customizable word grouping (1-5 words)")
    print("• 🎭 Special effects and color changes")
    print("• 📱 Perfect for social media clips!")

if __name__ == "__main__":
    main()