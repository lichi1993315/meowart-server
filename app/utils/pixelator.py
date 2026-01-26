"""Image pixelator utility for converting images to pixel art style."""
import argparse
import os
from pathlib import Path

import numpy as np
from PIL import Image
from PIL.Image import Image as PILImage


def pixelate_pil(
    img: PILImage,
    block_w: int,
    block_h: int,
    alpha_threshold: int = 128
) -> PILImage:
    """
    将 PIL Image 彩块化，并根据 alpha 阈值处理透明度。
    
    Args:
        img: 输入的 PIL Image 对象
        block_w: 色块宽度
        block_h: 色块高度
        alpha_threshold: alpha 阈值 (0-255)，块的平均 alpha 低于此值时整个像素设为透明
    
    Returns:
        彩块化后的 PIL Image
    """
    img = img.convert("RGBA")
    width, height = img.size
    
    # 计算缩小后的尺寸
    small_w = (width + block_w - 1) // block_w
    small_h = (height + block_h - 1) // block_h
    
    # 使用 numpy 处理以便精确控制 alpha
    img_array = np.array(img)
    result_array = np.zeros((small_h * block_h, small_w * block_w, 4), dtype=np.uint8)
    
    for y in range(small_h):
        for x in range(small_w):
            # 计算当前块的边界
            x1 = x * block_w
            y1 = y * block_h
            x2 = min((x + 1) * block_w, width)
            y2 = min((y + 1) * block_h, height)
            
            # 提取块
            block = img_array[y1:y2, x1:x2]
            
            # 计算 alpha 加权平均 RGB（避免透明像素影响颜色）
            alpha_channel = block[:, :, 3].astype(np.float32)
            alpha_sum = alpha_channel.sum()
            
            if alpha_sum > 0:
                # 使用 alpha 作为权重计算 RGB 平均
                weights = alpha_channel / alpha_sum
                avg_r = (block[:, :, 0] * weights).sum()
                avg_g = (block[:, :, 1] * weights).sum()
                avg_b = (block[:, :, 2] * weights).sum()
                avg_alpha = alpha_channel.mean()
                avg_rgb = (avg_r + avg_g + avg_b) / 3
            else:
                # 整个块都是透明的
                avg_r, avg_g, avg_b = 0, 0, 0
                avg_alpha = 0
                avg_rgb = 0
            
            # Determine final color based on transparency and whiteness
            is_near_white = avg_rgb > 200
            should_be_transparent = (
                alpha_sum == 0 or (is_near_white and avg_alpha < alpha_threshold)
            )

            if should_be_transparent:
                final_color = [0, 0, 0, 0]
            elif avg_alpha > 200:
                final_color = [int(avg_r), int(avg_g), int(avg_b), 255]
            else:
                final_color = [int(avg_r), int(avg_g), int(avg_b), int(avg_alpha)]
            
            # 填充结果数组中对应的块区域
            out_x1 = x * block_w
            out_y1 = y * block_h
            out_x2 = (x + 1) * block_w
            out_y2 = (y + 1) * block_h
            result_array[out_y1:out_y2, out_x1:out_x2] = final_color
    
    # 裁剪回原始尺寸 
    # todo: 增加参数：resize_to_original
    resize_to_original = False
    if resize_to_original:
        result_array = result_array[:height, :width]
    
    return Image.fromarray(result_array, 'RGBA')


