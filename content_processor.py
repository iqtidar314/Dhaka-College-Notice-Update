"""
Content Processor for Dhaka College Notice Monitor
Handles PDF downloading, rendering to images, and branding overlay
"""

import os
import io
import hashlib
import requests
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import fitz  # PyMuPDF
import numpy as np
from branding import add_branding


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
    
    def smart_crop_whitespace(self, img: Image.Image, threshold=245, padding=20) -> Image.Image:
        """Remove white borders while preserving content."""
        img_array = np.array(img.convert("RGB"))
        # Find rows/cols that are NOT pure white
        mask = np.any(img_array < threshold, axis=2)
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        if not rows.any():
            return img
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        # Add padding back
        h, w = img_array.shape[:2]
        rmin = max(0, rmin - padding)
        rmax = min(h, rmax + padding)
        cmin = max(0, cmin - padding)
        cmax = min(w, cmax + padding)
        return img.crop((cmin, rmin, cmax, rmax))


    def _stitch_vertical(self, images: List[Image.Image], max_width: int, gap: int, gap_color: tuple) -> Image.Image:
        scaled = []
        for img in images:
            r = max_width / img.width
            scaled.append(img.resize((int(img.width * r), int(img.height * r)), Image.Resampling.LANCZOS))
        
        total_h = sum(i.height for i in scaled) + gap * (len(scaled) - 1)
        canvas = Image.new("RGB", (max_width, total_h), gap_color)
        y = 0
        for img in scaled:
            canvas.paste(img, (0, y))
            y += img.height + gap
        return canvas

    def _stitch_horizontal(self, images: List[Image.Image], gap: int, gap_color: tuple) -> Image.Image:
        total_w = sum(i.width for i in images) + gap * (len(images) - 1)
        max_h   = max(i.height for i in images)
        canvas  = Image.new("RGB", (total_w, max_h), gap_color)
        x = 0
        for img in images:
            canvas.paste(img, (x, 0))
            x += img.width + gap
        return canvas

    def stitch_pages_vertical(
        self,
        page_images: List[Image.Image],
        max_width: int = 1920,
        gap: int = 8,
        gap_color: tuple = (255, 255, 255),
        max_pages_to_stitch: int = 8
    ) -> List[Image.Image]:
        """
        Strategy:
        - If 1-3 pages: stitch vertically into one tall image
        - If 4-8 pages: stitch into a 2-column grid
        - If 9+ pages: return original images unstitched
        """
        n = len(page_images)
        if n == 0:
            return []
        if n <= 3:
            return [self._stitch_vertical(page_images, max_width, gap, gap_color)]
        elif n <= max_pages_to_stitch:
            left  = page_images[0::2]
            right = page_images[1::2]
            col_w = (max_width - gap) // 2
            left_strip  = self._stitch_vertical(left,  col_w, gap, gap_color)
            right_strip = self._stitch_vertical(right, col_w, gap, gap_color)
            return [self._stitch_horizontal([left_strip, right_strip], gap, gap_color)]
        else:
            # Document is too long. We just return individual pages to be sent as album.
            return page_images
    
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
                
                # Apply smart crop
                processed = []
                for img in images:
                    img = self.smart_crop_whitespace(img)
                    processed.append(img)
                
                # Stitch images if there are multiple
                stitched_images = self.stitch_pages_vertical(processed, max_width=self.max_width)
                
                # Add branding overlay and bar to each stitched image
                final_images = [add_branding(img) for img in stitched_images]
                
                return final_images, pdf_hash, 'pdf'
        
        elif file_type == 'image':
            # Download image directly
            img_bytes, img_hash = self.download_file(download_url)
            
            if img_bytes:
                try:
                    img = Image.open(io.BytesIO(img_bytes))
                    
                    # Process image
                    branded = add_branding(img)
                    
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
