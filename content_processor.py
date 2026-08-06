"""
Content Processor for Dhaka College Notice Monitor
Handles PDF downloading, rendering to images, and branding overlay
"""

import os
import io
import time
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
        # (connect timeout, read timeout) — fail fast on stalled TCP, generous read for large PDFs
        self.timeout = (10, 60)
        self.max_width = 1920
        self.dpi = 150
        self._ua_headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            )
        }

        # Branding colors
        self.overlay_bg_color = (0, 0, 0, 180)  # Semi-transparent black
        self.text_color = (255, 255, 255)        # White
        self.accent_color = (99, 102, 241)        # Indigo
    
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
            response = requests.head(
                url, headers=self._ua_headers, timeout=self.timeout, allow_redirects=True
            )
            content_type = response.headers.get('Content-Type', '').lower()
            if 'pdf' in content_type:
                return 'pdf'
            elif 'image' in content_type:
                return 'image'
        except Exception:
            pass

        return 'unknown'

    def _download_with_retry(self, url: str, retries: int = 3, backoff: int = 2) -> bytes:
        """
        Download a URL with retry logic.
        Raises the last exception if all attempts fail.
        """
        last_exc = None
        for attempt in range(retries):
            try:
                response = requests.get(
                    url, headers=self._ua_headers, timeout=self.timeout
                )
                response.raise_for_status()
                return response.content
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                wait = backoff ** attempt
                print(f"  Attempt {attempt + 1}/{retries} failed ({type(e).__name__}). Retrying in {wait}s...")
                last_exc = e
                time.sleep(wait)
            except requests.exceptions.RequestException as e:
                # Non-transient error (e.g. 404) — no point retrying
                raise e
        raise last_exc
    
    def download_file(self, url: str) -> Tuple[Optional[bytes], Optional[str]]:
        """Download file and return (bytes, sha256-hash). Returns (None, None) on failure."""
        try:
            content = self._download_with_retry(url)
            file_hash = hashlib.sha256(content).hexdigest()
            return content, file_hash
        except Exception as e:
            print(f"Download failed after retries for {url}: {e}")
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
                
                # Apply smart crop then brand each page individually
                final_images = []
                for img in images:
                    img = self.smart_crop_whitespace(img)
                    final_images.append(add_branding(img))
                
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