def pixelate_image(
    input_path: str,
    block_w: int,
    block_h: int,
    output_path: str = None,
    alpha_threshold: int = 128
):
    """
    将图像彩块化：将图像划分为 block_w x block_h 的色块，每个色块填充为该区域的平均颜色。
    
    Args:
        input_path: 输入图片路径
        block_w: 色块宽度
        block_h: 色块高度
        output_path: 输出路径，默认为 input_stem_pixelated_WxH.png
        alpha_threshold: alpha 阈值，块平均 alpha 低于此值时整个像素设为透明
    """
    if not os.path.exists(input_path):
        print(f"❌ Error: File not found: {input_path}")
        return False

    try:
        img = Image.open(input_path).convert("RGBA")
        width, height = img.size

        print(f"🖼️  Image loaded: {width}x{height}, Block size: {block_w}x{block_h}, Alpha threshold: {alpha_threshold}")

        small_w = (width + block_w - 1) // block_w
        small_h = (height + block_h - 1) // block_h
        total_blocks = small_w * small_h
        print(f"🧩  Processing {total_blocks} blocks ({small_w}x{small_h})...")

        # 使用 pixelate_pil 处理（带 alpha 阈值）
        result_img = pixelate_pil(img, block_w, block_h, alpha_threshold)

        if not output_path:
            p = Path(input_path)
            output_path = str(p.parent / f"{p.stem}_pixelated_{block_w}x{block_h}.png")

        # 确保输出目录存在
        os.makedirs(Path(output_path).parent, exist_ok=True)

        ext = Path(output_path).suffix.lower()
        if ext in [".jpg", ".jpeg"]:
            if result_img.mode == "RGBA":
                background = Image.new("RGB", result_img.size, (255, 255, 255))
                background.paste(result_img, mask=result_img.split()[3])
                result_img = background
            else:
                result_img = result_img.convert("RGB")

        result_img.save(output_path)
        print(f"✅ Pixelated image saved to: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error processing {input_path}: {e}")
        return False


def pixelate_directory(input_dir: str, output_dir: str, block_w: int, block_h: int):
    """
    批量处理目录中的所有图片，使用相同的彩块化配置。
    
    Args:
        input_dir: 输入目录路径
        output_dir: 输出目录路径
        block_w: 色块宽度
        block_h: 色块高度
    """
    if not os.path.exists(input_dir):
        print(f"❌ Error: Input directory not found: {input_dir}")
        return
    
    if not os.path.isdir(input_dir):
        print(f"❌ Error: {input_dir} is not a directory")
        return
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 支持的图片格式
    image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp'}
    
    # 获取所有图片文件
    input_path = Path(input_dir)
    image_files = [f for f in input_path.iterdir() 
                   if f.is_file() and f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"⚠️  Warning: No image files found in {input_dir}")
        return
    
    print(f"📁 Found {len(image_files)} image(s) in {input_dir}")
    print(f"📁 Output directory: {output_dir}")
    print(f"🎨 Block size: {block_w}x{block_h}")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    for i, image_file in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] Processing: {image_file.name}")
        
        # 构建输出路径，保持原文件名和扩展名
        output_path = Path(output_dir) / image_file.name
        
        # 处理图片
        if pixelate_image(str(image_file), block_w, block_h, str(output_path)):
            success_count += 1
        else:
            fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"✅ Successfully processed: {success_count}/{len(image_files)}")
    if fail_count > 0:
        print(f"❌ Failed: {fail_count}/{len(image_files)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Image Pixelator - Pixelate an image by averaging colors in blocks.")
    parser.add_argument("input", nargs='?', help="Path to the input image (for single file mode).")
    parser.add_argument("--size", type=str, default="4,4", help="Block size as 'width,height' (default: 4,4)")
    parser.add_argument("-o", "--output", help="Output path for the pixelated image (for single file mode).")
    parser.add_argument("--input-dir", help="Input directory containing images (for batch mode).")
    parser.add_argument("--output-dir", help="Output directory for pixelated images (for batch mode).")

    args = parser.parse_args()

    try:
        bw, bh = map(int, args.size.split(","))
    except ValueError:
        print("❌ Error: Invalid size format. Use 'width,height' (e.g., 4,4)")
        exit(1)

    # 检查是否为目录批量处理模式
    if args.input_dir and args.output_dir:
        pixelate_directory(args.input_dir, args.output_dir, bw, bh)
    elif args.input_dir or args.output_dir:
        print("❌ Error: Both --input-dir and --output-dir must be specified for batch mode.")
        exit(1)
    elif args.input:
        pixelate_image(args.input, bw, bh, args.output)
    else:
        print("❌ Error: Either provide 'input' for single file mode, or --input-dir and --output-dir for batch mode.")
        parser.print_help()
        exit(1)
