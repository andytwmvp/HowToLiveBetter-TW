"""Reader-copy hash helpers for additive, independently tested navigation links."""
import hashlib


CHAPTER_TWO_CATALOG_LINK = (
    "[第2章：建立能持續的健康生活](book/ch02/README.md) · ".encode("utf-8")
)


def historical_reader_copy_sha256(path, content):
    """Hash a reader document after removing only the new Chapter 2 catalog link.

    Old cleanup records hash the pre-Chapter-2 chapter catalog. When validating
    those immutable records, normalize exactly the one additive link; any other
    catalog or wording change remains part of the digest and fails the snapshot.
    """
    if path == "locales/zh-TW/README.md":
        count = content.count(CHAPTER_TWO_CATALOG_LINK)
        if count == 1:
            content = content.replace(CHAPTER_TWO_CATALOG_LINK, b"", 1)
    return hashlib.sha256(content).hexdigest()
