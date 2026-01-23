"""Background removal utility using rembg library."""
import io
from pathlib import Path

import numpy as np
from PIL import Image
from rembg import remove

from .pixelator import pixelate_pil


def _apply_pixelation(
    result: Image.Image,
    original: Image.Image,
    block_size: tuple[int, int],
    alpha_threshold: int,
    refine_white: bool,
    white_threshold: int,
) -> Image.Image:
    """Apply pixelation and optional white refinement to the result image."""
    result = pixelate_pil(result, block_size[0], block_size[1], alpha_threshold)
    if refine_white:
        result = refine_with_original(
            result, original, block_size[0], block_size[1], white_threshold
        )
    return result


def refine_with_original(
    pixelated_mask_img: Image.Image,
    original_img: Image.Image,
    block_w: int,
    block_h: int,
    white_threshold: int = 200,
) -> Image.Image:
    """
    基于原图生成完美抠图结果。
    
    原理：
    1. 从抠图+像素化后的图像生成 mask（0=透明，1=不透明的格子）
    2. 对原图进行像素化处理
    3. 遍历每个格子：
       - 如果 mask 为透明 且 原图该格子为白色 → 设为透明
       - 否则 → 保留原图像素化的颜色（完全不透明）
    
    这样最终效果是：用 mask 来决定边缘的透明区域，但保留原图的真实颜色。
    
    Args:
        pixelated_mask_img: 抠图后像素化的图像 (用于提取 mask)
        original_img: 原始图像
        block_w: 格子宽度
        block_h: 格子高度  
        white_threshold: 白色判定阈值，RGB 平均值高于此值视为白色
    
    Returns:
        基于原图的完美抠图 PIL Image
    """
    pixelated_mask_img = pixelated_mask_img.convert("RGBA")
    original_img = original_img.convert("RGB")
    
    width, height = pixelated_mask_img.size
    orig_width, orig_height = original_img.size
    
    # 确保尺寸匹配（如果不匹配，缩放原图）
    if orig_width != width or orig_height != height:
        original_img = original_img.resize((width, height), Image.LANCZOS)
    
    # 计算格子数量
    grid_w = (width + block_w - 1) // block_w
    grid_h = (height + block_h - 1) // block_h
    
    # 转为 numpy 数组
    mask_arr = np.array(pixelated_mask_img)
    original_arr = np.array(original_img)
    
    # 创建结果数组（基于原图大小，带 alpha 通道）
    result_arr = np.zeros((height, width, 4), dtype=np.uint8)
    
    for gy in range(grid_h):
        for gx in range(grid_w):
            # 计算当前格子的边界
            x1 = gx * block_w
            y1 = gy * block_h
            x2 = min((gx + 1) * block_w, width)
            y2 = min((gy + 1) * block_h, height)
            
            # 获取 mask 中该格子的 alpha 值（取第一个像素即可，因为像素化后都一样）
            mask_alpha = mask_arr[y1, x1, 3]
            
            # 获取原图该格子的平均颜色
            orig_block = original_arr[y1:y2, x1:x2]
            avg_r = orig_block[:, :, 0].mean()
            avg_g = orig_block[:, :, 1].mean()
            avg_b = orig_block[:, :, 2].mean()
            avg_rgb = (avg_r + avg_g + avg_b) / 3
            
            # 判断是否应该透明
            # mask 为透明 且 原图为白色 → 透明
            if mask_alpha <= 240 and avg_rgb >= white_threshold:
                # 设为透明
                result_arr[y1:y2, x1:x2] = [0, 0, 0, 0]
            else:
                # 保留原图的像素化颜色，完全不透明
                result_arr[y1:y2, x1:x2] = [int(avg_r), int(avg_g), int(avg_b), 255]
    
    return Image.fromarray(result_arr, 'RGBA')


