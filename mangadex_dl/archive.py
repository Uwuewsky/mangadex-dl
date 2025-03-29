"""
Mangadex-dl: archive.py
Functions for archiving the manga directory.
"""

import shutil
import zipfile
from pathlib import Path

import pymupdf
from natsort import natsorted


def init_archive_mode(args):
    """Archiving mode for specified paths"""
    print(f"Mode: {args.archive} | "
          f"Format: {args.ext} | "
          f"Keep original files: {args.keep}")

    if not args.archive:
        print("Error: Archiving mode not specified!\n"
              "Change the 'archive' setting in the config.toml file!")
        return

    for url in args.manga_urls:
        d = Path(url)
        if not d.is_dir():
            print(f"'{d}' is not directory. Skipped.")
            continue
        archive_manga(d, args.archive, args.keep, args.ext)

    print("\nArchived successfully!")


def archive_manga(manga_dir: Path, archive_mode: str, is_keep: bool, ext: str,
                  gui: dict = {}) -> None:

    dir_list = _find_directories(manga_dir, archive_mode, ext)

    dir_archived = 0
    dir_max = len(dir_list)

    if dir_max == 0:
        print("Looks like there is nothing to archive.", end="", flush=True)
        return

    for directory in dir_list:
        _archive_directory(directory, ext, archive_mode, is_keep)
        dir_archived += 1

        if gui.get("set"):
            gui["progress_chapter"].set(
                (dir_archived/dir_max)*100)
            gui["progress_chapter_text"].set(
                f"[ {dir_archived} / {dir_max} ]")
        else:
            print(f"\r  Archiving [{dir_archived:3}/{dir_max:3}]...", end="")


def _archive_directory(directory: Path, ext: str, archive_mode: str,
                       is_keep: bool = True) -> None:
    arc_name = directory.with_suffix(directory.suffix + f".{ext}")

    if ext == "pdf":
        _pdf_dir(arc_name, directory, archive_mode)
    else:
        _zip_dir(arc_name, directory)

    if not is_keep:
        shutil.rmtree(directory)


def _pdf_dir(arc_name: str, directory: Path, archive_mode: str) -> None:
    doc = pymupdf.open()
    toc = []  # table of content

    page_num = 1

    def chapter2pdf(d: Path, level: int = 1) -> None:
        nonlocal page_num
        toc.append([level, d.name, page_num])
        for filename in natsorted(d.glob("**/*")):
            if not filename.is_file():
                continue
            page_num += 1
            img = pymupdf.open(filename)
            rect = img[0].rect
            img.close()
            page = doc.new_page(width=rect.width, height=rect.height)
            page.insert_image(rect, filename=filename)

    def volume2pdf(d: Path, level: int = 1) -> None:
        for c_dir in natsorted(d.glob("*")):
            if not c_dir.is_dir():
                continue
            chapter2pdf(c_dir, level)

    def manga2pdf(d: Path) -> None:
        l = natsorted(d.glob("*"))
        for v_dir in l:
            if not v_dir.is_dir():
                continue
            if len(l) > 1:
                toc.append([1, v_dir.name, page_num])
                volume2pdf(v_dir, 2)
            else:
                volume2pdf(v_dir, 1)

    if archive_mode == "chapter":
        chapter2pdf(directory)
    elif archive_mode == "volume":
        volume2pdf(directory)
    else:
        manga2pdf(directory)

    doc.set_toc(toc)
    doc.metadata["creator"] = "mangadex_dl"
    doc.metadata["creationDate"] = pymupdf.get_pdf_now()
    doc.ez_save(arc_name)
    doc.close()


def _zip_dir(arc_name: str, directory: Path) -> None:
    with zipfile.ZipFile(arc_name, mode="w",
                         compression=zipfile.ZIP_STORED,
                         allowZip64=True) as zip_file:
        for filename in natsorted(directory.glob("**/*")):
            zip_file.write(filename, filename.relative_to(directory))


def _find_directories(manga_dir: Path, archive_mode: str,
                      ext: str) -> list[Path]:
    dir_list = []

    if archive_mode == "manga":
        # archive whole manga dir
        dir_list.append(manga_dir)
    elif archive_mode == "volume":
        # archive volume directories
        dir_list += manga_dir.glob("*/")
    else:
        # archive chapter directories
        dir_list += manga_dir.glob("*/*/")

    # sort and skip directories that have already been archived before
    dir_list = natsorted(list(filter(
        lambda f: not (f.with_suffix("."+ext).is_file()),
        dir_list)))
    return dir_list
