from PIL import Image, ImageDraw

def create_icon():
    # Create a 256x256 image for the icon
    size = (256, 256)
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # ── Background ───────────────────────────────────────────────────────────
    # Draw a rounded purple square
    purple = (108, 99, 255, 255)
    dark_purple = (20, 20, 36, 255)
    
    # Simple circle background for now (looks like a planet/logo)
    draw.ellipse([10, 10, 246, 246], fill=dark_purple)
    
    # ── Arrow Icon (Streamore branding) ──────────────────────────────────────
    # Down arrow stem
    draw.rectangle([110, 50, 146, 150], fill=purple)
    # Down arrow head
    draw.polygon([(60, 150), (196, 150), (128, 200)], fill=purple)
    # Bottom tray line
    draw.rectangle([80, 210, 176, 225], fill=purple)
    
    # Save as ICO (supports multiple sizes automatically)
    import os
    save_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
    img.save(save_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Created icon.ico in: {save_path}")

if __name__ == "__main__":
    create_icon()
