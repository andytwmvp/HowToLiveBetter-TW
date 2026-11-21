"""Reader-copy hash helpers for additive, independently tested navigation links."""
import hashlib


ADDITIVE_CHAPTER_CATALOG_LINKS = (
    "[第2章：建立能持續的健康生活](book/ch02/README.md) · ".encode("utf-8"),
    "[第5章：省下不必要支出，保護財務選擇](book/ch05/README.md) · ".encode("utf-8"),
    "[第22章：休閒與紓壓](book/ch22/README.md) · ".encode("utf-8"),
)
TERMINAL_ADDITIVE_CHAPTER_LINK = (
    "[第34章：家庭用藥安全](book/ch34/README.md)".encode("utf-8")
)


def historical_reader_copy_sha256(path, content):
    """Hash a reader document after removing links added after its snapshot.

    Old cleanup records predate later additive chapter links. When validating
    those immutable records, normalize only the exact known links; any other
    catalog or wording change remains part of the digest.
    """
    if path == "locales/zh-TW/README.md":
        for link in ADDITIVE_CHAPTER_CATALOG_LINKS:
            if content.count(link) == 1:
                content = content.replace(link, b"", 1)
        if content.count(TERMINAL_ADDITIVE_CHAPTER_LINK) == 1:
            content = content.replace(
                " · ".encode("utf-8") + TERMINAL_ADDITIVE_CHAPTER_LINK,
                b"",
                1,
            )
    return hashlib.sha256(content).hexdigest()
