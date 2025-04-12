from pydantic import BaseModel

class WebpageInfo(BaseModel):
    link: str = "https://shop.aeon.com/netsuper/"
    location_info: str = ""

class ProductInfo(BaseModel):
    name: str
    quantity: int = 1