#!/usr/bin/env python3
"""
Универсальный конвертер толковых словарей в морфологические.

Читает словарь в любом формате (DSL, DSL.dz, StarDict),
добавляет ко ВСЕМ статьям полный список словоформ как альтернативные
заголовки, и сохраняет готовый словарь в DSL и/или StarDict.

Результат загружается в GoldenDict, Lingvo или любую другую программу —
поиск по любой форме слова работает «из коробки».

Использование:
  python morph_dict_convert.py <путь_к_словарю> [опции]

Примеры:
  python morph_dict_convert.py /путь/к/словарю.dsl
  python morph_dict_convert.py /путь/к/словарю/ --name МойСловарь --format dsl
  python morph_dict_convert.py /путь/к/словарю.ifo --format both --out /куда/сохранить/

Опции:
  --name    Название словаря (по умолчанию берётся из файла)
  --format  Формат вывода: dsl, stardict, both (по умолчанию: both)
  --out     Папка для результата (по умолчанию: рядом с исходным файлом)
"""

import argparse
import gzip
import os
import re
import struct
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Морфология
# ---------------------------------------------------------------------------
try:
    import pymorphy3
    _morph = pymorphy3.MorphAnalyzer()

    def get_all_forms(word: str) -> list[str]:
        """Все уникальные словоформы для слова (включая само слово)."""
        word = word.strip()
        if not word:
            return []
        parses = _morph.parse(word)
        if not parses:
            return [word]
        # берём разбор с наибольшим score
        p = parses[0]
        forms = {f.word for f in p.lexeme}
        forms.add(word.lower())
        return sorted(forms)

except ImportError:
    sys.exit("Ошибка: установите pymorphy3:\n  pip install pymorphy3 pymorphy3-dicts-ru")


# ---------------------------------------------------------------------------
# Вспомогательные
# ---------------------------------------------------------------------------

def _open_maybe_gz(path: Path, mode="rb"):
    if path.suffix == ".dz" or str(path).endswith(".dsl.dz"):
        return gzip.open(path, mode)
    return open(path, mode)


def _strip_dsl_markup(text: str) -> str:
    """Удаляет DSL-теги, оставляет читаемый текст."""
    text = re.sub(r'\[/?[a-zA-Z][^\]]*\]', '', text)
    text = re.sub(r'\{\{.*?\}\}', '', text)
    text = re.sub(r'\\\[.*?\\\]', '', text)
    text = re.sub(r"\['/?\]", '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def _strip_html(text: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', text)
    for ent, ch in [('&lt;','<'),('&gt;','>'),('&amp;','&'),('&nbsp;',' ')]:
        text = text.replace(ent, ch)
    return re.sub(r'[ \t]+', ' ', text).strip()


# ===========================================================================
# Парсеры входных форматов
# ===========================================================================

