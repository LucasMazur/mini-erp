from pathlib import Path
from uuid import uuid4
import shutil

from app.database.connection import get_database_path


SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def get_product_images_directory() -> Path:
    """Retorna a pasta de imagens vinculada à localização do banco."""
    directory = get_database_path().parent / "product_images"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def save_product_image(source_path: str) -> str:
    """Copia uma imagem para o armazenamento gerenciado pelo ERP."""
    source = Path(source_path)

    if not source.is_file():
        raise ValueError("O arquivo de imagem selecionado não foi encontrado.")

    extension = source.suffix.lower()
    if extension not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError("Formato não suportado. Use JPG, JPEG, PNG ou WEBP.")

    filename = f"{uuid4().hex}{extension}"
    destination = get_product_images_directory() / filename
    shutil.copy2(source, destination)

    return f"product_images/{filename}"


def resolve_product_image(image_path: str | None) -> Path | None:
    """Resolve o caminho relativo salvo no cadastro do produto."""
    if not image_path:
        return None

    relative_path = Path(image_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return None

    path = get_database_path().parent / relative_path
    return path if path.is_file() else None


def delete_product_image(image_path: str | None) -> None:
    """Remove uma imagem gerenciada, sem afetar arquivos externos."""
    path = resolve_product_image(image_path)
    if path is not None:
        path.unlink(missing_ok=True)
