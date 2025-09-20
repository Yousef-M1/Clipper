"""
Django management command to create built-in content generation templates
"""

from django.core.management.base import BaseCommand
from content_generation.models import ContentTemplate


class Command(BaseCommand):
    help = 'Create built-in content generation templates'

    def handle(self, *args, **options):
        templates = [
            # Blog Post Templates
            {
                'name': 'SEO Blog Post',
                'description': 'SEO-optimized blog post with keywords and structure',
                'template_type': 'blog_post',
                'platform': 'general',
                'prompt_template': '''
You are an expert SEO content writer. Transform this video transcript into a comprehensive, SEO-optimized blog post.

VIDEO TITLE: {video_title}
TARGET KEYWORDS: {target_keywords}
TARGET AUDIENCE: {target_audience}
BRAND VOICE: {brand_voice}

TRANSCRIPT:
{transcript}

REQUIREMENTS:
1. Create an engaging, SEO-optimized blog post
2. Use proper heading structure (H1, H2, H3)
3. Include bullet points and numbered lists
4. Make it scannable with short paragraphs
5. Include compelling introduction and conclusion
6. Naturally incorporate target keywords
7. Add value beyond just transcribing

OUTPUT AS JSON:
{{
    "title": "Main blog post title",
    "meta_title": "SEO meta title (max 60 chars)",
    "meta_description": "SEO meta description (max 160 chars)",
    "content": "Full blog post content in Markdown",
    "keywords": ["extracted", "keywords"],
    "headings": [{{"level": "h2", "text": "Section Title"}}]
}}
                ''',
                'output_structure': {
                    'title': 'string',
                    'meta_title': 'string',
                    'meta_description': 'string',
                    'content': 'markdown',
                    'keywords': 'array',
                    'headings': 'array'
                },
                'max_words': 1500,
                'min_words': 800,
                'tone': 'professional',
                'style': 'informative',
                'include_seo_meta': True,
                'include_headings': True,
                'include_bullet_points': True
            },

            # Show Notes Templates
            {
                'name': 'Podcast Show Notes',
                'description': 'Comprehensive show notes for podcasts with timestamps',
                'template_type': 'show_notes',
                'platform': 'general',
                'prompt_template': '''
You are an expert podcast producer creating comprehensive show notes.

EPISODE: {episode_number} - {video_title}
HOST: {host_name}
GUEST: {guest_name}

TRANSCRIPT:
{transcript}

OUTPUT AS JSON:
{{
    "title": "Episode title",
    "summary": "2-3 sentence episode summary",
    "content": "Full show notes in Markdown",
    "key_takeaways": ["takeaway 1", "takeaway 2"],
    "timestamps": [{{"time": "00:05", "description": "Topic discussed"}}],
    "guests": ["Guest Name with brief bio"],
    "resources": ["Resource 1: URL"]
}}
                ''',
                'output_structure': {
                    'title': 'string',
                    'summary': 'string',
                    'content': 'markdown',
                    'key_takeaways': 'array',
                    'timestamps': 'array',
                    'guests': 'array',
                    'resources': 'array'
                },
                'max_words': 1000,
                'min_words': 300,
                'tone': 'conversational',
                'style': 'informative'
            },

            # Social Media Templates
            {
                'name': 'Twitter Thread',
                'description': 'Engaging Twitter thread from video content',
                'template_type': 'social_media',
                'platform': 'twitter',
                'prompt_template': '''
Create an engaging Twitter thread from this video content.

VIDEO: {video_title}
BRAND VOICE: {brand_voice}

TRANSCRIPT:
{transcript}

REQUIREMENTS:
- Each tweet max 280 characters
- Create 5-8 connected tweets
- Include relevant hashtags
- Add call-to-action

OUTPUT AS JSON:
{{
    "posts": ["Tweet 1", "Tweet 2", "Tweet 3"],
    "hashtags": ["hashtag1", "hashtag2"],
    "call_to_action": "Watch the full video!"
}}
                ''',
                'output_structure': {
                    'posts': 'array',
                    'hashtags': 'array',
                    'call_to_action': 'string'
                },
                'max_words': 200,
                'min_words': 50,
                'tone': 'engaging',
                'style': 'conversational'
            },

            {
                'name': 'LinkedIn Post',
                'description': 'Professional LinkedIn post with insights',
                'template_type': 'social_media',
                'platform': 'linkedin',
                'prompt_template': '''
Create a professional LinkedIn post from this video content.

VIDEO: {video_title}
TARGET AUDIENCE: {target_audience}

TRANSCRIPT:
{transcript}

REQUIREMENTS:
- Professional tone
- Include key insights
- Add relevant hashtags
- Call-to-action for engagement

OUTPUT AS JSON:
{{
    "posts": ["LinkedIn post content"],
    "hashtags": ["hashtag1", "hashtag2"],
    "call_to_action": "What's your experience with this?"
}}
                ''',
                'output_structure': {
                    'posts': 'array',
                    'hashtags': 'array',
                    'call_to_action': 'string'
                },
                'max_words': 500,
                'min_words': 100,
                'tone': 'professional',
                'style': 'insightful'
            },

            # YouTube Description
            {
                'name': 'YouTube Description',
                'description': 'SEO-optimized YouTube video description',
                'template_type': 'video_description',
                'platform': 'youtube',
                'prompt_template': '''
Create an SEO-optimized YouTube description from this video content.

VIDEO TITLE: {video_title}
TARGET KEYWORDS: {target_keywords}

TRANSCRIPT:
{transcript}

REQUIREMENTS:
- Compelling description (first 125 chars)
- Include timestamps for key topics
- Add relevant hashtags
- Include call-to-actions

OUTPUT AS JSON:
{{
    "title": "Optimized video title",
    "content": "Full description with timestamps",
    "keywords": ["keyword1", "keyword2"],
    "hashtags": ["#hashtag1", "#hashtag2"]
}}
                ''',
                'output_structure': {
                    'title': 'string',
                    'content': 'string',
                    'keywords': 'array',
                    'hashtags': 'array'
                },
                'max_words': 800,
                'min_words': 200,
                'tone': 'engaging',
                'style': 'descriptive',
                'include_seo_meta': True
            },

            # Email Newsletter
            {
                'name': 'Email Newsletter',
                'description': 'Email newsletter content from video insights',
                'template_type': 'email_newsletter',
                'platform': 'general',
                'prompt_template': '''
Create email newsletter content from this video.

VIDEO: {video_title}
BRAND VOICE: {brand_voice}
TARGET AUDIENCE: {target_audience}

TRANSCRIPT:
{transcript}

REQUIREMENTS:
- Engaging subject line
- Scannable content with sections
- Key takeaways highlighted
- Clear call-to-action

OUTPUT AS JSON:
{{
    "subject": "Email subject line",
    "content": "Newsletter content in HTML/Markdown",
    "key_takeaways": ["takeaway 1", "takeaway 2"],
    "call_to_action": "Watch the full video"
}}
                ''',
                'output_structure': {
                    'subject': 'string',
                    'content': 'html',
                    'key_takeaways': 'array',
                    'call_to_action': 'string'
                },
                'max_words': 600,
                'min_words': 200,
                'tone': 'friendly',
                'style': 'conversational'
            },

            # Key Takeaways
            {
                'name': 'Key Takeaways',
                'description': 'Extract key insights and takeaways',
                'template_type': 'key_takeaways',
                'platform': 'general',
                'prompt_template': '''
Extract the most important takeaways from this video.

VIDEO: {video_title}

TRANSCRIPT:
{transcript}

REQUIREMENTS:
- 5-10 key takeaways
- Each takeaway should be actionable
- Include brief explanations
- Prioritize by importance

OUTPUT AS JSON:
{{
    "title": "Key Takeaways",
    "takeaways": [
        {{"point": "Main takeaway", "explanation": "Brief explanation"}},
        {{"point": "Second takeaway", "explanation": "Brief explanation"}}
    ],
    "summary": "One paragraph summary"
}}
                ''',
                'output_structure': {
                    'title': 'string',
                    'takeaways': 'array',
                    'summary': 'string'
                },
                'max_words': 400,
                'min_words': 150,
                'tone': 'concise',
                'style': 'actionable'
            },

            # Transcript Summary
            {
                'name': 'Video Summary',
                'description': 'Concise summary of video content',
                'template_type': 'summary',
                'platform': 'general',
                'prompt_template': '''
Create a concise summary of this video content.

VIDEO: {video_title}

TRANSCRIPT:
{transcript}

REQUIREMENTS:
- 2-3 paragraph summary
- Capture main themes
- Include key quotes if impactful
- Maintain video's tone

OUTPUT AS JSON:
{{
    "title": "Video Summary",
    "content": "Summary content",
    "main_themes": ["theme1", "theme2"],
    "key_quotes": ["quote1", "quote2"]
}}
                ''',
                'output_structure': {
                    'title': 'string',
                    'content': 'string',
                    'main_themes': 'array',
                    'key_quotes': 'array'
                },
                'max_words': 300,
                'min_words': 100,
                'tone': 'neutral',
                'style': 'concise'
            }
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = ContentTemplate.objects.get_or_create(
                name=template_data['name'],
                template_type=template_data['template_type'],
                platform=template_data['platform'],
                defaults=template_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template.name}')
                )
            else:
                updated_count += 1
                # Update existing template with new data
                for key, value in template_data.items():
                    setattr(template, key, value)
                template.save()
                self.stdout.write(
                    self.style.WARNING(f'Updated template: {template.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Created {created_count} new templates, '
                f'updated {updated_count} existing templates.'
            )
        )