import os
from PIL import Image, ImageDraw, ImageFont

def main():
    manifest_dir = "/Users/srihari1306/Desktop/bray-candidate-evaluator/teams-panel/public/manifest"
    os.makedirs(manifest_dir, exist_ok=True)
    
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    if not os.path.exists(font_path):
        font_path = "arial.ttf"  # fallback
        
    print(f"Using font path: {font_path}")
    
    # 1. Generate color.png (192x192, #2B579A background, white 'SI' text)
    color_img = Image.new("RGBA", (192, 192), "#2B579A")
    draw_color = ImageDraw.Draw(color_img)
    try:
        font_color = ImageFont.truetype(font_path, 96)
    except IOError:
        font_color = ImageFont.load_default()
        print("Warning: Could not load Arial font for color icon, using default")
        
    # Draw 'SI' text centered using anchor 'mm' (middle-middle)
    draw_color.text((96, 96), "SI", fill="white", font=font_color, anchor="mm")
    
    color_path = os.path.join(manifest_dir, "color.png")
    color_img.save(color_path, "PNG")
    print(f"Generated color.png at: {color_path}")
    
    # 2. Generate outline.png (32x32, fully transparent background, white 'SI' text)
    outline_img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw_outline = ImageDraw.Draw(outline_img)
    try:
        font_outline = ImageFont.truetype(font_path, 16)
    except IOError:
        font_outline = ImageFont.load_default()
        print("Warning: Could not load Arial font for outline icon, using default")
        
    draw_outline.text((16, 16), "SI", fill="white", font=font_outline, anchor="mm")
    
    outline_path = os.path.join(manifest_dir, "outline.png")
    outline_img.save(outline_path, "PNG")
    print(f"Generated outline.png at: {outline_path}")
    
    # Check image sizes and modes
    print(f"color.png: size={color_img.size}, mode={color_img.mode}")
    print(f"outline.png: size={outline_img.size}, mode={outline_img.mode}")

if __name__ == "__main__":
    main()
