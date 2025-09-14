"""
Video format utilities for different social media platforms and aspect ratios
"""

import logging
logger = logging.getLogger(__name__)


class VideoFormatManager:
    """Manage video format presets and conversions"""

    # Platform-specific presets with optimal dimensions
    PLATFORM_PRESETS = {
        'youtube': {
            'name': 'YouTube',
            'aspect_ratio': '16:9',
            'recommended_dimensions': [(1920, 1080), (1280, 720), (854, 480)],
            'max_duration': 60,  # seconds for shorts, unlimited for regular
            'description': 'Horizontal format perfect for YouTube videos and shorts'
        },
        'tiktok': {
            'name': 'TikTok',
            'aspect_ratio': '9:16',
            'recommended_dimensions': [(1080, 1920), (720, 1280)],
            'max_duration': 60,
            'description': 'Vertical format optimized for TikTok content'
        },
        'instagram_story': {
            'name': 'Instagram Story',
            'aspect_ratio': '9:16',
            'recommended_dimensions': [(1080, 1920), (720, 1280)],
            'max_duration': 60,
            'description': 'Vertical format for Instagram Stories'
        },
        'instagram_post': {
            'name': 'Instagram Post',
            'aspect_ratio': '1:1',
            'recommended_dimensions': [(1080, 1080), (720, 720)],
            'max_duration': 60,
            'description': 'Square format for Instagram feed posts'
        },
        'instagram_reel': {
            'name': 'Instagram Reel',
            'aspect_ratio': '9:16',
            'recommended_dimensions': [(1080, 1920), (720, 1280)],
            'max_duration': 90,
            'description': 'Vertical format for Instagram Reels'
        },
        'facebook_post': {
            'name': 'Facebook Post',
            'aspect_ratio': '16:9',
            'recommended_dimensions': [(1280, 720), (1920, 1080)],
            'max_duration': 240,
            'description': 'Horizontal format for Facebook video posts'
        },
        'twitter': {
            'name': 'Twitter/X',
            'aspect_ratio': '16:9',
            'recommended_dimensions': [(1280, 720), (1920, 1080)],
            'max_duration': 140,
            'description': 'Horizontal format for Twitter/X videos'
        },
        'linkedin': {
            'name': 'LinkedIn',
            'aspect_ratio': '16:9',
            'recommended_dimensions': [(1280, 720), (1920, 1080)],
            'max_duration': 600,
            'description': 'Professional horizontal format for LinkedIn'
        }
    }

    # Aspect ratio to dimensions mapping
    ASPECT_RATIOS = {
        'horizontal': {
            'ratio': '16:9',
            'dimensions': [(1920, 1080), (1280, 720), (854, 480)],
            'description': 'Standard horizontal format (16:9)'
        },
        'vertical': {
            'ratio': '9:16',
            'dimensions': [(1080, 1920), (720, 1280), (480, 854)],
            'description': 'Vertical format perfect for mobile (9:16)'
        },
        'square': {
            'ratio': '1:1',
            'dimensions': [(1080, 1080), (720, 720), (480, 480)],
            'description': 'Square format for social posts (1:1)'
        }
    }

    @classmethod
    def get_platform_preset(cls, platform):
        """Get preset configuration for a social media platform"""
        return cls.PLATFORM_PRESETS.get(platform)

    @classmethod
    def get_dimensions_for_quality(cls, format_type, quality='720p'):
        """Get optimal dimensions based on format and quality"""
        quality_map = {
            '480p': 0,  # Index for lower quality
            '720p': 1,  # Index for medium quality
            '1080p': 0, # Index for high quality
            '1440p': 0,
            '2160p': 0
        }

        if format_type == 'custom':
            return None

        # Get aspect ratio info
        aspect_info = cls.ASPECT_RATIOS.get(format_type)
        if not aspect_info:
            return None

        # Select dimension based on quality
        dimensions = aspect_info['dimensions']
        quality_index = quality_map.get(quality, 1)

        if quality_index < len(dimensions):
            return dimensions[quality_index]

        return dimensions[0]  # Default to highest quality

    @classmethod
    def calculate_aspect_ratio(cls, width, height):
        """Calculate aspect ratio from width and height"""
        if not width or not height:
            return None

        # Find GCD to simplify ratio
        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a

        ratio_gcd = gcd(width, height)
        ratio_w = width // ratio_gcd
        ratio_h = height // ratio_gcd

        return f"{ratio_w}:{ratio_h}"

    @classmethod
    def get_ffmpeg_scale_filter(cls, output_format, custom_width=None, custom_height=None, quality='720p'):
        """Generate FFmpeg scale filter for the specified format"""

        if output_format == 'custom' and custom_width and custom_height:
            return f"scale={custom_width}:{custom_height}"

        # Get optimal dimensions
        dimensions = cls.get_dimensions_for_quality(output_format, quality)
        if not dimensions:
            return "scale=1280:720"  # Default fallback

        width, height = dimensions
        return f"scale={width}:{height}"

    @classmethod
    def get_crop_filter(cls, output_format, input_width, input_height):
        """Generate FFmpeg crop filter to maintain aspect ratio"""

        aspect_ratios = {
            'horizontal': 16/9,
            'vertical': 9/16,
            'square': 1/1
        }

        target_ratio = aspect_ratios.get(output_format)
        if not target_ratio:
            return ""

        input_ratio = input_width / input_height

        if abs(input_ratio - target_ratio) < 0.01:  # Already correct ratio
            return ""

        if input_ratio > target_ratio:
            # Input is wider, crop width
            new_width = int(input_height * target_ratio)
            x_offset = (input_width - new_width) // 2
            return f"crop={new_width}:{input_height}:{x_offset}:0"
        else:
            # Input is taller, crop height
            new_height = int(input_width / target_ratio)
            y_offset = (input_height - new_height) // 2
            return f"crop={input_width}:{new_height}:0:{y_offset}"

    @classmethod
    def get_all_platform_presets(cls):
        """Get all available platform presets"""
        return {
            platform: {
                'name': data['name'],
                'aspect_ratio': data['aspect_ratio'],
                'max_duration': data['max_duration'],
                'description': data['description'],
                'recommended_width': data['recommended_dimensions'][0][0],
                'recommended_height': data['recommended_dimensions'][0][1]
            }
            for platform, data in cls.PLATFORM_PRESETS.items()
        }

    @classmethod
    def get_format_options(cls):
        """Get all format options for API responses"""
        return {
            'aspect_ratios': {
                format_type: {
                    'ratio': data['ratio'],
                    'description': data['description'],
                    'width': data['dimensions'][0][0],
                    'height': data['dimensions'][0][1]
                }
                for format_type, data in cls.ASPECT_RATIOS.items()
            },
            'platforms': cls.get_all_platform_presets()
        }


def get_available_video_formats():
    """API function to get all available video formats"""
    return VideoFormatManager.get_format_options()


def get_available_platforms():
    """API function to get all social media platform presets"""
    return VideoFormatManager.get_all_platform_presets()


def validate_custom_dimensions(width, height):
    """Validate custom dimensions"""
    if not isinstance(width, int) or not isinstance(height, int):
        return False, "Width and height must be integers"

    if width < 240 or height < 240:
        return False, "Minimum dimensions are 240x240"

    if width > 4096 or height > 4096:
        return False, "Maximum dimensions are 4096x4096"

    return True, "Valid dimensions"