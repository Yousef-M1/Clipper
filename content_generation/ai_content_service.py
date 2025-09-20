"""
AI Content Generation Service
Transforms video content into various written formats using OpenAI
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import asyncio

import openai
from django.conf import settings

logger = logging.getLogger(__name__)


class AIContentGenerationService:
    """
    Service for generating written content from video transcripts using AI
    Similar to Quaso's content generation features
    """

    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.default_model = 'gpt-4'
        self.fallback_model = 'gpt-3.5-turbo'

    # ==============================================================================
    # BLOG POST GENERATION
    # ==============================================================================

    async def generate_blog_post(
        self,
        transcript: str,
        video_title: str = "",
        target_keywords: List[str] = None,
        target_audience: str = "",
        brand_voice: str = "professional",
        custom_instructions: str = "",
        word_count: int = 1500,
        template=None
    ) -> Dict:
        """Generate SEO-optimized blog post from video transcript"""

        prompt = self._build_blog_post_prompt(
            transcript=transcript,
            video_title=video_title,
            target_keywords=target_keywords or [],
            target_audience=target_audience,
            brand_voice=brand_voice,
            custom_instructions=custom_instructions,
            word_count=word_count
        )

        try:
            response = await self._call_openai_async(prompt, max_tokens=4000)

            # Parse the structured response
            content_data = self._parse_blog_post_response(response)

            return {
                'success': True,
                'content_type': 'blog_post',
                'title': content_data.get('title', ''),
                'content': content_data.get('content', ''),
                'meta_title': content_data.get('meta_title', ''),
                'meta_description': content_data.get('meta_description', ''),
                'keywords': content_data.get('keywords', []),
                'headings': content_data.get('headings', []),
                'word_count': len(content_data.get('content', '').split()),
                'ai_confidence': 0.9,
                'tokens_used': response.get('usage', {}).get('total_tokens', 0)
            }

        except Exception as e:
            logger.error(f"Blog post generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'content_type': 'blog_post'
            }

    def _build_blog_post_prompt(
        self,
        transcript: str,
        video_title: str,
        target_keywords: List[str],
        target_audience: str,
        brand_voice: str,
        custom_instructions: str,
        word_count: int
    ) -> str:
        """Build comprehensive blog post generation prompt"""

        keywords_section = ""
        if target_keywords:
            keywords_section = f"""
TARGET KEYWORDS TO INCLUDE:
{', '.join(target_keywords)}
"""

        audience_section = ""
        if target_audience:
            audience_section = f"""
TARGET AUDIENCE: {target_audience}
"""

        custom_section = ""
        if custom_instructions:
            custom_section = f"""
ADDITIONAL INSTRUCTIONS:
{custom_instructions}
"""

        return f"""
You are an expert content writer and SEO specialist. Transform this video transcript into a comprehensive, engaging blog post.

VIDEO TITLE: {video_title}
{audience_section}
BRAND VOICE: {brand_voice}
TARGET WORD COUNT: {word_count} words

{keywords_section}
{custom_section}

VIDEO TRANSCRIPT:
{transcript}

REQUIREMENTS:
1. Create an engaging, SEO-optimized blog post
2. Use proper heading structure (H1, H2, H3)
3. Include bullet points and numbered lists where appropriate
4. Make it scannable with short paragraphs
5. Include a compelling introduction and conclusion
6. Naturally incorporate target keywords
7. Add value beyond just transcribing the video

OUTPUT FORMAT (JSON):
{{
    "title": "Main blog post title (H1)",
    "meta_title": "SEO meta title (max 60 chars)",
    "meta_description": "SEO meta description (max 160 chars)",
    "content": "Full blog post content in Markdown format",
    "keywords": ["extracted", "keywords", "array"],
    "headings": [
        {{"level": "h2", "text": "Section Title"}},
        {{"level": "h3", "text": "Subsection Title"}}
    ]
}}

