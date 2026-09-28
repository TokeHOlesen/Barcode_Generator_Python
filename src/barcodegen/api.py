import io
from typing import Annotated
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from .__main__ import BarcodeChecksumError, generate_barcode_image


class BarcodeParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    barcode_number: str = Field(description="8-digit EAN-8, 12-digit UPC-A, or 13-digit EAN-13 number")
    unit_width: int = Field(default=10, gt=0, description="Width of one barcode encoding unit in pixels")
    height: int = Field(default=200, gt=0, description="Height of the barcode bars in pixels")
    notch: int = Field(default=0, ge=0, description="Height of the guard-bar notches in pixels")
    border: int = Field(default=0, ge=0, description="Default quiet-area width in pixels")
    left_border: int | None = Field(default=None, ge=0)
    right_border: int | None = Field(default=None, ge=0)
    top_border: int | None = Field(default=None, ge=0)
    bottom_border: int | None = Field(default=None, ge=0)
    digits: bool = Field(default=False, description="Draw human-readable digits underneath the barcode")
    
    
app = FastAPI(title="Barcode Generator", description="Generates EAN-8, EAN-13 and UPC-A barcodes.")


@app.get("/barcode",
         response_class=Response,
         responses={200: {"content": {"image/png": {}}, "description": "Generated barcode image"}})

def barcode(params: Annotated[BarcodeParameters, Query()]):
    try:
        image = generate_barcode_image(
            barcode=params.barcode_number,
            unit_width=params.unit_width,
            barcode_height=params.height,
            notch_height=params.notch,
            border_width=params.border,
            left_border=params.left_border,
            right_border=params.right_border,
            top_border=params.top_border,
            bottom_border=params.bottom_border,
            draw_digits=params.digits
        )

    except BarcodeChecksumError as e:
        raise HTTPException(status_code=422, detail={
            "message": "Barcode checksum is incorrect.",
            "incorrect_barcode": e.barcode,
            "corrected_barcode": e.corrected_barcode})

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    filename = f"barcode_{params.barcode_number}.png"
    return Response(content=buffer.getvalue(), media_type="image/png", headers={"Content-Disposition": f'inline; filename="{filename}"'})
