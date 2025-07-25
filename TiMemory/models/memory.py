from sqlalchemy import String, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, declarative_base
from sqlalchemy.sql import func
from tidb_vector.sqlalchemy import VectorType

Base = declarative_base()

class Memory(Base):
    __tablename__ = 'memories'
    
    id: Mapped[int] = mapped_column(String(36), primary_key=True)
    vector: Mapped[list[float]] = mapped_column(VectorType(dim=1536))  # Default OpenAI embedding dim
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    memory_attributes: Mapped[JSON] = mapped_column(JSON)