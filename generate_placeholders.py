from PIL import Image, ImageDraw, ImageFont
import os

def create_education_image(filename, text, size=(800, 600)):
    # Create a new image with a light gray background
    img = Image.new('RGB', size, '#f0f0f0')
    draw = ImageDraw.Draw(img)
    
    # Add a border
    draw.rectangle([(0, 0), (size[0]-1, size[1]-1)], outline='#000000', width=2)
    
    # Add text
    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except:
        font = ImageFont.load_default()
    
    # Center the text
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    # Draw text
    draw.text((x, y), text, fill='#000000', font=font)
    
    # Save the image
    img.save(f'static/images/{filename}')

def create_reward_image(filename, text, size=(200, 200)):
    # Create a new image with a white background
    img = Image.new('RGBA', size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a circle
    circle_bbox = [(20, 20), (size[0]-20, size[1]-20)]
    draw.ellipse(circle_bbox, fill='#FFD700', outline='#000000', width=2)
    
    # Add text
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Center the text
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    # Draw text
    draw.text((x, y), text, fill='#000000', font=font)
    
    # Save the image
    img.save(f'static/images/{filename}')

def main():
    # Create images directory if it doesn't exist
    os.makedirs('static/images', exist_ok=True)
    
    # Generate education images
    education_images = [
        ('grid-basics.jpg', 'Grid Basics'),
        ('demand-response.jpg', 'Demand Response'),
        ('renewable-energy.jpg', 'Renewable Energy'),
        ('smart-grid.jpg', 'Smart Grid')
    ]
    
    for filename, text in education_images:
        create_education_image(filename, text)
    
    # Generate reward images
    reward_images = [
        ('gift-card.png', 'Gift Card'),
        ('smart-thermostat.png', 'Thermostat'),
        ('led-bulbs.png', 'LED Bulbs'),
        ('energy-monitor.png', 'Monitor')
    ]
    
    for filename, text in reward_images:
        create_reward_image(filename, text)

if __name__ == '__main__':
    main() 