def parse_dsl(path: Path):
    """
    Генератор: (headword: str, raw_definition_lines: list[str]).
    raw_definition_lines — строки с оригинальной DSL-разметкой (для DSL-вывода)
    и stripped-текст (для StarDict).
    Возвращает кортеж (headword, dsl_lines, plain_text).
    """
    with _open_maybe_gz(path, 'rb') as f:
        bom = f.read(3)

    encoding = 'utf-16' if bom[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8'

    with _open_maybe_gz(path, 'rb') as raw:
        content = raw.read().decode(encoding, errors='replace')

    current_headword = None
    dsl_lines = []

    for line in content.splitlines():
        # заголовок: не начинается с таба/пробела/#
        if line and not line[0] in ('\t', ' ', '#'):
            if current_headword is not None and dsl_lines:
                plain = '\n'.join(_strip_dsl_markup(l.strip()) for l in dsl_lines if l.strip())
                yield current_headword, dsl_lines[:], plain
            current_headword = line.strip()
            dsl_lines = []
        elif current_headword is not None and line and line[0] in ('\t', ' '):
            dsl_lines.append(line)

    if current_headword is not None and dsl_lines:
        plain = '\n'.join(_strip_dsl_markup(l.strip()) for l in dsl_lines if l.strip())
        yield current_headword, dsl_lines[:], plain


def parse_dsl_meta(path: Path) -> dict:
    """Читает метаданные (#NAME, #INDEX_LANGUAGE и т.д.) из DSL."""
    meta = {}
    with _open_maybe_gz(path, 'rb') as f:
        bom = f.read(3)
    encoding = 'utf-16' if bom[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8'
    with _open_maybe_gz(path, 'rb') as f:
        for raw_line in f:
            try:
                line = raw_line.decode(encoding, errors='replace').strip()
            except Exception:
                break
            if not line:
                continue
            if not line.startswith('#'):
                break
            m = re.match(r'#(\w+)\s+"?([^"]*)"?', line)
            if m:
                meta[m.group(1)] = m.group(2)
    return meta


def parse_stardict(ifo_path: Path):
    """
    Генератор: (headword, dsl_lines=[], plain_text).
    StarDict не имеет DSL-разметки, dsl_lines будет пустым.
    """
    meta = {}
    with open(ifo_path, encoding='utf-8') as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                meta[k.strip()] = v.strip()

    base = ifo_path.with_suffix('')
    idx_gz = base.with_suffix('.idx.gz')
    idx    = base.with_suffix('.idx')
    if idx_gz.exists():
        with gzip.open(idx_gz, 'rb') as f:
            idx_data = f.read()
    else:
        with open(idx, 'rb') as f:
            idx_data = f.read()

    dict_dz = Path(str(base) + '.dict.dz')
    dict_f  = base.with_suffix('.dict')

    def read_dict(offset, size):
        if dict_dz.exists():
            with gzip.open(dict_dz, 'rb') as f:
                f.seek(offset)
                return f.read(size)
        with open(dict_f, 'rb') as f:
            f.seek(offset)
            return f.read(size)

    seq = meta.get('sametypesequence', 'm')
    i = 0
    while i < len(idx_data):
        end = idx_data.index(b'\x00', i)
        try:
            word = idx_data[i:end].decode('utf-8')
        except UnicodeDecodeError:
            word = idx_data[i:end].decode('latin-1')
        offset = struct.unpack('>I', idx_data[end+1:end+5])[0]
        size   = struct.unpack('>I', idx_data[end+5:end+9])[0]
        i = end + 9

        raw = read_dict(offset, size).decode('utf-8', errors='replace')
        plain = _strip_html(raw) if seq in ('x', 'h') else raw.strip()
        yield word, [], plain  # нет DSL-строк


# ---------------------------------------------------------------------------
# Автоопределение формата
# ---------------------------------------------------------------------------

def detect_and_parse(path: Path):
    """Возвращает (генератор статей, метаданные dict, путь к файлу)."""
    if path.is_file():
        if path.suffix == '.dsl' or str(path).endswith('.dsl.dz'):
            return parse_dsl(path), parse_dsl_meta(path), path
        if path.suffix == '.ifo':
            meta = {}
            with open(path, encoding='utf-8') as f:
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        meta[k] = v
            meta['NAME'] = meta.get('bookname', path.stem)
            return parse_stardict(path), meta, path
        raise ValueError(f"Неизвестный формат: {path.suffix}")

    if path.is_dir():
        for p in path.iterdir():
            if p.suffix == '.ifo':
                return detect_and_parse(p)
        for p in path.iterdir():
            if p.suffix == '.dsl' or str(p).endswith('.dsl.dz'):
                return detect_and_parse(p)

    raise ValueError(f"Не удалось определить формат словаря: {path}")


# ===========================================================================
# Запись в DSL
# ===========================================================================

def write_dsl(entries, dict_name: str, out_path: Path, has_dsl: bool):
    """
    entries: список (headword, dsl_lines, plain_text, all_forms)
    has_dsl: True если оригинал был DSL (сохраняем разметку), иначе plain text
    """
    print(f"  Запись DSL: {out_path}")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f'#NAME\t"{dict_name} (морфо)"\n')
        f.write('#INDEX_LANGUAGE\t"Russian"\n')
        f.write('#CONTENTS_LANGUAGE\t"Russian"\n')
        f.write('\n')

        for headword, dsl_lines, plain, forms in entries:
            # первый заголовок — оригинальный
            f.write(headword + '\n')
            # остальные формы
            for form in forms:
                if form != headword.lower():
                    f.write(form + '\n')
            # определение
            if has_dsl and dsl_lines:
                for line in dsl_lines:
                    f.write(line + '\n')
            else:
                # plain text → обернуть в DSL-тег
                for line in plain.split('\n'):
                    line = line.strip()
                    if line:
                        f.write(f'\t[m1]{line}[/m]\n')
            f.write('\n')

    print(f"  ✓ DSL готов: {out_path}  ({out_path.stat().st_size // 1024} КБ)")


# ===========================================================================
# Запись в StarDict
# ===========================================================================

def write_stardict(entries, dict_name: str, out_base: Path):
    """
    entries: список (headword, dsl_lines, plain_text, all_forms)
    Создаёт .ifo + .idx + .dict
    """
    ifo_path  = out_base.with_suffix('.ifo')
    idx_path  = out_base.with_suffix('.idx')
    dict_path = out_base.with_suffix('.dict')

    print(f"  Запись StarDict: {out_base}.*")

    idx_buf  = bytearray()
    dict_buf = bytearray()
    word_count = 0

    for headword, dsl_lines, plain, forms in entries:
        # определение
        definition = plain.encode('utf-8')
        offset = len(dict_buf)
        size   = len(definition)
        dict_buf.extend(definition)

        # все формы → отдельные idx-записи, все указывают на одно определение
        all_headwords = [headword] + [f for f in forms if f != headword.lower()]
        seen = set()
        for hw in all_headwords:
            hw_lower = hw.lower()
            if hw_lower in seen:
                continue
            seen.add(hw_lower)
            idx_buf.extend(hw.encode('utf-8'))
            idx_buf.extend(b'\x00')
            idx_buf.extend(struct.pack('>I', offset))
            idx_buf.extend(struct.pack('>I', size))
            word_count += 1

    # сортируем idx (StarDict требует сортировки)
    records = []
    i = 0
    data = bytes(idx_buf)
    while i < len(data):
        end = data.index(b'\x00', i)
        word = data[i:end]
        offset = struct.unpack('>I', data[end+1:end+5])[0]
        size   = struct.unpack('>I', data[end+5:end+9])[0]
        records.append((word, offset, size))
        i = end + 9

    records.sort(key=lambda r: r[0].decode('utf-8', errors='replace').lower())

    idx_sorted = bytearray()
    for word, offset, size in records:
        idx_sorted.extend(word)
        idx_sorted.extend(b'\x00')
        idx_sorted.extend(struct.pack('>I', offset))
        idx_sorted.extend(struct.pack('>I', size))

    with open(dict_path, 'wb') as f:
        f.write(dict_buf)
    with open(idx_path, 'wb') as f:
        f.write(idx_sorted)
    with open(ifo_path, 'w', encoding='utf-8') as f:
        f.write("StarDict's dict ifo file\n")
        f.write("version=2.4.2\n")
        f.write(f"wordcount={word_count}\n")
        f.write(f"idxfilesize={len(idx_sorted)}\n")
        f.write(f"bookname={dict_name} (морфо)\n")
        f.write("sametypesequence=m\n")

    print(f"  ✓ StarDict готов: {ifo_path.parent / ifo_path.stem}.*  ({word_count} записей)")


# ===========================================================================
# Главная логика
# ===========================================================================

def convert(input_path: Path, dict_name: str, out_dir: Path, fmt: str):
    gen, meta, resolved = detect_and_parse(input_path)
    has_dsl = resolved.suffix == '.dsl' or str(resolved).endswith('.dsl.dz')

    if dict_name is None:
        dict_name = meta.get('NAME') or meta.get('bookname') or resolved.stem

    print(f"\nСловарь:  {dict_name}")
    print(f"Источник: {resolved}")
    print(f"Формат:   {'DSL' if has_dsl else 'StarDict/plain'} → {fmt.upper()}")
    print(f"Вывод:    {out_dir}\n")

    # Собираем все статьи в память (нужно для StarDict — требует сортировки)
    entries = []
    total = 0
    skipped = 0

    for headword, dsl_lines, plain in gen:
        hw = headword.strip()
        if not hw or hw.startswith('#'):
            continue

        # генерируем формы для каждого слова в заголовке
        # (заголовок может быть словосочетанием)
        words = re.split(r'[\s,;/\-]+', hw)
        all_forms = set()
        for w in words:
            w_clean = re.sub(r'[^а-яёА-ЯЁ]', '', w)
            if len(w_clean) >= 2:
                for f in get_all_forms(w_clean):
                    all_forms.add(f)

        if not all_forms:
            all_forms = {hw.lower()}

        entries.append((hw, dsl_lines, plain, sorted(all_forms)))
        total += 1
        if total % 5000 == 0:
            print(f"  обработано: {total} статей...")

    print(f"\n  Всего статей: {total}")
    print(f"  Запись результата...")

    safe_name = re.sub(r'[^\w\-]', '_', dict_name)

    if fmt in ('dsl', 'both'):
        dsl_out = out_dir / f"{safe_name}_morph.dsl"
        write_dsl(entries, dict_name, dsl_out, has_dsl)

    if fmt in ('stardict', 'both'):
        sd_base = out_dir / f"{safe_name}_morph"
        write_stardict(entries, dict_name, sd_base)

    print(f"\n✓ Готово! Файлы сохранены в: {out_dir}")


# ===========================================================================
# CLI
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Конвертер толкового словаря в морфологический",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('input', help='Путь к словарю (файл .dsl/.dsl.dz/.ifo или папка)')
    parser.add_argument('--name', '-n', default=None, help='Название словаря')
    parser.add_argument('--format', '-f', default='both',
                        choices=['dsl', 'stardict', 'both'],
                        help='Формат вывода (по умолчанию: both)')
    parser.add_argument('--out', '-o', default=None,
                        help='Папка для сохранения (по умолчанию: рядом с исходным файлом)')

    args = parser.parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        sys.exit(f"Ошибка: путь не найден: {input_path}")

    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = input_path.parent if input_path.is_file() else input_path

    convert(input_path, args.name, out_dir, args.format)


if __name__ == '__main__':
    main()
