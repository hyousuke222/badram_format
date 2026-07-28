#!/usr/bin/env python3
import argparse
import re
import sys


def parse_badram(text):
    """Extract 0x... hex values from input text and pair them into (address, mask)."""
    tokens = re.findall(r"0x[0-9a-fA-F]+", text)
    if len(tokens) % 2 != 0:
        print(
            "Warning: Odd number of hex tokens found. Ignoring trailing token.",
            file=sys.stderr,
        )
        tokens = tokens[:-1]

    pairs = []
    for i in range(0, len(tokens), 2):
        addr = int(tokens[i], 16)
        mask = int(tokens[i + 1], 16)
        pairs.append((addr, mask))
    return pairs


def expand_pfns(addr, mask):
    """Calculate affected 4KB PFNs (Page Frame Numbers) from address and mask."""
    pfn_addr = addr >> 12
    pfn_mask = mask >> 12

    zero_bit_positions = [i for i in range(52) if not ((pfn_mask >> i) & 1)]

    pfns = set()
    num_zeros = len(zero_bit_positions)

    if num_zeros > 16:
        print(
            f"Warning: Mask for address 0x{addr:x} expands to too many combinations. Capping to 16 bits.",
            file=sys.stderr,
        )
        num_zeros = 16
        zero_bit_positions = zero_bit_positions[:16]

    for bits in range(1 << num_zeros):
        curr_pfn = pfn_addr
        for idx, pos in enumerate(zero_bit_positions):
            if (bits >> idx) & 1:
                curr_pfn |= 1 << pos
            else:
                curr_pfn &= ~(1 << pos)
        pfns.add(curr_pfn)

    return pfns


def merge_badram_entries(pfns):
    """Merge contiguous/pattern-matched PFN entries into minimal GRUB badram (addr, mask) pairs."""
    entries = set((pfn << 12, 0xFFFFFFFFFFFFF000) for pfn in pfns)

    while True:
        merged_any = False
        next_entries = set()

        by_mask = {}
        for addr, mask in entries:
            by_mask.setdefault(mask, []).append(addr)

        for mask, addrs in by_mask.items():
            addrs.sort()
            used = [False] * len(addrs)

            for i in range(len(addrs)):
                if used[i]:
                    continue
                for j in range(i + 1, len(addrs)):
                    if used[j]:
                        continue
                    diff = addrs[i] ^ addrs[j]
                    if diff != 0 and (diff & (diff - 1)) == 0 and (diff & mask) == diff:
                        new_addr = addrs[i] & ~diff
                        new_mask = mask & ~diff
                        next_entries.add((new_addr, new_mask))
                        used[i] = True
                        used[j] = True
                        merged_any = True
                        break
                if not used[i]:
                    next_entries.add((addrs[i], mask))

        entries = next_entries
        if not merged_any:
            break

    return sorted(entries)


def parse_memory_size(size_str):
    """Parse size string like '128K', '64M', '16G' into bytes."""
    m = re.match(r"^(\d+)\s*([kKmMgGtT]?[bB]?)$", size_str.strip())
    if not m:
        raise ValueError(f"Invalid memory size format: '{size_str}'")

    val = int(m.group(1))
    unit = m.group(2).upper()

    if unit.startswith("K"):
        return val * 1024
    elif unit.startswith("M"):
        return val * 1024**2
    elif unit.startswith("G"):
        return val * 1024**3
    elif unit.startswith("T"):
        return val * 1024**4
    return val


def main():
    parser = argparse.ArgumentParser(
        description="Convert Memtest86+ badram pattern to Windows badmemorylist and GRUB badram."
    )
    parser.add_argument(
        "-o",
        "--oneline",
        action="store_true",
        help="Output commands on a single line without backslashes",
    )
    parser.add_argument(
        "-m",
        "--memory",
        type=str,
        help="Total system memory size (e.g., 128K, 64M, 16G) to clip mask bits",
    )
    args = parser.parse_args()

    # Read all input from standard input
    input_text = sys.stdin.read()
    pairs = parse_badram(input_text)

    all_pfns = set()
    for addr, mask in pairs:
        pfns = expand_pfns(addr, mask)
        all_pfns.update(pfns)

    # Sort PFNs and format as hex strings
    sorted_pfns = sorted(all_pfns)
    hex_pfns = [f"0x{pfn:x}" for pfn in sorted_pfns]

    # Print formatted PFN list (4 items per line)
    print(f"=== Bad PFN List (Total: {len(hex_pfns)}) ===")
    for i in range(0, len(hex_pfns), 4):
        chunk = hex_pfns[i : i + 4]
        print(" ".join(chunk))

    # Print Windows bcdedit command
    print("\n=== Windows bcdedit Command ===")
    if not args.oneline and hex_pfns:
        chunks = [" ".join(hex_pfns[i : i + 4]) for i in range(0, len(hex_pfns), 4)]
        formatted_list = " \\\n".join(chunks)
        print(f"bcdedit /set {{badmemory}} badmemorylist {formatted_list}")
    else:
        print(f"bcdedit /set {{badmemory}} badmemorylist {' '.join(hex_pfns)}")

    # Print GRUB command
    max_mask = None
    if args.memory:
        try:
            mem_bytes = parse_memory_size(args.memory)
            max_mask = mem_bytes - 1
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    merged_entries = merge_badram_entries(sorted_pfns)

    grub_pairs = []
    for addr, mask in merged_entries:
        if max_mask is not None:
            mask &= max_mask
        grub_pairs.append(f"0x{addr:x},0x{mask:x}")

    print("\n=== GRUB badram Command ===")
    if not args.oneline and grub_pairs:
        grub_str = ", \\\n".join(grub_pairs)
        print(f"badram {grub_str}")
    else:
        grub_str = ",".join(grub_pairs)
        print(f"badram {grub_str}")


if __name__ == "__main__":
    main()