Generate a {word_count}-word blog post that provides value to readers and ranks well in search engines.
"""

    # ==============================================================================
    # SHOW NOTES GENERATION
    # ==============================================================================

    async def generate_show_notes(
        self,
        transcript: str,
        video_title: str = "",
        video_duration: int = 0,
        target_audience: str = "",
        brand_voice: str = "conversational",
        custom_instructions: str = "",
        template=None
    ) -> Dict:
        """Generate detailed show notes for podcasts/videos"""

        prompt = self._build_show_notes_prompt(
            transcript=transcript,
            video_title=video_title,
            video_duration=video_duration,
            target_audience=target_audience,
            brand_voice=brand_voice,
            custom_instructions=custom_instructions
        )

        try:
            response = await self._call_openai_async(prompt, max_tokens=3000)
            content_data = self._parse_show_notes_response(response)

            return {
                'success': True,
                'content_type': 'show_notes',
                'title': content_data.get('title', ''),
                'content': content_data.get('content', ''),
                'summary': content_data.get('summary', ''),
                'key_takeaways': content_data.get('key_takeaways', []),
                'timestamps': content_data.get('timestamps', []),
                'guests': content_data.get('guests', []),
                'resources': content_data.get('resources', []),
                'word_count': len(content_data.get('content', '').split()),
                'ai_confidence': 0.88,
                'tokens_used': response.get('usage', {}).get('total_tokens', 0)
            }

        except Exception as e:
            logger.error(f"Show notes generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'content_type': 'show_notes'
            }

    def _build_show_notes_prompt(
        self,
        transcript: str,
        video_title: str,
        video_duration: int,
        target_audience: str,
        brand_voice: str,
        custom_instructions: str
    ) -> str:
        """Build show notes generation prompt"""

        duration_text = f" ({video_duration // 60}:{video_duration % 60:02d})" if video_duration else ""
        audience_section = f"TARGET AUDIENCE: {target_audience}\n" if target_audience else ""
        custom_section = f"\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}" if custom_instructions else ""

        return f"""
You are an expert content producer creating comprehensive show notes. Transform this video/audio transcript into detailed, valuable show notes.

VIDEO/EPISODE: {video_title}{duration_text}
{audience_section}BRAND VOICE: {brand_voice}

TRANSCRIPT:
{transcript}

{custom_section}

OUTPUT FORMAT (JSON):
{{
    "title": "Episode title",
    "summary": "2-3 sentence episode summary",
    "content": "Full show notes in Markdown format",
    "key_takeaways": ["takeaway 1", "takeaway 2", "..."],
    "timestamps": [
        {{"time": "00:05", "description": "Topic discussed"}},
        {{"time": "15:30", "description": "Key point made"}}
    ],
    "guests": ["Guest Name with brief bio"],
    "resources": ["Resource 1: URL", "Resource 2: URL"]
}}

Create comprehensive show notes that help listeners navigate the episode and find value.
"""

    # ==============================================================================
    # SOCIAL MEDIA CONTENT GENERATION
    # ==============================================================================

    async def generate_social_media_posts(
        self,
        transcript: str,
        video_title: str = "",
        target_keywords: List[str] = None,
        target_audience: str = "",
        brand_voice: str = "engaging",
        custom_instructions: str = "",
        template=None
    ) -> Dict:
        """Generate social media posts for various platforms"""

        prompt = self._build_social_media_prompt(
            transcript=transcript,
            video_title=video_title,
            target_keywords=target_keywords or [],
            target_audience=target_audience,
            brand_voice=brand_voice,
            custom_instructions=custom_instructions
        )

        try:
            response = await self._call_openai_async(prompt, max_tokens=2000)
            content_data = self._parse_social_media_response(response)

            return {
                'success': True,
                'content_type': 'social_media',
                'title': content_data.get('title', 'Social Media Posts'),
                'content': content_data.get('content', ''),
                'posts': content_data.get('posts', []),
                'hashtags': content_data.get('hashtags', []),
                'call_to_action': content_data.get('call_to_action', ''),
                'format': 'markdown',
                'word_count': sum(len(post.split()) for post in content_data.get('posts', [])),
                'ai_confidence': 0.85,
                'tokens_used': response.get('usage', {}).get('total_tokens', 0)
            }

        except Exception as e:
            logger.error(f"Social media generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'content_type': 'social_media'
            }

    def _get_platform_config(self, platform: str) -> Dict:
        """Get platform-specific configuration"""
        configs = {
            'twitter': {
                'char_limit': 280,
                'optimal_hashtags': 2,
                'style': 'concise and engaging'
            },
            'linkedin': {
                'char_limit': 3000,
                'optimal_hashtags': 5,
                'style': 'professional and insightful'
            },
            'instagram': {
                'char_limit': 2200,
                'optimal_hashtags': 10,
                'style': 'visual and engaging'
            },
            'facebook': {
                'char_limit': 2000,
                'optimal_hashtags': 3,
                'style': 'conversational and shareable'
            },
            'general': {
                'char_limit': 500,
                'optimal_hashtags': 5,
                'style': 'engaging and versatile'
            }
        }
        return configs.get(platform, configs['general'])

    def _build_social_media_prompt(
        self,
        transcript: str,
        video_title: str,
        target_keywords: List[str],
        target_audience: str,
        brand_voice: str,
        custom_instructions: str
    ) -> str:
        """Build social media generation prompt"""

        keywords_section = f"TARGET KEYWORDS: {', '.join(target_keywords)}\n" if target_keywords else ""
        audience_section = f"TARGET AUDIENCE: {target_audience}\n" if target_audience else ""
        custom_section = f"\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}" if custom_instructions else ""

        return f"""
