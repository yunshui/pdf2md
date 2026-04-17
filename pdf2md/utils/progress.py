"""Progress tracking utilities for pdf2md."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pdf2md.utils.logger import get_logger

logger = get_logger()


class ProgressTracker:
    """Tracks processing progress and supports checkpointing."""

    def __init__(self, checkpoint_dir: Optional[str] = None) -> None:
        """Initialize the progress tracker.

        Args:
            checkpoint_dir: Directory to store checkpoint files.
        """
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None
        self.current_file: Optional[str] = None
        self.start_time: Optional[float] = None
        self.checkpoint_data: Dict = {}

    def start(self, file_path: str) -> None:
        """Start tracking a file.

        Args:
            file_path: Path to the file being processed.
        """
        self.current_file = file_path
        self.start_time = time.time()
        self.checkpoint_data = {
            "file_path": file_path,
            "started_at": datetime.now().isoformat(),
        }
        logger.info(f"Started processing: {file_path}")

    def update(self, progress: float, message: str = "") -> None:
        """Update progress.

        Args:
            progress: Progress value (0.0 to 1.0).
            message: Optional progress message.
        """
        if message:
            logger.info(f"Progress: {progress:.1%} - {message}")
        else:
            logger.info(f"Progress: {progress:.1%}")

    def complete(self) -> None:
        """Mark processing as complete."""
        if self.start_time:
            elapsed = time.time() - self.start_time
            logger.info(
                f"Completed processing: {self.current_file} "
                f"(took {elapsed:.2f} seconds)"
            )
        self.current_file = None
        self.start_time = None
        self.checkpoint_data = {}

    def save_checkpoint(
        self,
        file_path: str,
        total_pages: int,
        processed_pages: List[int],
        failed_pages: List[int],
        version: str = "1.0",
    ) -> Path:
        """Save checkpoint data.

        Args:
            file_path: Path to the source file.
            total_pages: Total number of pages.
            processed_pages: List of processed page numbers.
            failed_pages: List of failed page numbers.
            version: Checkpoint format version.

        Returns:
            Path to checkpoint file.
        """
        if not self.checkpoint_dir:
            self.checkpoint_dir = Path(file_path).parent

        from pdf2md.utils.file_manager import FileManager

        fm = FileManager()
        file_hash = fm.get_file_hash(file_path)

        checkpoint_path = self.checkpoint_dir / f"{Path(file_path).name}.checkpoint.json"

        checkpoint_data = {
            "file_hash": file_hash,
            "total_pages": total_pages,
            "processed_pages": processed_pages,
            "failed_pages": failed_pages,
            "timestamp": datetime.now().isoformat(),
            "version": version,
        }

        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2)

        logger.debug(f"Saved checkpoint: {checkpoint_path}")
        return checkpoint_path

    def load_checkpoint(self, file_path: str) -> Optional[Dict]:
        """Load checkpoint data.

        Args:
            file_path: Path to the source file.

        Returns:
            Checkpoint data dictionary, or None if no valid checkpoint exists.
        """
        if not self.checkpoint_dir:
            self.checkpoint_dir = Path(file_path).parent

        checkpoint_path = self.checkpoint_dir / f"{Path(file_path).name}.checkpoint.json"

        if not checkpoint_path.exists():
            logger.debug(f"No checkpoint found: {checkpoint_path}")
            return None

        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                checkpoint_data = json.load(f)

            # Verify file hash
            from pdf2md.utils.file_manager import FileManager

            fm = FileManager()
            current_hash = fm.get_file_hash(file_path)

            if checkpoint_data.get("file_hash") != current_hash:
                logger.warning(
                    f"File hash changed, checkpoint invalid: {checkpoint_path}"
                )
                return None

            logger.info(f"Loaded checkpoint: {checkpoint_path}")
            return checkpoint_data

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def remove_checkpoint(self, file_path: str) -> None:
        """Remove checkpoint file.

        Args:
            file_path: Path to the source file.
        """
        if not self.checkpoint_dir:
            self.checkpoint_dir = Path(file_path).parent

        checkpoint_path = self.checkpoint_dir / f"{Path(file_path).name}.checkpoint.json"

        if checkpoint_path.exists():
            checkpoint_path.unlink()
            logger.debug(f"Removed checkpoint: {checkpoint_path}")

    def get_processed_pages(self, file_path: str) -> List[int]:
        """Get list of processed pages from checkpoint.

        Args:
            file_path: Path to the source file.

        Returns:
            List of processed page numbers.
        """
        checkpoint_data = self.load_checkpoint(file_path)
        if checkpoint_data:
            return checkpoint_data.get("processed_pages", [])
        return []

    def get_failed_pages(self, file_path: str) -> List[int]:
        """Get list of failed pages from checkpoint.

        Args:
            file_path: Path to the source file.

        Returns:
            List of failed page numbers.
        """
        checkpoint_data = self.load_checkpoint(file_path)
        if checkpoint_data:
            return checkpoint_data.get("failed_pages", [])
        return []

    def should_process_page(self, file_path: str, page_num: int) -> bool:
        """Check if a page should be processed.

        Args:
            file_path: Path to the source file.
            page_num: Page number (1-indexed).

        Returns:
            True if page should be processed, False if already processed.
        """
        processed_pages = self.get_processed_pages(file_path)
        return page_num not in processed_pages

    def is_page_failed(self, file_path: str, page_num: int) -> bool:
        """Check if a page previously failed.

        Args:
            file_path: Path to the source file.
            page_num: Page number (1-indexed).

        Returns:
            True if page previously failed.
        """
        failed_pages = self.get_failed_pages(file_path)
        return page_num in failed_pages