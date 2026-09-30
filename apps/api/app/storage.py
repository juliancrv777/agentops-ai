from pathlib import Path
from uuid import UUID

from anyio import to_thread

from app.config import get_settings

settings = get_settings()


def _write_file(
    organization_id: UUID,
    document_id: UUID,
    filename: str,
    content: bytes,
) -> str:
    safe_name = Path(filename).name
    base = Path(settings.upload_dir)
    target_dir = base / str(organization_id) / str(document_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    target = target_dir / safe_name
    target.write_bytes(content)
    return str(target)


async def save_upload(
    organization_id: UUID,
    document_id: UUID,
    filename: str,
    content: bytes,
) -> str:
    return await to_thread.run_sync(
        _write_file,
        organization_id,
        document_id,
        filename,
        content,
    )
