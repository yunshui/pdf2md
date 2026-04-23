"""Resource link management for Markdown output."""

from pathlib import Path
from typing import List, Optional

from pdf2md.extractor import ImageInfo


class Linker:
    """Manages links and references in Markdown output."""

    def __init__(self, base_path: Optional[Path] = None) -> None:
        """Initialize the linker.

        Args:
            base_path: Base path for resolving relative links.
        """
        self.base_path = base_path or Path.cwd()

    def create_image_link(
        self,
        image_info: ImageInfo,
        output_dir: Optional[Path] = None,
    ) -> str:
        """Create a Markdown link for an image.

        Args:
            image_info: ImageInfo object.
            output_dir: Output directory for relative link calculation.

        Returns:
            Markdown image link string.
        """
        if output_dir is None:
            output_dir = self.base_path

        # Get relative path
        image_path = Path(image_info.path)
        relative_path = self._get_relative_path(image_path, output_dir)

        # Format as Markdown image
        # Alt text can be derived from filename or context
        alt_text = self._get_image_alt_text(image_info)

        return f"![{alt_text}]({relative_path})"

    def create_image_link_with_size(
        self,
        image_info: ImageInfo,
        max_width: Optional[int] = None,
        output_dir: Optional[Path] = None,
    ) -> str:
        """Create an image link with size specification.

        Args:
            image_info: ImageInfo object.
            max_width: Maximum width in pixels.
            output_dir: Output directory.

        Returns:
            Markdown image link with HTML width attribute.
        """
        base_link = self.create_image_link(image_info, output_dir)

        if max_width:
            # Use HTML attributes for sizing
            alt_text = self._get_image_alt_text(image_info)
            relative_path = self._get_relative_path(
                Path(image_info.path), output_dir or self.base_path
            )
            return f'<img src="{relative_path}" alt="{alt_text}" width="{max_width}">'

        return base_link

    def create_section_link(
        self,
        section_title: str,
        section_file: Optional[str] = None,
        anchor: Optional[str] = None,
    ) -> str:
        """Create a link to a section.

        Args:
            section_title: Section title.
            section_file: Section file path (for multi-file output).
            anchor: Anchor name within file.

        Returns:
            Markdown link string.
        """
        # Create anchor from title if not provided
        if anchor is None:
            anchor = self._create_anchor(section_title)

        # Build link
        if section_file:
            link = f"{section_file}#{anchor}"
        else:
            link = f"#{anchor}"

        return f"[{section_title}]({link})"

    def create_toc_link(
        self,
        section_title: str,
        section_file: str,
        page_number: Optional[int] = None,
    ) -> str:
        """Create a table of contents link.

        Args:
            section_title: Section title.
            section_file: Section file path.
            page_number: Optional page number.

        Returns:
            Markdown link string with optional page reference.
        """
        link = self.create_section_link(section_title, section_file)

        if page_number is not None:
            return f"- {link} (page {page_number})"

        return f"- {link}"

    def _get_relative_path(self, target_path: Path, base_path: Path) -> str:
        """Get relative path from base to target.

        Args:
            target_path: Target file path.
            base_path: Base directory path.

        Returns:
            Relative path as string.
        """
        try:
            # Try direct relative path
            relative = target_path.relative_to(base_path)
            return str(relative).replace("\\", "/")  # Use forward slashes
        except ValueError:
            # Paths don't share a direct subpath relationship
            # Find common ancestor and build relative path
            try:
                # Convert to absolute paths
                target_abs = target_path.resolve()
                base_abs = base_path.resolve()

                # Get common parts
                target_parts = list(target_abs.parts)
                base_parts = list(base_abs.parts)

                # Find common ancestor
                common_parts = []
                for i, (t, b) in enumerate(zip(target_parts, base_parts)):
                    if t == b:
                        common_parts.append(t)
                    else:
                        break

                # Build relative path
                up_levels = len(base_parts) - len(common_parts)
                target_relative_parts = target_parts[len(common_parts):]

                # Add .. for each level up
                up_parts = [".."] * up_levels
                full_relative = Path(*up_parts, *target_relative_parts)

                return str(full_relative).replace("\\", "/")
            except:
                # Fallback to absolute path
                return str(target_path)

    def _get_image_alt_text(self, image_info: ImageInfo) -> str:
        """Generate alt text for an image.

        Args:
            image_info: ImageInfo object.

        Returns:
            Alt text string.
        """
        # Use filename without extension as base alt text
        filename = Path(image_info.path).stem

        # Clean up filename
        alt_text = filename.replace("_", " ").replace("-", " ").title()

        return alt_text

    def _create_anchor(self, text: str) -> str:
        """Create an anchor name from text.

        Args:
            text: Text to create anchor from.

        Returns:
            Anchor name.
        """
        # Lowercase and replace spaces with hyphens
        anchor = text.lower()

        # Remove special characters except alphanumeric and hyphens
        import re

        anchor = re.sub(r"[^a-z0-9\s-]", "", anchor)
        anchor = re.sub(r"\s+", "-", anchor)

        # Remove leading/trailing hyphens
        anchor = anchor.strip("-")

        return anchor

    def create_image_gallery(
        self,
        images: List[ImageInfo],
        output_dir: Optional[Path] = None,
        columns: int = 2,
    ) -> str:
        """Create a markdown image gallery.

        Args:
            images: List of ImageInfo objects.
            output_dir: Output directory.
            columns: Number of columns in the gallery.

        Returns:
            Markdown formatted gallery.
        """
        if not images:
            return ""

        # For now, just list images vertically
        # A more sophisticated implementation could use HTML tables or CSS
        lines = ["## Images\n"]

        for idx, image_info in enumerate(images, start=1):
            link = self.create_image_link(image_info, output_dir)
            lines.append(f"{idx}. {link}\n")

        return "\n".join(lines)

    def update_image_links(
        self,
        markdown: str,
        image_mappings: dict,
    ) -> str:
        """Update image links in markdown content.

        Args:
            markdown: Markdown content.
            image_mappings: Dictionary mapping old paths to new paths.

        Returns:
            Updated markdown content.
        """
        for old_path, new_path in image_mappings.items():
            markdown = markdown.replace(old_path, new_path)

        return markdown