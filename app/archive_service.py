from datetime import datetime, timezone
import uuid
from .services import get_db
from .models import Archive, Message, Tier, TIER_LIMITS
from .prompts import get_reflection_prompt
from firebase_admin import firestore
from loguru import logger
import asyncio
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import random


class ArchiveService:
    def __init__(self):
        self.model_name = "gemini-2.0-flash"

    @property
    def db(self):
        return get_db()
    
    def _get_archive_ref(self):
        return self.db.collection("archives")

    async def generate_reflection(self, transcript: list[Message]) -> dict:
        """
        Generates a reflection from the session transcript using an LLM.
        Returns a dict with: title, reflection, emotion_tag.
        """
        # Format transcript
        if not transcript:
             return {
                "title": "Quiet Moments",
                "reflection": "Silence can be as meaningful as words.",
                "emotion_tag": "peaceful"
            }

        transcript_str = "\n".join([f"{msg.role.upper()}: {msg.content}" for msg in transcript])
        prompt = get_reflection_prompt(transcript_str)
        
        try:
             model = GenerativeModel(self.model_name)
             # Use json output
             generation_config = GenerationConfig(response_mime_type="application/json")
             
             response = await asyncio.to_thread(
                 model.generate_content,
                 prompt,
                 generation_config=generation_config
             )
             data = json.loads(response.text)
             # Basic validation
             if "title" not in data or "reflection" not in data:
                 raise ValueError("Invalid JSON structure")
             return data
        except Exception as e:
            logger.error(f"Failed to generate reflection: {e}")
            # Fallback
            return {
                "title": "A Moment of Connection",
                "reflection": "Every conversation leaves a mark. This one matters.",
                "emotion_tag": "reflective"
            }

    async def create_archive_entry(self, uid: str, transcript: list[Message]) -> Archive:
        reflection_data = await self.generate_reflection(transcript)
        
        archive_id = str(uuid.uuid4())
        archive_entry = Archive(
            archive_id=archive_id,
            user_id=uid,
            title=reflection_data.get("title", "Untitled"),
            reflection=reflection_data.get("reflection", ""),
            emotion_tag=reflection_data.get("emotion_tag", "neutral"),
            created_at=datetime.now(timezone.utc)
        )
        
        # Save to Firestore
        self._get_archive_ref().document(archive_id).set(archive_entry.dict())
        
        return archive_entry
        
    async def get_user_archives(self, uid: str, limit: int = 10) -> list[Archive]:
        docs = self._get_archive_ref().where("user_id", "==", uid)\
            .limit(50).stream() # Get recent archives (unordered)
            
        archives = [Archive(**doc.to_dict()) for doc in docs]
        # Sort desc
        archives.sort(key=lambda x: x.created_at, reverse=True)
        
        return archives[:limit]

    async def get_archive(self, archive_id: str) -> Archive | None:
        doc = self._get_archive_ref().document(archive_id).get()
        if not doc.exists:
            return None
        return Archive(**doc.to_dict())

    def generate_archive_image(self, archive: Archive) -> BytesIO:
        """
        Generates a shareable image for the archive entry.
        Returns a BytesIO object containing the PNG image.
        """
        # Canvas setup
        width, height = 1080, 1080 # Instagram square
        
        # Determine background color based on emotion
        emotion_colors = {
            "hopeful": (135, 206, 250), # Light Sky Blue
            "conflicted": (221, 160, 221), # Plum
            "lonely": (119, 136, 153), # Light Slate Gray
            "weary": (169, 169, 169), # Dark Gray
            "determined": (255, 127, 80), # Coral
            "peaceful": (144, 238, 144), # Light Green
            "reflective": (176, 196, 222) # Light Steel Blue
        }
        bg_color = emotion_colors.get(archive.emotion_tag.lower(), (240, 248, 255)) # Alice Blue default
        
        # Create image
        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # Load fonts - try a few common linux ones or fallback
        try:
            # Try specific aesthetic fonts if available, else default sans
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            font_large = ImageFont.truetype(font_path, 60)
            font_medium = ImageFont.truetype(font_path, 40)
            font_small = ImageFont.truetype(font_path, 30)
        except OSError:
            # Fallback to default
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Config
        text_color = (40, 40, 40)
        padding = 100
        
        # Draw Reflection (Centered, wrapped)
        reflection_text = f'"{archive.reflection}"'
        
        # Simple text wrapping logic
        def wrap_text(text, font, max_width):
            lines = []
            words = text.split()
            current_line = []
            
            for word in words:
                current_line.append(word)
                # Check width
                test_line = ' '.join(current_line)
                bbox = draw.textbbox((0, 0), test_line, font=font)
                w = bbox[2] - bbox[0]
                if w > max_width:
                    # Pop last word and save line
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            return lines

        lines = wrap_text(reflection_text, font_large, width - 2*padding)
        
        # Calculate total height of text block to center responsibly
        line_heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font_large)
            line_heights.append(bbox[3] - bbox[1] + 20) # +20 line spacing
            
        total_text_height = sum(line_heights)
        current_y = (height - total_text_height) / 2 - 50 # Slightly up

        for i, line in enumerate(lines):
             # Center each line
            bbox = draw.textbbox((0, 0), line, font=font_large)
            w = bbox[2] - bbox[0]
            x = (width - w) / 2
            draw.text((x, current_y), line, font=font_large, fill=text_color)
            current_y += line_heights[i]

        # Draw Title (Top)
        # title_text = archive.title.upper()
        # bbox = draw.textbbox((0, 0), title_text, font=font_medium)
        # w = bbox[2] - bbox[0]
        # draw.text(((width - w)/2, 100), title_text, font=font_medium, fill=(80, 80, 80))

        # Footer
        footer_text = "From NEX"
        bbox = draw.textbbox((0, 0), footer_text, font=font_medium)
        w = bbox[2] - bbox[0]
        draw.text(((width - w)/2, height - 150), footer_text, font=font_medium, fill=(100, 100, 100))
        
        # Date
        date_str = archive.created_at.strftime("%B %d, %Y")
        bbox = draw.textbbox((0, 0), date_str, font=font_small)
        w = bbox[2] - bbox[0]
        draw.text(((width - w)/2, height - 100), date_str, font=font_small, fill=(130, 130, 130))

        # Output
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io

archive_service = ArchiveService()
