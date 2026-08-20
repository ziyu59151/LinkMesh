from __future__ import annotations

from pathlib import Path
import re
import textwrap


INPUT = Path("History.md")
OUTPUT = Path("History.reflowed.md")
WIDTH = 88


def is_fenced_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def is_heading(line: str) -> bool:
    return bool(re.match(r"^\s{0,3}#{1,6}\s", line))


def is_numbered_item_start(line: str) -> bool:
    return bool(re.match(r"^\s*\d+\.\s+", line))


def is_bullet_start(line: str) -> bool:
    return bool(re.match(r"^\s*([-*+])\s+", line))


def should_preserve_block(lines: list[str]) -> bool:
    """判断一个空行分隔块是否应保持原样。"""
    if not lines:
        return True

    if any(is_fenced_line(line) for line in lines):
        return True

    if any(is_table_line(line) for line in lines):
        return True

    if any("<<<<<<<" in line or "=======" in line or ">>>>>>>" in line for line in lines):
        return True

    if any(line.lstrip().startswith(("<", ">")) for line in lines):
        return True

    return False


def join_text(lines: list[str]) -> str:
    """
    将原段落的物理行合并为逻辑文本。

    History.md 中的普通段落是自然语言文本；物理换行只承担显示作用。
    各行首尾空白被去除，行之间补一个普通空格。
    """
    return " ".join(line.strip() for line in lines).strip()


def wrap_plain_text(text: str, width: int = WIDTH) -> list[str]:
    return textwrap.wrap(
        text,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
        replace_whitespace=False,
        drop_whitespace=True,
    )


def reflow_block(lines: list[str]) -> list[str]:
    if should_preserve_block(lines):
        return lines

    if not lines:
        return lines

    # 标题单独保持原样。
    if len(lines) == 1 and is_heading(lines[0]):
        return lines

    first = lines[0]
    text = join_text(lines)

    # 普通标题或空内容不处理。
    if not text or is_heading(first):
        return lines

    # 识别 Markdown 有序列表项。
    numbered = re.match(r"^(\s*)(\d+\.\s+)(.*)$", text)
    if numbered:
        prefix = numbered.group(1) + numbered.group(2)
        body = numbered.group(3)
        wrapped = textwrap.wrap(
            body,
            width=max(20, WIDTH - len(prefix)),
            initial_indent=prefix,
            subsequent_indent=" " * len(prefix),
            break_long_words=False,
            break_on_hyphens=False,
            replace_whitespace=False,
            drop_whitespace=True,
        )
        return wrapped

    # 识别无序列表项。
    bullet = re.match(r"^(\s*)([-*+]\s+)(.*)$", text)
    if bullet:
        prefix = bullet.group(1) + bullet.group(2)
        body = bullet.group(3)
        return textwrap.wrap(
            body,
            width=max(20, WIDTH - len(prefix)),
            initial_indent=prefix,
            subsequent_indent=" " * len(prefix),
            break_long_words=False,
            break_on_hyphens=False,
            replace_whitespace=False,
            drop_whitespace=True,
        )

    return wrap_plain_text(text)


def split_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
            blocks.append([line])
        else:
            current.append(line)

    if current:
        blocks.append(current)

    return blocks


def main() -> None:
    original = INPUT.read_text(encoding="utf-8")
    lines = original.splitlines()

    output_lines: list[str] = []
    changed_blocks = 0
    preserved_blocks = 0

    for block in split_blocks(lines):
        if block == [""]:
            output_lines.append("")
            continue

        new_block = reflow_block(block)
        output_lines.extend(new_block)

        if new_block != block:
            changed_blocks += 1
        else:
            preserved_blocks += 1

    result = "\n".join(output_lines) + "\n"
    OUTPUT.write_text(result, encoding="utf-8", newline="\n")

    print(f"输入文件: {INPUT}")
    print(f"输出文件: {OUTPUT}")
    print(f"重新换行的文本块: {changed_blocks}")
    print(f"保持原样的文本块: {preserved_blocks}")
    print("原文件未被修改。")


if __name__ == "__main__":
    main()
