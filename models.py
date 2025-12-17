"""
ショッピングアプリケーション用のデータモデル

イオンネットスーパーでの買い物自動化に使用するデータ構造を定義します。
"""

your_address = "東京都新宿区"  # ここにあなたの住所を入力してください

from pydantic import BaseModel, Field, field_validator


class WebpageInfo(BaseModel):
    """
    ネットスーパーのWebページ情報

    Attributes:
        link: ネットスーパーのURL
        location_info: 配送先の位置情報（オプション）
    """
    link: str = Field(
        default="https://shop.aeon.com/netsuper/",
        description="ネットスーパーのURL"
    )
    location_info: str = Field(
        default=your_address,
        description="配送先住所情報"
    )

    @field_validator('link')
    @classmethod
    def validate_link(cls, v: str) -> str:
        """URLが有効な形式であることを検証"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URLはhttp://またはhttps://で始まる必要があります')
        return v


class ProductInfo(BaseModel):
    """
    商品情報

    Attributes:
        name: 商品名
        quantity: 購入数量（デフォルト: 1）
    """
    name: str = Field(
        ...,
        description="商品名",
        min_length=1
    )
    quantity: int = Field(
        default=1,
        description="購入数量",
        ge=1,
        le=99
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """商品名が空でないことを検証"""
        if not v or not v.strip():
            raise ValueError('商品名は空にできません')
        return v.strip()
