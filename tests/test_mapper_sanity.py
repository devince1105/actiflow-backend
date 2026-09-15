# tests/test_mapper_sanity.py

from sqlalchemy.orm import configure_mappers

from app.core.db import Base


def test_sqlalchemy_mapper_sanity():
    """
    一次性驗證：
    - 所有 models 都能成功 mapper
    - 所有 relationship / back_populates 對齊
    - 不存在 hidden mapper configuration error
    """

    # 1️⃣ 強制載入所有 mappers（這一步會直接炸出 relationship 錯誤）
    configure_mappers()

    # 2️⃣ 確認 models 已註冊；不連線資料庫，避免 mapper sanity
    # 測試意外碰觸正式環境。
    assert Base.metadata.tables

    # 3️⃣ 逐一檢查每個 mapper 的 relationship 是否可解析
    for mapper in Base.registry.mappers:
        for rel in mapper.relationships:
            assert rel.mapper is not None
            assert rel.direction is not None
