"""
Django management command to create sample background videos using FFmpeg
"""
import os
import tempfile
import subprocess
from django.core.management.base import BaseCommand
from django.core.files import File
from ai_influencer.models import BackgroundVideo


class Command(BaseCommand):
    help = 'Create sample background videos for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of sample backgrounds to create (default: 5)'
        )

    def handle(self, *args, **options):
        count = options['count']

        self.stdout.write(
            self.style.SUCCESS(f'Creating {count} sample background videos...')
        )

        # Sample background configurations
        backgrounds = [
            {
                'name': 'Tech Blue Gradient',
                'category': 'tech',
                'description': 'Animated blue gradient perfect for tech content',
                'duration': 10,
                'color1': '#1e3a8a',
                'color2': '#3b82f6',
                'animation': 'gradient'
            },
            {
                'name': 'Business Professional',
                'category': 'business',
                'description': 'Clean corporate background with subtle animation',
                'duration': 15,
                'color1': '#1f2937',
                'color2': '#374151',
                'animation': 'slide'
            },
            {
                'name': 'Gaming Neon',
                'category': 'gaming',
                'description': 'Cyberpunk-style neon background',
                'duration': 8,
                'color1': '#7c3aed',
                'color2': '#ec4899',
                'animation': 'pulse'
            },
            {
                'name': 'Nature Green',
                'category': 'nature',
                'description': 'Calming green gradient with gentle motion',
                'duration': 12,
                'color1': '#065f46',
                'color2': '#10b981',
                'animation': 'wave'
            },
            {
                'name': 'Abstract Orange',
                'category': 'abstract',
                'description': 'Dynamic orange and yellow abstract pattern',
                'duration': 6,
                'color1': '#ea580c',
                'color2': '#fbbf24',
                'animation': 'spiral'
            }
        ]

        created_count = 0

        for i, bg_config in enumerate(backgrounds[:count]):
            self.stdout.write(f"Creating background {i+1}/{count}: {bg_config['name']}")

            try:
                # Create background video
                video_path = self._create_background_video(bg_config)

                if not video_path or not os.path.exists(video_path):
                    self.stdout.write(
                        self.style.ERROR(f"Failed to create video for {bg_config['name']}")
                    )
                    continue

                # Create thumbnail
                thumbnail_path = self._create_thumbnail(video_path)

                # Create database entry
                bg_video = BackgroundVideo(
                    name=bg_config['name'],
                    description=bg_config['description'],
                    category=bg_config['category'],
                    duration=bg_config['duration'],
                    is_loopable=True,
                    is_premium=False,
                    is_active=True
                )

                # Save video file
                with open(video_path, 'rb') as video_file:
                    bg_video.video_file.save(
                        f"{bg_config['name'].lower().replace(' ', '_')}.mp4",
                        File(video_file),
                        save=False
                    )

                # Save thumbnail if created
                if thumbnail_path and os.path.exists(thumbnail_path):
                    with open(thumbnail_path, 'rb') as thumb_file:
                        bg_video.thumbnail.save(
                            f"{bg_config['name'].lower().replace(' ', '_')}_thumb.jpg",
                            File(thumb_file),
                            save=False
                        )

                bg_video.save()

                # Clean up temp files
                if os.path.exists(video_path):
                    os.unlink(video_path)
                if thumbnail_path and os.path.exists(thumbnail_path):
                    os.unlink(thumbnail_path)

                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Created: {bg_config['name']}")
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Failed to create {bg_config['name']}: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Sample background creation completed!\n'
                f'Created: {created_count}/{count} backgrounds\n'
                f'Total backgrounds in database: {BackgroundVideo.objects.count()}'
            )
        )

    def _create_background_video(self, config):
        """Create animated background video using FFmpeg"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                output_path = tmp.name

            duration = config['duration']
            color1 = config['color1']
            color2 = config['color2']
            animation = config['animation']

            # Create different animations based on type
            if animation == 'gradient':
                # Animated gradient
                filter_complex = (
                    f"color=c={color1}:s=1920x1080:d={duration}[base];"
                    f"color=c={color2}:s=1920x1080:d={duration}[overlay];"
                    f"[overlay]geq=r='255*sin(2*PI*T/4)':g='255*sin(2*PI*T/4)':b='255*sin(2*PI*T/4)'[anim];"
                    f"[base][anim]blend=all_mode=overlay:all_opacity=0.5"
                )
            elif animation == 'slide':
                # Sliding color bands
                filter_complex = (
                    f"color=c={color1}:s=1920x1080:d={duration}[base];"
                    f"[base]geq='if(mod(X+T*100,400)<200,255,r(X,Y))':'if(mod(X+T*100,400)<200,255,g(X,Y))':'if(mod(X+T*100,400)<200,255,b(X,Y))'"
                )
            elif animation == 'pulse':
                # Pulsing effect
                filter_complex = (
                    f"color=c={color1}:s=1920x1080:d={duration}[base];"
                    f"[base]geq='r(X,Y)+50*sin(2*PI*T)':'g(X,Y)+50*sin(2*PI*T)':'b(X,Y)+50*sin(2*PI*T)'"
                )
            elif animation == 'wave':
                # Wave pattern
                filter_complex = (
                    f"color=c={color1}:s=1920x1080:d={duration}[base];"
                    f"[base]geq='r(X,Y)+30*sin(X/50+T*2)':'g(X,Y)+30*sin(X/50+T*2)':'b(X,Y)+30*sin(X/50+T*2)'"
                )
            else:  # spiral
                # Spiral pattern
                filter_complex = (
                    f"color=c={color1}:s=1920x1080:d={duration}[base];"
                    f"[base]geq='r(X,Y)+40*sin(sqrt((X-960)*(X-960)+(Y-540)*(Y-540))/30+T*3)':'g(X,Y)+40*sin(sqrt((X-960)*(X-960)+(Y-540)*(Y-540))/30+T*3)':'b(X,Y)+40*sin(sqrt((X-960)*(X-960)+(Y-540)*(Y-540))/30+T*3)'"
                )

            cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', f'color=c={color1}:s=1920x1080:d={duration}',
                '-vf', filter_complex.split(';')[-1],  # Use the last part of filter
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-y',
                output_path
            ]

            # For simple cases, use a simpler command
            if animation == 'gradient':
                cmd = [
                    'ffmpeg',
                    '-f', 'lavfi',
                    '-i', f'color=c={color1}:s=1920x1080:d={duration}',
                    '-f', 'lavfi',
                    '-i', f'color=c={color2}:s=1920x1080:d={duration}',
                    '-filter_complex', f'[0:v][1:v]blend=all_mode=overlay:all_opacity=0.3+0.2*sin(2*PI*t/{duration})',
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '23',
                    '-pix_fmt', 'yuv420p',
                    '-y',
                    output_path
                ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(output_path):
                return output_path
            else:
                self.stdout.write(
                    self.style.WARNING(f"FFmpeg error: {result.stderr}")
                )
                return None

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Video creation error: {e}")
            )
            return None

    def _create_thumbnail(self, video_path):
        """Create thumbnail from video"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                thumbnail_path = tmp.name

            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', '1',
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                thumbnail_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(thumbnail_path):
                return thumbnail_path
            else:
                return None

        except Exception:
            return None