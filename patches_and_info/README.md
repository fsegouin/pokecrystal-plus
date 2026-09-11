# Patches

Released Pokémon Crystal+ patches and their symbol tables live here.

`v0.1.0` is the first release and carries **every feature** listed in the
table at the top of `docs/plus.md`.

To build one:

    tools/build_vanilla.sh   # once, produces pokecrystal_vanilla.gbc
    make crystal
    make patch               # -> pokecrystal_plus_v<version>.<yymmdd>.bps

Apply the `.bps` to an unmodified Pokémon Crystal (UE) ROM with Flips, beat,
or any BPS patcher. The patch stores CRC32s of both ROMs, so applying it to the
wrong file is rejected rather than silently producing a broken ROM.

The `.sym` is the symbol table for the latest patch's build. Load it in
BGB or SameBoy to get named labels while debugging.
