"""Image processing API routes for background removal and pixelation."""
import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image

from app.utils.pixelator import pixelate_pil
from app.utils.remove_bg import remove_background_pil

router = APIRouter(prefix="/api/image", tags=["image"])


def validate_image_upload(file: UploadFile) -> None:
    """Validate that the uploaded file is an image."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")


def create_png_response(image: Image.Image, filename: str) -> Response:
    """Convert a PIL Image to a PNG response with download headers."""
    output_buffer = io.BytesIO()
    image.save(output_buffer, format="PNG")
    return Response(
        content=output_buffer.getvalue(),
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/remove-background")
async def remove_background_api(
    file: UploadFile = File(..., description="上传的图片文件"),
    pixelate: bool = Form(True, description="是否进行像素化处理"),
    block_size: int = Form(8, description="像素块大小 (正方形)"),
    alpha_threshold: int = Form(128, description="Alpha 阈值 (0-255)"),
    refine_white: bool = Form(True, description="是否使用原图过滤白色格子"),
    white_threshold: int = Form(200, description="白色判定阈值 (0-255)"),
    alpha_matting: bool = Form(False, description="是否启用 alpha matting"),
) -> Response:
    """
    抠图 + 像素化 API

    处理流程：
    1. 使用 rembg 进行背景去除
    2. 对抠图结果进行像素化处理
    3. 使用原图过滤白色格子，实现完美抠图

    返回：PNG 格式的透明背景图片
    """
    validate_image_upload(file)

    try:
        image_data = await file.read()
        original_img = Image.open(io.BytesIO(image_data))

        result = remove_background_pil(
            image=original_img,
            alpha_matting=alpha_matting,
            pixelate=pixelate,
            block_size=(block_size, block_size),
            alpha_threshold=alpha_threshold,
            refine_white=refine_white,
            white_threshold=white_threshold,
        )

        return create_png_response(result, "result.png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片处理失败: {str(e)}")


@router.post("/pixelate")
async def pixelate_api(
    file: UploadFile = File(..., description="上传的图片文件"),
    block_size: int = Form(8, description="像素块大小 (正方形)"),
    alpha_threshold: int = Form(128, description="Alpha 阈值 (0-255)"),
) -> Response:
    """
    纯像素化 API（不抠图）

    将图片按指定块大小进行像素化处理。

    返回：PNG 格式的图片
    """
    validate_image_upload(file)

    try:
        image_data = await file.read()
        img = Image.open(io.BytesIO(image_data))

        result = pixelate_pil(img, block_size, block_size, alpha_threshold)

        return create_png_response(result, "pixelated.png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片处理失败: {str(e)}")
