# Memtest86+ BadRAM Formatter

A lightweight, zero-dependency Python script that parses **[Memtest86+](https://www.memtest.org/)** bad memory outputs and converts them into formats compatible with **Windows (`bcdedit`)** and **GRUB (`badram`)**.

It automatically expands bad memory regions into 4KB Page Frame Numbers (PFNs), merges adjacent pages into minimal address/mask entries for GRUB.

---

## Features

* **Dual Output:** Generates both Windows `bcdedit /set {badmemory} badmemorylist` commands and GRUB `badram` instructions in a single pass.
* **Automatic Entry Merging:** Optimizes adjacent 4KB PFNs into combined address/mask pairs using power-of-two alignment matching, significantly reducing the GRUB entry count.
* **GRUB Overflow Prevention:** Allows clipping mask bits using the `-m` / `--memory` option (e.g., `-m 16G`) to avoid 64-bit integer overflow bugs in GRUB that cause boot hangs.
* **Human-Readable Formatting by Default:** Outputs multi-line commands with trailing backslashes (`\`) for easy copy-pasting into terminal sessions or scripts.
* **Zero External Dependencies:** Built entirely with Python standard libraries (`argparse`, `re`, `sys`).

---

## Requirements

* Python 3.6 or higher

---

## Usage

Pass your Memtest86+ output badram pattern directly to the script via standard input (`stdin`).

During the test, press `<F1><F4><F4>` to set output mode to "badram patterns" and `<F10><F10>` to resume the test.

### Basic Syntax

```bash
cat memtest_log.txt | python3 badram_format.py [OPTIONS]
```

Or paste directly using an echo pipe:

```bash
echo "0x62d60310 0xffffffffffffc310 0x62d65040,0xffffffffffffd1c8" | python3 badram_format.py
```

---

## Options

| Option | Long Option | Description |
| :--- | :--- | :--- |
| `-m` | `--memory <SIZE>` | Specify total system RAM (e.g., `128K`, `64M`, `16G`, `64G`) to clip high mask bits and prevent GRUB overflow hangs. |
| `-o` | `--oneline` | Output `bcdedit` and `badram` commands on a single line instead of multi-line backslash format. |
| `-h` | `--help` | Show the help message and exit. |

---

## Example

### Input (`memtest_output.txt`)
```text
badram=0x18944688,0xfffffffffffffff8,0x62d60310,0xffffffffffffc310,
0x62d65040,0xffffffffffffd1c8,0x12f210038,0xffffffffffffb478,
0x12f212da0,0xfffffffffffffff8,0x1ac228100,0xffffffffffffe500,
0x1ac228180,0xffffffffffffe980,0x1ac22a518,0xfffffffffffffff8,
0x1ac22a700,0xffffffffffffe700,0x1ac22a980,0xffffffffffffe980,
0x1ac22c000,0xffffffffffffe900,0x1ac22c000,0xffffffffffffc1c0,
0x1ac22e008,0xffffffffffffe108,0x1ac22f600,0xffffffffffffff08,
0x219ddf168,0xfffffffffffffff8,0x2484580b8,0xfffffffffffffff8,
0x393f90030,0xffffffffffffd130,0x393f92200,0xffffffffffffe300,
0x393f93028,0xfffffffffffff328,0x393f97120,0xfffffffffffff1a8
```

### Running the Command

```bash
python3 badram_format.py -m 16G < memtest_output.txt
```

### Output

```text
=== Bad PFN List (Total: 24) ===
0x18944 0x62d60 0x62d61 0x62d62
0x62d63 0x62d65 0x62d67 0x12f210
0x12f212 0x12f214 0x1ac228 0x1ac229
0x1ac22a 0x1ac22b 0x1ac22c 0x1ac22d
0x1ac22e 0x1ac22f 0x219ddf 0x248458
0x393f90 0x393f92 0x393f93 0x393f97

=== Windows bcdedit Command ===
bcdedit /set {badmemory} badmemorylist 0x18944 0x62d60 0x62d61 0x62d62 \
0x62d63 0x62d65 0x62d67 0x12f210 \
0x12f212 0x12f214 0x1ac228 0x1ac229 \
0x1ac22a 0x1ac22b 0x1ac22c 0x1ac22d \
0x1ac22e 0x1ac22f 0x219ddf 0x248458 \
0x393f90 0x393f92 0x393f93 0x393f97

=== GRUB badram Command ===
badram 0x18944000,0x3fffff000, \
0x62d60000,0x3ffffc000, \
0x62d65000,0x3ffffd000, \
0x12f210000,0x3ffffd000, \
0x12f214000,0x3fffff000, \
0x1ac228000,0x3ffff8000, \
0x219ddf000,0x3fffff000, \
0x248458000,0x3fffff000, \
0x393f90000,0x3ffffd000, \
0x393f93000,0x3ffffb000
```

---

## Why Use the `-m` / `--memory` Option?

When GRUB processes `badram` masks with full 64-bit addresses (like `0xfffffffffffff000`), certain versions of GRUB suffer from integer overflow issues during memory mapping calculations, causing the system to hang at boot.

By passing your installed RAM capacity (e.g., `-m 16G`), the script clips mask bits beyond the physical upper bound of your system RAM (`mask &= RAM_SIZE - 1`), avoiding overflow while ensuring bad pages remain masked out properly.

---

## License

This project is open-source and available under the [MIT License](LICENSE).

---

## See also
* https://memtest.org/readme#badram-patterns
* [[tutorial] BadRAM 2025 update](https://forums.gentoo.org/viewtopic.php?t=1172918)
* [Microsoft Learn > How to Manage the Predictive Failure Analysis (PFA) Memory List](https://learn.microsoft.com/en-us/windows-hardware/drivers/whea/how-to-manage-the-pfa-memory-list)
