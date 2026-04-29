"""
Content Processor for Dhaka College Notice Monitor
Handles PDF downloading, rendering to images, and branding overlay
"""

import os
import io
import hashlib
import requests
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF


class ContentProcessor:
    def __init__(self, logo_path: str = 'assets/logo.png'):
        self.logo_path = logo_path
        self.branding_name = "Archived by The DC Archive"
        self.facebook_link = "https://www.facebook.com/thedcarchive"
        self.telegram_link = "https://t.me/thedcarchive_notice"
        self.timeout = 30
        self.dpi = 150
        self.max_width = 1920
        
        # Branding colors
        self.overlay_bg_color = (0, 0, 0, 180)  # Semi-transparent black
        self.text_color = (255, 255, 255)  # White
        self.accent_color = (99, 102, 241)  # Indigo
    
    def detect_file_type(self, url: str) -> Optional[str]:
        """Detect file type from URL or HEAD request"""
        if not url:
            return None
        
        # Check URL extension
        url_lower = url.lower()
        if url_lower.endswith('.pdf'):
            return 'pdf'
        elif any(url_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            return 'image'
        
        # Try HEAD request
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'pdf' in content_type:
                return 'pdf'
            elif 'image' in content_type:
                return 'image'
        except:
            pass
        
        return 'unknown'
    
    def download_file(self, url: str) -> Tuple[Optional[bytes], Optional[str]]:
        """Download file and return bytes + hash"""
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            content = response.content
            file_hash = hashlib.sha256(content).hexdigest()
            return content, file_hash
        except Exception as e:
            print(f"❌ Error downloading {url}: {e}")
            return None, None
    
    def render_pdf_to_images(self, pdf_bytes: bytes) -> List[Image.Image]:
        """Render all pages of a PDF to PIL Images"""
        images = []
        
        try:
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Calculate zoom for desired DPI
                zoom = self.dpi / 72
                mat = fitz.Matrix(zoom, zoom)
                
                # Render page to pixmap
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # Resize if too wide
                if img.width > self.max_width:
                    ratio = self.max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((self.max_width, new_height), Image.Resampling.LANCZOS)
                
                images.append(img)
            
            doc.close()
            print(f"✅ Rendered {len(images)} pages from PDF")
        
        except Exception as e:
            print(f"❌ Error rendering PDF: {e}")
        
        return images
    
    def load_logo(self) -> Optional[Image.Image]:
        """Load the branding logo"""
        try:
            if os.path.exists(self.logo_path):
                logo = Image.open(self.logo_path)
                # Resize to 48x48
                logo = logo.resize((48, 48), Image.Resampling.LANCZOS)
                # Convert to RGBA if needed
                if logo.mode != 'RGBA':
                    logo = logo.convert('RGBA')
                return logo
        except Exception as e:
            print(f"⚠️ Could not load logo: {e}")
        return None
    
    def add_branding_overlay(self, image: Image.Image, logo: Optional[Image.Image] = None) -> Image.Image:
        """Add branding overlay to an image"""
        # Ensure RGBA mode
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Create overlay layer
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Calculate overlay dimensions
        overlay_height = 60
        top_bar_height = 50
        bottom_bar_height = 40
        
        # Draw top bar (semi-transparent)
        draw.rectangle(
            [(0, 0), (image.width, top_bar_height)],
            fill=self.overlay_bg_color
        )
        
        # Draw bottom bar (semi-transparent)
        draw.rectangle(
            [(0, image.height - bottom_bar_height), (image.width, image.height)],
            fill=self.overlay_bg_color
        )
        
        # Composite overlay onto image
        image = Image.alpha_composite(image, overlay)
        
        # Create new draw object for text
        draw = ImageDraw.Draw(image)
        
        # Try to load a font, fallback to default
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 16)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 12)
        except:
            try:
                font_large = ImageFont.truetype("arial.ttf", 16)
                font_small = ImageFont.truetype("arial.ttf", 12)
            except:
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
        
        # Add logo to top-left
        if logo:
            image.paste(logo, (10, 1), logo)
            text_start_x = 68
        else:
            text_start_x = 10
        
        # Add branding text to top
        draw.text(
            (text_start_x, 15),
            self.branding_name,
            fill=self.text_color,
            font=font_large
        )
        
        # Add links to bottom
        link_y = image.height - bottom_bar_height + 8
        draw.text(
            (10, link_y),
            f"Facebook: {self.facebook_link}",
            fill=self.text_color,
            font=font_small
        )
        draw.text(
            (10, link_y + 16),
            f"Telegram: {self.telegram_link}",
            fill=self.text_color,
            font=font_small
        )
        
        return image
    
    def process_notice_media(self, notice: Dict) -> Tuple[List[Image.Image], Optional[str], str]:
        """
        Process a notice's media (PDF or image)
        
        Returns:
            (images, pdf_hash, file_type)
        """
        download_url = notice.get('download_url', '')
        
        if not download_url:
            return [], None, 'none'
        
        # Detect file type
        file_type = self.detect_file_type(download_url)
        
        if file_type == 'pdf':
            # Download and render PDF
            pdf_bytes, pdf_hash = self.download_file(download_url)
            
            if pdf_bytes:
                images = self.render_pdf_to_images(pdf_bytes)
                
                # Load logo once
                logo = self.load_logo()
                
                # Add branding to all pages
                branded_images = []
                for img in images:
                    branded = self.add_branding_overlay(img, logo)
                    branded_images.append(branded)
                
                return branded_images, pdf_hash, 'pdf'
        
        elif file_type == 'image':
            # Download image directly
            img_bytes, img_hash = self.download_file(download_url)
            
            if img_bytes:
                try:
                    img = Image.open(io.BytesIO(img_bytes))
                    
                    # Add branding
                    logo = self.load_logo()
                    branded = self.add_branding_overlay(img, logo)
                    
                    return [branded], img_hash, 'image'
                except Exception as e:
                    print(f"❌ Error processing image: {e}")
        
        return [], None, 'unknown'
    
    def images_to_bytes(self, images: List[Image.Image], format: str = 'PNG') -> List[bytes]:
        """Convert PIL Images to bytes"""
        result = []
        for img in images:
            buffer = io.BytesIO()
            # Convert to RGB for JPEG, keep RGBA for PNG
            if format.upper() == 'JPEG':
                img = img.convert('RGB')
            img.save(buffer, format=format)
            result.append(buffer.getvalue())
        return result


if __name__ == "__main__":
    # Test content processor
    processor = ContentProcessor()
    
    print("Content Processor initialized")
    print(f"Logo path: {processor.logo_path}")
    print(f"Branding: {processor.branding_name}")
