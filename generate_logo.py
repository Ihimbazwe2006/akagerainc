"""
Generate Akagera Inc Logo with Dancing Script Font
"""
import os
import requests
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# =========================
# DOWNLOAD DANCING SCRIPT FONT
# =========================
def download_dancing_script_font():
    """Download Dancing Script font from Google Fonts"""
    font_dir = Path("fonts")
    font_dir.mkdir(exist_ok=True)
    
    font_path = font_dir / "DancingScript-Bold.ttf"
    
    if not font_path.exists():
        print("📥 Downloading Dancing Script font...")
        url = "https://github.com/google/fonts/raw/main/ofl/dancingscript/DancingScript-Bold.ttf"
        try:
            response = requests.get(url, timeout=10)
            with open(font_path, "wb") as f:
                f.write(response.content)
            print(f"✅ Font downloaded: {font_path}")
        except Exception as e:
            print(f"⚠️ Error downloading font: {e}")
            print("Using system fallback font")
            return None
    else:
        print(f"✅ Font found: {font_path}")
    
    return str(font_path)


# =========================
# GENERATE LOGO
# =========================
def generate_akagera_logo():
    """Generate Akagera Inc Logo"""
    
    # Font setup
    font_path = download_dancing_script_font()
    
    # Create image with gradient background
    width, height = 800, 300
    img = Image.new('RGB', (width, height), color='#FFFFFF')
    draw = ImageDraw.Draw(img, 'RGBA')
    
    # Draw background with gradient effect
    for y in range(height):
        # Gradient from dark blue to light blue
        r = int(25 + (173 - 25) * (y / height))
        g = int(25 + (216 - 25) * (y / height))
        b = int(112 + (230 - 112) * (y / height))
        draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
    
    # Load font
    try:
        if font_path:
            font_size = 120
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
            print("⚠️ Using default font")
    except Exception as e:
        print(f"Error loading font: {e}")
        font = ImageFont.load_default()
    
    # Text to render
    text = "Akagera Inc"
    
    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # Draw text shadow
    shadow_offset = 3
    draw.text(
        (x + shadow_offset, y + shadow_offset),
        text,
        font=font,
        fill=(0, 0, 0, 100)
    )
    
    # Draw main text
    draw.text(
        (x, y),
        text,
        font=font,
        fill=(255, 255, 255, 255)
    )
    
    # Save logo
    uploads_dir = Path("uploads/logos")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    logo_path = uploads_dir / "akagera_inc_logo.png"
    img.save(logo_path)
    
    print(f"✅ Logo created: {logo_path}")
    print(f"📍 Logo path for URL: /uploads/logos/akagera_inc_logo.png")
    
    return str(logo_path)


# =========================
# GENERATE ICON VARIANT
# =========================
def generate_akagera_icon():
    """Generate Akagera Inc Icon (square, smaller)"""
    
    font_path = download_dancing_script_font()
    
    # Create square icon
    size = 200
    img = Image.new('RGB', (size, size), color='#FFFFFF')
    draw = ImageDraw.Draw(img, 'RGBA')
    
    # Draw circular gradient background
    for radius in range(size // 2, 0, -1):
        # Gradient from light to dark
        intensity = int(255 * (1 - radius / (size // 2)))
        color = (30, 130 + intensity // 4, 160 + intensity // 2)
        draw.ellipse(
            [(size // 2 - radius, size // 2 - radius),
             (size // 2 + radius, size // 2 + radius)],
            fill=color
        )
    
    # Load font
    try:
        if font_path:
            font = ImageFont.truetype(font_path, 40)
        else:
            font = ImageFont.load_default()
    except Exception as e:
        print(f"Error loading font: {e}")
        font = ImageFont.load_default()
    
    # Draw "AI" text (initials)
    text = "AI"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    draw.text(
        (x, y),
        text,
        font=font,
        fill=(255, 255, 255, 255)
    )
    
    # Save icon
    uploads_dir = Path("uploads/logos")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    icon_path = uploads_dir / "akagera_inc_icon.png"
    img.save(icon_path)
    
    print(f"✅ Icon created: {icon_path}")
    
    return str(icon_path)


if __name__ == "__main__":
    print("🎨 Generating Akagera Inc Branding...")
    print()
    
    logo = generate_akagera_logo()
    icon = generate_akagera_icon()
    
    print()
    print("=" * 50)
    print("✨ Logo generation complete!")
    print("=" * 50)