You are a social media expert creating engaging posts. Transform key insights from this video into compelling social media content.

VIDEO TITLE: {video_title}
{audience_section}{keywords_section}BRAND VOICE: {brand_voice}

{custom_section}

VIDEO TRANSCRIPT:
{transcript}

REQUIREMENTS:
1. Create engaging social media posts
2. Use {brand_voice} tone
3. Include relevant hashtags
4. Include call-to-action when appropriate
5. Make posts shareable and engaging
6. Use emojis where appropriate

OUTPUT FORMAT (JSON):
{{
    "title": "Social Media Posts Title",
    "content": "Combined social media post content in markdown format",
    "posts": [
        "Post 1 content...",
        "Post 2 content..."
    ],
    "hashtags": ["hashtag1", "hashtag2"],
    "call_to_action": "Clear call-to-action"
}}

Create viral-worthy content that drives engagement!
"""

    # ==============================================================================
    # SEO ARTICLE GENERATION
    # ==============================================================================

    async def generate_seo_article(
        self,
        transcript: str,
        primary_keyword: str,
        secondary_keywords: List[str] = None,
        target_audience: str = "",
        article_length: int = 2000,
        custom_instructions: str = ""
    ) -> Dict:
        """Generate comprehensive SEO-optimized article"""

        prompt = self._build_seo_article_prompt(
            transcript=transcript,
            primary_keyword=primary_keyword,
            secondary_keywords=secondary_keywords or [],
            target_audience=target_audience,
            article_length=article_length,
            custom_instructions=custom_instructions
        )

        try:
            response = await self._call_openai_async(prompt, max_tokens=5000)
            content_data = self._parse_seo_article_response(response)

            return {
                'success': True,
                'content_type': 'seo_article',
                'title': content_data.get('title', ''),
                'content': content_data.get('content', ''),
                'meta_title': content_data.get('meta_title', ''),
                'meta_description': content_data.get('meta_description', ''),
                'keywords': content_data.get('keywords', []),
                'headings': content_data.get('headings', []),
                'word_count': len(content_data.get('content', '').split()),
                'keyword_density': content_data.get('keyword_density', {}),
                'ai_confidence': 0.92,
                'tokens_used': response.get('usage', {}).get('total_tokens', 0)
            }

        except Exception as e:
            logger.error(f"SEO article generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'content_type': 'seo_article'
            }

    # ==============================================================================
    # CORE AI COMMUNICATION
    # ==============================================================================

    async def _call_openai_async(self, prompt: str, max_tokens: int = 3000) -> Dict:
        """Make async call to OpenAI API with fallback"""
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.default_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert content writer and SEO specialist. Always respond with valid JSON format."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )

            return {
                'content': response.choices[0].message.content,
                'usage': {
                    'total_tokens': response.usage.total_tokens,
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens
                },
                'model': response.model
            }

        except Exception as e:
            logger.warning(f"Primary model failed, trying fallback: {str(e)}")
            try:
                # Fallback to cheaper model
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.fallback_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert content writer. Always respond with valid JSON format."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=0.7
                )

                return {
                    'content': response.choices[0].message.content,
                    'usage': {
                        'total_tokens': response.usage.total_tokens,
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens
                    },
                    'model': response.model
                }

            except Exception as fallback_error:
                logger.error(f"Both models failed: {str(fallback_error)}")
                raise fallback_error

    # ==============================================================================
    # RESPONSE PARSING
    # ==============================================================================

    def _parse_blog_post_response(self, response: Dict) -> Dict:
        """Parse blog post response from OpenAI"""
        try:
            content = response.get('content', '')
            # Remove potential markdown code blocks
            content = re.sub(r'^```json\s*|\s*```$', '', content.strip())
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback parsing if JSON is malformed
            return self._fallback_parse_blog_post(response.get('content', ''))

    def _parse_show_notes_response(self, response: Dict) -> Dict:
        """Parse show notes response from OpenAI"""
        try:
            content = response.get('content', '')
            content = re.sub(r'^```json\s*|\s*```$', '', content.strip())
            return json.loads(content)
        except json.JSONDecodeError:
            return self._fallback_parse_show_notes(response.get('content', ''))

    def _parse_social_media_response(self, response: Dict) -> Dict:
        """Parse social media response from OpenAI"""
        try:
            content = response.get('content', '')
            content = re.sub(r'^```json\s*|\s*```$', '', content.strip())
            return json.loads(content)
        except json.JSONDecodeError:
            return self._fallback_parse_social_media(response.get('content', ''))

    def _parse_seo_article_response(self, response: Dict) -> Dict:
        """Parse SEO article response from OpenAI"""
        try:
            content = response.get('content', '')
            content = re.sub(r'^```json\s*|\s*```$', '', content.strip())
            return json.loads(content)
        except json.JSONDecodeError:
            return self._fallback_parse_seo_article(response.get('content', ''))

    # ==============================================================================
    # FALLBACK PARSERS
    # ==============================================================================

    def _fallback_parse_blog_post(self, content: str) -> Dict:
        """Fallback parser for blog post when JSON parsing fails"""
        return {
            'title': 'Generated Blog Post',
            'meta_title': 'Generated Blog Post',
            'meta_description': 'AI-generated blog post from video content',
            'content': content,
            'keywords': [],
            'headings': []
        }

    def _fallback_parse_show_notes(self, content: str) -> Dict:
        """Fallback parser for show notes when JSON parsing fails"""
        return {
            'title': 'Episode Show Notes',
            'summary': 'AI-generated show notes from video content',
            'content': content,
            'key_takeaways': [],
            'timestamps': [],
            'guests': [],
            'resources': []
        }

    def _fallback_parse_social_media(self, content: str) -> Dict:
        """Fallback parser for social media when JSON parsing fails"""
        return {
            'posts': [content],
            'hashtags': [],
            'call_to_action': 'Watch the full video!'
        }

    def _fallback_parse_seo_article(self, content: str) -> Dict:
        """Fallback parser for SEO article when JSON parsing fails"""
        return {
            'title': 'SEO Optimized Article',
            'meta_title': 'SEO Optimized Article',
            'meta_description': 'Comprehensive SEO article from video content',
            'content': content,
            'keywords': [],
            'headings': [],
            'keyword_density': {}
        }

    # ==============================================================================
    # UTILITY METHODS
    # ==============================================================================

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for pricing"""
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4

    def calculate_cost(self, tokens_used: int, model: str = 'gpt-4') -> float:
        """Calculate estimated cost in USD"""
        # Pricing as of 2024 (update as needed)
        rates = {
            'gpt-4': 0.03 / 1000,  # $0.03 per 1K tokens
            'gpt-3.5-turbo': 0.002 / 1000  # $0.002 per 1K tokens
        }
        return tokens_used * rates.get(model, rates['gpt-4'])

    def get_supported_content_types(self) -> List[str]:
        """Get list of supported content generation types"""
        return [
            'blog_post',
            'show_notes',
            'social_media',
            'video_description',
            'seo_article',
            'email_newsletter',
            'transcript_summary',
            'key_takeaways'
        ]

    # ==============================================================================
    # ADDITIONAL CONTENT GENERATION METHODS
    # ==============================================================================

    async def generate_email_newsletter(
        self,
        transcript: str,
        video_title: str = "",
        target_keywords: List[str] = None,
        target_audience: str = "",
        brand_voice: str = "professional",
        custom_instructions: str = "",
        template=None
    ) -> Dict:
        """Generate email newsletter from video transcript"""
        prompt = self._build_email_newsletter_prompt(
            transcript=transcript,
            video_title=video_title,
            target_keywords=target_keywords or [],
            target_audience=target_audience,
            brand_voice=brand_voice,
            custom_instructions=custom_instructions
        )

        try:
            response = await self._call_openai_async(prompt, max_tokens=3000)
            content_data = self._parse_email_newsletter_response(response)

            return {
                'success': True,
                'content_type': 'email_newsletter',
                'title': content_data.get('title', ''),
                'content': content_data.get('content', ''),
                'subject_line': content_data.get('subject_line', ''),
                'preview_text': content_data.get('preview_text', ''),
                'call_to_action': content_data.get('call_to_action', ''),
                'format': 'html',
                'word_count': len(content_data.get('content', '').split()),
                'ai_confidence': 0.87,
                'tokens_used': response.get('usage', {}).get('total_tokens', 0)
            }

        except Exception as e:
            logger.error(f"Email newsletter generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'content_type': 'email_newsletter'
            }

    async def generate_video_summary(
        self,
        transcript: str,
        video_title: str = "",
        video_duration: int = 0,
        target_audience: str = "",
        brand_voice: str = "professional",
        custom_instructions: str = "",
        template=None
    ) -> Dict:
        """Generate video summary from transcript"""
        prompt = self._build_video_summary_prompt(
            transcript=transcript,
            video_title=video_title,
            video_duration=video_duration,
            target_audience=target_audience,
            brand_voice=brand_voice,
            custom_instructions=custom_instructions
        )

        try:
            response = await self._call_openai_async(prompt, max_tokens=2000)
            content_data = self._parse_video_summary_response(response)

            return {
                'success': True,
                'content_type': 'video_summary',
                'title': content_data.get('title', ''),
                'content': content_data.get('content', ''),
                'key_points': content_data.get('key_points', []),
                'summary': content_data.get('summary', ''),
                'format': 'markdown',
                'word_count': len(content_data.get('content', '').split()),
                'ai_confidence': 0.90,
                'tokens_used': response.get('usage', {}).get('total_tokens', 0)
            }

        except Exception as e:
            logger.error(f"Video summary generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'content_type': 'video_summary'
            }

    async def generate_custom_content(
        self,
        transcript: str,
        video_title: str = "",
        template=None,
        custom_variables: Dict = None
    ) -> Dict:
        """Generate custom content using template"""
        if not template:
            return {
                'success': False,
                'error': 'Template is required for custom content generation'
            }

        variables = custom_variables or {}

        # Replace template placeholders with actual values
        prompt = template.prompt_template

        # Common replacements
        prompt = prompt.replace('{transcript}', transcript)
        prompt = prompt.replace('{video_title}', video_title)
        prompt = prompt.replace('{target_audience}', variables.get('target_audience', ''))
        prompt = prompt.replace('{brand_voice}', variables.get('brand_voice', 'professional'))
        prompt = prompt.replace('{custom_instructions}', variables.get('custom_instructions', ''))

        # Handle arrays
        if '{target_keywords}' in prompt:
            keywords = variables.get('target_keywords', [])
            prompt = prompt.replace('{target_keywords}', ', '.join(keywords) if keywords else '')

        try:
            response = await self._call_openai_async(prompt, max_tokens=3500)
            content_data = self._parse_custom_content_response(response, template.template_type)

            return {
                'success': True,
                'content_type': template.template_type,
                'title': content_data.get('title', video_title),
                'content': content_data.get('content', ''),
                'format': content_data.get('format', 'markdown'),
                'word_count': len(content_data.get('content', '').split()),
                'ai_confidence': 0.85,
                'tokens_used': response.get('usage', {}).get('total_tokens', 0)
            }

        except Exception as e:
            logger.error(f"Custom content generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'content_type': template.template_type
            }

    # ==============================================================================
    # ADDITIONAL PROMPT BUILDERS
    # ==============================================================================

    def _build_email_newsletter_prompt(
        self,
        transcript: str,
        video_title: str,
        target_keywords: List[str],
        target_audience: str,
        brand_voice: str,
        custom_instructions: str
    ) -> str:
        """Build email newsletter generation prompt"""
        return f"""
You are an expert email marketing specialist. Transform this video transcript into an engaging email newsletter.

VIDEO TITLE: {video_title}
TARGET AUDIENCE: {target_audience}
BRAND VOICE: {brand_voice}
TARGET KEYWORDS: {', '.join(target_keywords)}

{custom_instructions}

VIDEO TRANSCRIPT:
{transcript}

OUTPUT FORMAT (JSON):
{{
    "title": "Newsletter title",
    "subject_line": "Compelling email subject line (max 50 chars)",
    "preview_text": "Email preview text (max 90 chars)",
    "content": "Full newsletter content in HTML format",
    "call_to_action": "Clear call-to-action text"
}}

Create an engaging newsletter that provides value and drives action.
"""

    def _build_video_summary_prompt(
        self,
        transcript: str,
        video_title: str,
        video_duration: int,
        target_audience: str,
        brand_voice: str,
        custom_instructions: str
    ) -> str:
        """Build video summary generation prompt"""
        duration_text = f" ({video_duration // 60}:{video_duration % 60:02d})" if video_duration else ""

        return f"""
You are an expert content summarizer. Create a comprehensive summary of this video content.

VIDEO: {video_title}{duration_text}
TARGET AUDIENCE: {target_audience}
BRAND VOICE: {brand_voice}

{custom_instructions}

VIDEO TRANSCRIPT:
{transcript}

OUTPUT FORMAT (JSON):
{{
    "title": "Video summary title",
    "summary": "2-3 sentence overview",
    "content": "Detailed summary in Markdown format",
    "key_points": ["key point 1", "key point 2", "..."]
}}

Create a valuable summary that captures the essence and key insights.
"""

    # ==============================================================================
    # ADDITIONAL RESPONSE PARSERS
    # ==============================================================================

    def _parse_email_newsletter_response(self, response: Dict) -> Dict:
        """Parse email newsletter response from OpenAI"""
        try:
            content = response.get('content', '')
            content = re.sub(r'^```json\s*|\s*```$', '', content.strip())
            return json.loads(content)
        except json.JSONDecodeError:
            return self._fallback_parse_email_newsletter(response.get('content', ''))

    def _parse_video_summary_response(self, response: Dict) -> Dict:
        """Parse video summary response from OpenAI"""
        try:
            content = response.get('content', '')
            content = re.sub(r'^```json\s*|\s*```$', '', content.strip())
            return json.loads(content)
        except json.JSONDecodeError:
            return self._fallback_parse_video_summary(response.get('content', ''))

    def _parse_custom_content_response(self, response: Dict, content_type: str) -> Dict:
        """Parse custom content response from OpenAI"""
        try:
            content = response.get('content', '')
            content = re.sub(r'^```json\s*|\s*```$', '', content.strip())
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                'title': f'Generated {content_type.replace("_", " ").title()}',
                'content': response.get('content', ''),
                'format': 'markdown'
            }

    def _fallback_parse_email_newsletter(self, content: str) -> Dict:
        """Fallback parser for email newsletter when JSON parsing fails"""
        return {
            'title': 'Weekly Newsletter',
            'subject_line': 'New insights from our latest video',
            'preview_text': 'Check out the key takeaways...',
            'content': content,
            'call_to_action': 'Watch the full video'
        }

    def _fallback_parse_video_summary(self, content: str) -> Dict:
        """Fallback parser for video summary when JSON parsing fails"""
        return {
            'title': 'Video Summary',
            'summary': 'AI-generated summary from video content',
            'content': content,
            'key_points': []
        }