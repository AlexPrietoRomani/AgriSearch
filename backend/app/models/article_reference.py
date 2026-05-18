"""
Archivo: article_reference.py
Modificación: 2026-05-18
Autor: AgriSearch Team

Descripción:
Modelo SQLAlchemy para almacenar referencias bibliográficas extraídas de artículos
científicos incluidos en el screening. Cada fila representa una cita: un artículo
fuente (source_article_id) cita a otro artículo (cited_doi).

Este modelo alimenta el grafo de citaciones de la Fase 4 (Exploración Bibliográfica).

Estructura Interna:
    - `ArticleReference`: Registro de una referencia bibliográfica extraída.
    - Campos: source_article_id, cited_doi, cited_title, cited_authors, cited_year,
      extraction_source, is_in_project, created_at.

Entradas / Dependencias:
    - `SQLAlchemy`: ORM para la gestión de la base de datos.
    - `app.db.database.Base`: Clase base declarativa.
    - `app.models.project.Article`: Modelo de artículo para la relación FK.

Salidas / Efectos:
    - Define la tabla `article_references` en SQLite.
    - Gestiona la integridad referencial con eliminación en cascada.

Ejemplo de Integración:
    from app.models.article_reference import ArticleReference
    ref = ArticleReference(
        source_article_id="uuid-articulo-que-cita",
        cited_doi="10.1038/s41586-021-03819-2",
        cited_title="Paper title",
        extraction_source="openalex",
        is_in_project=False,
    )
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


def generate_uuid() -> str:
    """Genera una cadena de texto representando un UUID4 único."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Retorna el objeto datetime actual con zona horaria UTC."""
    return datetime.now(timezone.utc)


class ArticleReference(Base):
    """
    Representa una referencia bibliográfica extraída de un artículo incluido.
    
    Cada fila significa: "source_article_id cita a cited_doi".
    
    Atributos:
        id: UUID único de la referencia.
        source_article_id: FK al artículo que contiene la cita.
        cited_doi: DOI del artículo citado (normalizado).
        cited_title: Título del artículo citado.
        cited_authors: Autores del artículo citado (separados por comas).
        cited_year: Año de publicación del artículo citado.
        extraction_source: De dónde se obtuvo la referencia (openalex, semantic_scholar, grobid, manual).
        is_in_project: True si el DOI citado ya existe como artículo en el proyecto.
        created_at: Marca de tiempo de creación.
    """

    __tablename__ = "article_references"

    id = Column(String, primary_key=True, default=generate_uuid)
    source_article_id = Column(
        String, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    cited_doi = Column(String(255), nullable=False)
    cited_title = Column(Text, default="")
    cited_authors = Column(Text, default="")
    cited_year = Column(String(10), nullable=True)
    extraction_source = Column(
        String(100), nullable=False, default="unknown"
    )  # openalex | semantic_scholar | grobid | manual
    is_in_project = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    # Relaciones
    source_article = relationship("Article", back_populates="references")

    # Constraints e índices
    __table_args__ = (
        UniqueConstraint(
            "source_article_id", "cited_doi", name="uq_source_cited"
        ),
        Index("ix_article_references_cited_doi", "cited_doi"),
        Index("ix_article_references_source", "source_article_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ArticleReference(id={self.id!r}, "
            f"source={self.source_article_id[:8]}..., "
            f"cited_doi={self.cited_doi!r})>"
        )
