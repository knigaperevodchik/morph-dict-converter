[![Boosty](https://img.shields.io/badge/Boosty-DONATE-f15f2c?style=for-the-badge)](https://boosty.to/knigaperevodchik)

# morph_dict_convert

Скрипт превращает обычный толковый словарь в морфологический — чтобы поиск работал по любой форме слова.

**Без скрипта:** вводишь «человеку» — ничего не найдено.  
**После скрипта:** вводишь «человеку» — находит статью «человек».

---

## 🇷🇺 Русский

### Что делает

Берёт словарь в формате DSL или StarDict и добавляет к каждой статье все формы слова как альтернативные заголовки. Готовый файл загружается в GoldenDict, Lingvo или любую другую программу — морфология работает без каких-либо дополнений.

### Установка

```bash
pip install pymorphy3 pymorphy3-dicts-ru
```

### Использование

Положите скрипт рядом со словарём и запустите:

```bash
python morph_dict_convert.py словарь.dsl
```

На выходе появятся готовые файлы с суффиксом `_morph` в той же папке.

**Параметры:**
```bash
--format dsl        # только DSL (один файл, для GoldenDict/Lingvo)
--format stardict   # только StarDict (три файла)
--format both       # оба формата (по умолчанию)
--out /папка/       # куда сохранить результат
--name "Название"   # своё название словаря
```

### Поддерживаемые форматы входного словаря

| Формат | Расширение |
|--------|-----------|
| ABBYY Lingvo DSL | `.dsl`, `.dsl.dz` |
| StarDict | `.ifo` (+ `.idx` + `.dict`) |
| Папка со словарём | определяется автоматически |

### Языки

Сейчас встроена морфология для **русского языка** (через pymorphy3).  
Для других языков можно использовать аналогичные библиотеки:
- Английский — `nltk` + WordNet
- Немецкий, французский и др. — `spaCy`

Если нужна поддержка вашего языка — создайте issue.

---

## 🇬🇧 English

### What it does

Converts a DSL or StarDict dictionary into a morphological one — every article gets all word forms added as alternative headwords. The output file works in GoldenDict, Lingvo, or any other dictionary app with no extra plugins needed.

**Before:** search "running" — article not found (dictionary only has "run").  
**After:** search "running" — finds the article "run".

### Install

```bash
pip install pymorphy3 pymorphy3-dicts-ru
```

### Usage

Put the script next to your dictionary file and run:

```bash
python morph_dict_convert.py dictionary.dsl
```

Output files with `_morph` suffix will appear in the same folder.

**Options:**
```bash
--format dsl        # DSL only (single file)
--format stardict   # StarDict only (three files)
--format both       # both formats (default)
--out /folder/      # output folder
--name "My Dict"    # custom dictionary name
```

### Supported input formats

| Format | Extension |
|--------|-----------|
| ABBYY Lingvo DSL | `.dsl`, `.dsl.dz` |
| StarDict | `.ifo` (+ `.idx` + `.dict`) |
| Folder | auto-detected |

### Language support

Built-in morphology for **Russian** (via pymorphy3).  
Other languages can be added using:
- English — `nltk` + WordNet
- German, French, etc. — `spaCy`

Open an issue if you need support for your language.

---

## 🇨🇳 中文

### 功能说明

将 DSL 或 StarDict 格式的词典转换为形态学词典——每个词条都会添加该词的所有变形形式作为备用词头。生成的文件可直接加载到 GoldenDict、Lingvo 等词典软件中，无需任何插件。

**转换前：** 搜索「человеку」——未找到（词典中只有「человек」）。  
**转换后：** 搜索「человеку」——找到「человек」词条。

### 安装

```bash
pip install pymorphy3 pymorphy3-dicts-ru
```

### 使用方法

将脚本放在词典文件旁边，然后运行：

```bash
python morph_dict_convert.py dictionary.dsl
```

结果文件（带 `_morph` 后缀）将出现在同一文件夹中。

**参数：**
```bash
--format dsl        # 仅 DSL 格式（单个文件）
--format stardict   # 仅 StarDict 格式（三个文件）
--format both       # 两种格式（默认）
--out /文件夹/      # 输出目录
--name "词典名称"   # 自定义词典名称
```

### 支持的输入格式

| 格式 | 扩展名 |
|------|--------|
| ABBYY Lingvo DSL | `.dsl`, `.dsl.dz` |
| StarDict | `.ifo`（+ `.idx` + `.dict`）|
| 文件夹 | 自动识别 |

### 语言支持

目前内置**俄语**形态学分析（通过 pymorphy3）。  
其他语言可通过以下库扩展支持：
- 英语 — `nltk` + WordNet  
- 德语、法语等 — `spaCy`

如需支持其他语言，请提交 issue。

---

## 💙 Donate / Донат / 捐赠

Если полезно — угостите кофе. If helpful — buy me a coffee. 如果有帮助，请我喝杯咖啡。

**TON (USDT)**
```
UQBWKwf2mgakNi4Ls2I6NNs1okcDyCxivdxxc22ypsMV4590
```

**TRC-20 (USDT)**
```
TDdok5FgB6fJSXZrPzxnn7hMk4qREUZPJe
```
