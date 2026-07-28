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
    # Shift right by 12 bits to target 4KB page granularity
    pfn_addr = addr >> 12
    pfn_mask = mask >> 12

    # Identify zero-bit positions (wildcard bits) in the PFN mask (52 bits for 64-bit addresses)
    zero_bit_positions = [i for i in range(52) if not ((pfn_mask >> i) & 1)]

    pfns = set()
    num_zeros = len(zero_bit_positions)

    # Safety check: Cap wildcard expansion if it produces too many pages (> 2^16 = 65,536 pages)
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


def main():
    parser = argparse.ArgumentParser(
        description="Convert Memtest86+ badram pattern to Windows badmemorylist or GRUB badram."
    )
    parser.add_argument(
        "--grub",
        action="store_true",
        help="Output GRUB badram configuration and command",
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
    print(f"bcdedit /set {{badmemory}} badmemorylist {' '.join(hex_pfns)}")

    # Print GRUB configuration if --grub option is set
    if args.grub:
        # Each PFN (4KB page) corresponds to address `pfn << 12`
        # and mask `0xfffffffffffff000` (matches exact 4KB page)
        grub_pairs = [f"0x{pfn << 12:x},0xfffffffffffff000" for pfn in sorted_pfns]
        grub_str = ",".join(grub_pairs)

        print("\n=== GRUB badram Command ===")
        print(f"badram {grub_str}")

if __name__ == "__main__":
    main()