def remove_background(
    input_path: str | Path,
    output_path: str | Path | None = None,
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    alpha_matting_erode_size: int = 10,
    pixelate: bool = False,
    block_size: tuple[int, int] = (4, 4),
    alpha_threshold: int = 128,
    refine_white: bool = True,
    white_threshold: int = 240,
) -> Path:
    """
    Remove background from an image.
    
    Args:
        input_path: Path to the input image file.
        output_path: Path for the output image. If None, will create a new file
                    with '_nobg' suffix in the same directory.
        alpha_matting: Enable alpha matting for better edge quality.
        alpha_matting_foreground_threshold: Foreground threshold for alpha matting.
        alpha_matting_background_threshold: Background threshold for alpha matting.
        alpha_matting_erode_size: Erode size for alpha matting.
        pixelate: Enable pixelation after background removal.
        block_size: Tuple of (width, height) for pixelation blocks.
        alpha_threshold: Alpha threshold for pixelation (0-255).
        refine_white: 使用原图过滤白色格子，实现完美抠图（仅当 pixelate=True 时有效）。
        white_threshold: 白色判定阈值，RGB 平均值高于此值视为白色（默认 240）。
    
    Returns:
        Path to the output image file.
    
    Example:
        >>> from app.utils.remove_bg import remove_background
        >>> output = remove_background("input.jpg")
        >>> print(f"Background removed: {output}")
        >>> # With pixelation
        >>> output = remove_background("input.jpg", pixelate=True, block_size=(8, 8))
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Generate output path if not provided
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_nobg.png"
    else:
        output_path = Path(output_path)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Read input image
    with open(input_path, "rb") as f:
        input_data = f.read()
    
    # Remove background
    output_data = remove(
        input_data,
        alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
        alpha_matting_background_threshold=alpha_matting_background_threshold,
        alpha_matting_erode_size=alpha_matting_erode_size,
    )
    
    if pixelate:
        original_img = Image.open(io.BytesIO(input_data))
        result_img = Image.open(io.BytesIO(output_data))
        result_img = _apply_pixelation(
            result_img, original_img, block_size, alpha_threshold, refine_white, white_threshold
        )
        img_buffer = io.BytesIO()
        result_img.save(img_buffer, format="PNG")
        output_data = img_buffer.getvalue()
    
    # Save output image
    with open(output_path, "wb") as f:
        f.write(output_data)
    
    return output_path


def remove_background_bytes(
    image_bytes: bytes,
    alpha_matting: bool = False,
    pixelate: bool = False,
    block_size: tuple[int, int] = (4, 4),
    alpha_threshold: int = 128,
    refine_white: bool = True,
    white_threshold: int = 240,
) -> bytes:
    """
    Remove background from image bytes.

    Args:
        image_bytes: Input image as bytes.
        alpha_matting: Enable alpha matting for better edge quality.
        pixelate: Enable pixelation after background removal.
        block_size: Tuple of (width, height) for pixelation blocks.
        alpha_threshold: Alpha threshold for pixelation.
        refine_white: Use original image to filter white blocks (only when pixelate=True).
        white_threshold: White threshold value (default 240).

    Returns:
        Output image as bytes (PNG format with transparency).

    Example:
        >>> with open("input.jpg", "rb") as f:
        ...     input_bytes = f.read()
        >>> output_bytes = remove_background_bytes(input_bytes)
        >>> with open("output.png", "wb") as f:
        ...     f.write(output_bytes)
    """
    original_img = Image.open(io.BytesIO(image_bytes))
    result = remove_background_pil(
        image=original_img,
        alpha_matting=alpha_matting,
        pixelate=pixelate,
        block_size=block_size,
        alpha_threshold=alpha_threshold,
        refine_white=refine_white,
        white_threshold=white_threshold,
    )
    output_buffer = io.BytesIO()
    result.save(output_buffer, format="PNG")
    return output_buffer.getvalue()


def remove_background_pil(
    image: Image.Image,
    alpha_matting: bool = False,
    pixelate: bool = False,
    block_size: tuple[int, int] = (4, 4),
    alpha_threshold: int = 128,
    refine_white: bool = True,
    white_threshold: int = 240,
) -> Image.Image:
    """
    Remove background from a PIL Image object.

    Args:
        image: Input PIL Image.
        alpha_matting: Enable alpha matting for better edge quality.
        pixelate: Enable pixelation after background removal.
        block_size: Tuple of (width, height) for pixelation blocks.
        alpha_threshold: Alpha threshold for pixelation.
        refine_white: Use original image to filter white blocks (only when pixelate=True).
        white_threshold: White threshold value (default 240).

    Returns:
        Output PIL Image with transparent background.

    Example:
        >>> from PIL import Image
        >>> img = Image.open("input.jpg")
        >>> result = remove_background_pil(img)
        >>> result.save("output.png")
        >>> # With pixelation
        >>> result = remove_background_pil(img, pixelate=True, block_size=(8, 8))
    """
    img_buffer = io.BytesIO()
    image.save(img_buffer, format="PNG")
    output_bytes = remove(img_buffer.getvalue(), alpha_matting=alpha_matting)
    result = Image.open(io.BytesIO(output_bytes))

    if pixelate:
        result = _apply_pixelation(
            result, image, block_size, alpha_threshold, refine_white, white_threshold
        )

    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python remove_bg.py <input_image> [output_image]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = remove_background(input_file, output_file)
    print(f"Background removed successfully: {result}")
