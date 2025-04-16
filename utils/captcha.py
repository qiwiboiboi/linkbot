import os
import random
import string
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

def generate_captcha_text(length=5):
    """Generate random text for captcha"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_captcha_image(text):
    """Generate captcha image from text"""
    # Create image with white background
    width = 200
    height = 80
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Add noise (random dots)
    for _ in range(1000):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill='gray')
    
    # Add lines for noise
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill='gray', width=1)
    
    # Calculate font size and position
    font_size = 45
    try:
        # Try to use Arial font if available
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Calculate text size and position
    text_width = font.getlength(text)
    text_x = (width - text_width) // 2
    text_y = (height - font_size) // 2
    
    # Add text to image
    draw.text((text_x, text_y), text, font=font, fill='black')
    
    # Return image as bytes
    img_byte_array = BytesIO()
    image.save(img_byte_array, format='PNG')
    img_byte_array.seek(0)
    return img_byte_array.getvalue()
