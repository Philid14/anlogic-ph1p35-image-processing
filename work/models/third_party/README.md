# third_party - 上游字体

| 文件 | 来源 | 许可证 | 取得日期 | 用途 |
|---|---|---|---|---|
| `font8x8_basic.h` | https://github.com/dhepper/font8x8 (`font8x8_basic.h`) | Public Domain（文件头声明；基于 IBM 公开领域 VGA 字体，经 Marcel Sondaar 整理） | 2026-10-16 | 生成 `work/rtl/osd/char_rom.v` 与 `work/models/font8x8_public_domain.py` |

SHA-256：`49D8DF366296B203CA3211BC0672CF2A762135BF12710735B6292756B19DFFD5`

本目录只保存未修改的上游文件。生成物由 `scripts/gen_char_rom.py` 产出，`--check`
可用于核对生成物是否与上游一致。上游字体的位序约定：每个字节 bit0 为最左像素。
