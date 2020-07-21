# User Guide

This section is addressed to anyone writing a code using this framework. The framework supports certain aliases that make gecko codes faster to write, and easier to read and debug. What follows in this section is a listing of those aliases and what they do.

## Commenting

In any gecko file in this project, all content will be ignored after the first occurence of the # symbol on a line.

## Assembly Insert

PowerPC assembly code (which is far too vast a topic to be covered here) can be executed by a gecko code via the C0 code type. However, compiling one's own assembly code and manually inserting it as a C0 code into a gecko code can be tedious and error-prone. To that end, this project supports inserting such code by simply referencing the filename. Consider the following example.

```
2859CF8C 00002008   # If Z+D-pad up being held:
{changedata.asm}    # Execute this assembly
E0000000 80008000   # End If.
```

This will insert the C0 code compiled from the assembly file found at `./src-asm/changedata.asm`.

At this time, insertion of C2 codes in this manner is not supported.

## Flow Control

There are aliases for a limited amount of flow control. To motivate this, consider the following gecko, which writes a value to two different positions in two different instances of the same struct.

```
4A000000 8000FEFE   # Sets po to 0x8000FEFE, the address of one instance of the struct
80000001 DEADBEEF   # Sets gr1 to 0xDEADBEEF, the content we want to write.
68000003 0000000A   # Jumps forward 4 lines, placing the code address to return to in block register A
4A000000 8000FEFE   # Sets po to 0x8001FEFE, the address of the next instance of the struct
68000001 0000000A   # Jumps forward 2 lines, placing the code address to return to in block register A
66000003 00000000   # Jumps forward 4 lines, to the end
94200001 00000010   # Write content of gr1 to po + 0x10
94200001 00000058   # Write content of gr1 to po + 0x58
64000000 0000000A   # Returns to the code whose address is in block register A
E0000000 80008000   # End Code
```

That may work, but it is difficult to maintain. If some more processing needs to be done after the subroutine is called, this may affect the number of lines to jump, which means going back and manually updating the lines of code that do the flow control. To that end, this project supports assembly style labels with `gosub` and `goto` commands. We could rewrite the above as follows:

```
4A000000 8000FEFE   # Sets po to 0x8000FEFE, the address of one instance of the struct
80000001 DEADBEEF   # Sets gr1 to 0xDEADBEEF, the content we want to write.
gosub A write_to_mem# Calls a function that writes the content to the struct.
4A000000 8000FEFE   # Sets po to 0x8001FEFE, the address of the next instance of the struct
gosub A write_to_mem# Calls the function again
goto end            # Skip the function content
write_to_mem:
94200001 00000010   # Write content of gr1 to po + 0x10
94200001 00000058   # Write content of gr1 to po + 0x58
64000000 0000000A   # Returns to the code whose address is in block register A
return A
end:
E0000000 80008000   # End Code
```

The register specification (in the above, `A`) in the `gosub` and `return` commands are necessary (and powerful!) with gecko's conventions. If a function makes a `gosub` or `goto` command with the same block register it was called with, it will be overwriting its own return point.

Note on the above: The [official gecko docs](https://geckocodes.org/index.php?arsenal=1#66) say that the number of lines to jump is signed, thus supporting functions placed before the caller. However, some versions of dolphin treat the value as unsigned, meaning that they will try to jump forward into garbage data instead of backwards to sensible data. The framework will write the codes according to the docs and simply print out a warning if a function is placed before its caller, but it is worth being aware of this limitation.

## If

What follows is a table of common logic tasks, the alias to perform them, and the corresponding gecko code. Note that anywhere base address (`ba`) is used, pointer offset (`po`) can be used in the alias just as well.

| Task | Alias | Compiled Gecko |
| --- | --- | --- |
| If the 16 bits at (base address + 0x1500), with the inverted mask 0xFF00, is equal to the value 0x0010: | `ifm [ba|1500] / FF00 == 1000` | `28001500 FF000010` |
| If the 32 bits at (base address + 0x1500), is equal to the value 0x12AB34CD: | `if [ba|1500] == 12AB34CD` | `20001500 12AB34CD` |
| EndIf, then If the 16 bits at (base address + 0x1500), with the inverted mask 0xFF00, is equal to the value 0x0010: | `'ifm [ba|1500] / FF00 == 1000` | `28001501 FF000010` |
| EndIf, then If the 32 bits at (base address + 0x1500), is equal to the value 0x12AB34CD: | `'if [ba|1500] == 12AB34CD` | `20001501 12AB34CD` |
| Apply 0x1A EndIfs. Leave ba and po alone. | `endif 1A` | `E200001A 00000000` |
| End all Ifs. Reset ba and po. | `endif *` | `E0000000 80008000` |
| If pointer offset is a valid pointer in MEM1. | `ifptr` | `DE000000 80008180` |
| EndIf, then If pointer offset is a valid pointer in MEM1. | `'ifptr` | `DE000001 80008180` |

## Storing and loading data

What follows is a table of common data storage tasks, the alias to perform them, and the corresponding gecko code. Note that anywhere base address (`ba`) is used, pointer offset (`po`) can be used in the alias just as well. Also note, any line where the task has _byte_ italicized, the alias works just as well by replacing the italicized _byte_ with _halfword_ or _word_ and replacing the `b` on the righthand side of the assignment with `h` or `w` respectively.

| Task | Alias | Compiled Gecko |
| --- | --- | --- |
| Set the base address to the literal value 0x8090A0B0 | `ba := 8090A0B0` | `42000000 8090A0B0` |
| Set the base address to the word found at address 0x8090A0B0 | `ba := [8090A0B0]` | `40000000 8090A0B0` |
| Set the pointer offset to the literal value 0x8090A0B0 | `po := 8090A0B0` | `4A000000 8090A0B0` |
| Set the pointer offset to the word found at address 0x8090A0B0 | `po := [8090A0B0]` | `48000000 8090A0B0` |
| Load the literal value 0x8090A0B0 into gecko register B | `grB := 8090A0B0` | `8000000B 8090A0B0` |
| Load the _byte_ starting at the address 0x80001000 into gecko register C | `grC := b[80001000]` | `8200000C 80001000` |
| Load the _byte_ starting at base address plus 0x1234 into gecko register C | `grC := b[ba+1234]` | `8201000C 00001234` |
| Load the _byte_ starting at pointer offset plus 0x1234 into gecko register C | `grC := b[po+1234]` | `9201000C 00001234` |
| Store _byte_ literal 0xEF to the address in ba | `[ba] := bEF` | `00000000 000000EF` |
| Store _byte_ literal 0xEF to 0x1C consecutive _byte_-sized addresses starting at ba | `[ba] := bEF**1C` | `00000000 001B00EF` |
| Store _byte_ literal 0xEF to the address 0x5A bytes after ba | `[ba|5A] := bEF` | `0000005A 000000EF` |
| Store _byte_ literal 0xEF to 0x1C consecutive _byte_-sized addresses starting 0x5A bytes after ba | `[ba|5A] := bEF**1C` | `0000005A 001B00EF` |
| Copy 1 byte from the address in gecko register A to the address in ba | `[ba] := [grA]` | `8A0001AF 00000000` |
| Copy 0x1F bytes from the address in gecko register A to the address in ba | `[ba] := [grA]**1F` | `8A001FAF 00000000` |
| Copy 1 byte from the address in gecko register A to the address 0x5A bytes after ba | `[ba|5A] := [grA]` | `8A0001AF 0000005A` |
| Copy 0x1F bytes from the address in gecko register A to the address 0x5A bytes after ba | `[ba|5A] := [grA]**1F` | `8A001FAF 0000005A` |
| Copy 1 byte from the address in ba to the address in gecko register 7 | `[gr7] := [ba]` | `8C0001F7 00000000` |
| Copy 0x1F bytes from the address in ba to the address in gecko register 7 | `[gr7] := [ba]**1F` | `8C001FF7 00000000` |
| Copy 1 byte from the address 0x5A bytes after ba to the address in gecko register 7 | `[gr7] := [ba|5A]` | `8C0001F7 0000005A` |
| Copy 0x1F bytes from the address 0x5A bytes after ba to the address in gecko register 7 | `[gr7] := [ba|5A]**1F` | `8C001FF7 0000005A` |
| Copy 1 byte from the address in gecko register 6 to the address in gecko register 7 | `[gr7] := [gr6]` | `8C000167 00000000` |
| Copy 0x1F bytes from the address in gecko register 6 to the address in gecko register 7 | `[gr7] := [gr6]**1F` | `8C001F67 00000000` |
| Copy 1 byte from the address 0x5A bytes after the address in gecko register 6 to the address in gecko register 7 | `[gr7] := [gr6|5A]` | `8C000167 0000005A` |
| Copy 0x1F bytes from the address 0x5A bytes after the address in gecko register 6 to the address in gecko register 7 | `[gr7] := [gr6|5A]**1F` | `8C001F67 0000005A` |
| Copy 1 byte from the address in gecko register 6 to the address 0x5A bytes after the address in gecko register 7 | `[gr7|5A] := [gr6]` | `8A000167 0000005A` |
| Copy 0x1F bytes from the address in gecko register 6 to the address 0x5A bytes after the address in gecko register 7 | `[gr7|5A] := [gr6]**1F` | `8A001F67 0000005A` |
| Write the _byte_ in gecko register 8 to the address in ba | `[ba] := bgr8` | `84010008 00000000` |
| Write the _byte_ in gecko register 8 to 0x1F consecutive _byte_-sized addresses starting at ba | `[ba] := bgr8**1F` | `840101E8 00000000` |
| Write the _byte_ in gecko register 8 to the address 0x5A bytes after the address in ba | `[ba|5A] := bgr8` | `84010008 0000005A` |
| Write the _byte_ in gecko register 8 to 0x1F consecutive _byte_-sized addresses starting 0x5A bytes after the address in ba | `[ba|5A] := bgr8**1F` | `840101E8 0000005A` |

## Aliased Addresses

Some in-game addresses are reused across several macros or are different across different versions of the game. This can cause copy-paste errors in reusing the addresses across different codes, as well as a headache maintaining different versions of the same code for different versions of the game. To that end, this project uses an aliases file defining aliases for these addresses. An alias is defined by a (case-sensitive) keyword and an address or set of addresses.

For these examples, suppose we have an aliased address which maps the keyword `LinkPtr` to the address 0x805789EC on NTSC-J and to the address 0x8057578C on NTSC-U 1.0.

In asm, such an aliased address can be used as a defined macro. So, for example, to load the aliased address of LinkPtr into GPR4, one could use...

```
    lis r4,LinkPtr @h
    ori r4,r4,LinkPtr @l
```

In gecko, on the other hand, an aliased address can be used by surrounding the alias with angle brackets...

```
80000005 <LinkPtr>  # Set gr5 to link pointer
```

will compile to `80000005 805789EC` on NTSC-J and to `80000005 8057578C` on NTSC-U 1.0.

However, sometimes a gecko line wants the first seven bits of the address to be stripped off, like in this code...

```
285789EC 00000000   # If LinkPtr is null
```

The `80` is missing from the front of the address since this code is actually using base address plus an offset. Doing this won't work...

```
28<LinkPtr> 00000000    # Compiles to `28805789EC 00000000` which is not a valid Gecko line
```

However, you can place a `|` before the alias to mask off the first seven bits...

```
28|<LinkPtr> 00000000   # Compiles to `285789EC 00000000` on NTSC-J and `2857578C 00000000` on NTSC-U 1.0.
```

## Game Version Management

In regards to the aliasing above, it may seem like every code should be easy to compile for every version of the game. Unfortunately, that ignores the tedium of finding a given memory address on every version of the game. To solve this problem, a .gecko file can declare the versions of the game that it supports. The basic syntax is like this...

```
!assertgame RVL-SOUJ-0A-0
```

That directive would indicate that the code works only on the Japanese version. For multiple versions, just use a whitespace-separated list...

```
!assertgame RVL-SOUE-0A-0 RVL-SOUE-0A-1
```

That directive would indicate that the code works on NTSC-U 1.0 and NTSC-U 1.1. On the other hand, it is possible to assert that a code should work without any version-specific aliases, i.e. that the same code should work on all versions. This is done with a simple `*`.

```
!assertgame *
```

# Developer Guide

This section is intended as documentation for the aliasing python logic in a technical sense. If you don't intend to work on the framework itself, this section is probably not for you.

## compiler_syntax.py

The compiler_syntax.py file is responsible for parsing individual lines. It consists of a number of functions and a list of regexes to go with them. Adding a new alias is as easy as adding a new function with the regex as exemplified many times in that file. The first validator in the list to match a line will be given priority.

### Example: Load Memory Into Gecko Register

```python
def flowLoadMemToGR(match):
    return f'82{typeConvert[match.group(2)]}0000{match.group(1)} {match.group(3)}'
validators.append([ re.compile(r'^gr([0-9a-f])\s*:=\s*([bhw])\s*\[\s*([0-9a-f]{8})\s*\]$', re.IGNORECASE), flowLoadMemToGR ])
```

The validator function may take 0, 1, or 2 arguments. The first argument, if extant, will be the match object returned from the regex match. The function will not be called unless the match succeeded, but the match is still passed for the sake of extracting capturing groups. The second argument, if extant, will be the current gecko token, which exposes useful attributes such as `game` and `name` for the current game version and code name respectively, as well as logging methods such as `addinfo`, `addwarning`, `adderror`, and `addfatal`. In the above example, the gecko register is in group 1, the type of the memory to load is in group 2, and the address is in group 3.

The validator function may return a string (which will be treated as raw gecko), a function (which will be called later with the token as the sole argument--for the sake of looking up label addresses *after* the file has been parsed), or an iterable of the above.

It is recommended that all of these regexes be case insensitive and be generous in supporting user-inserted whitespace between tokens of distinct meaning. Returning again to the gecko register memory load syntax, all of the following are equivalent...

```
gr0:=h[80001000]
gr0 :=h[80001000]
gr0 := h[80001000]
gr0 := h [80001000]
gr0    :=    h    [    80001000    ]
```

## <span>alias.py</span>

An AliasList object is constructed by the `read_aliases` function from the appropriate file type. This object maintains the list of aliases and is used for setting asm macros and replacing alias occurrences in gecko strings.

## <span>compiler.py</span>

The compiler file has a single relevant class called Context, which is passed to the main function of the file, `compile`. The Context provides game, code, and aliasing information throughout the parsing process. The compile function uses a functional style to return a single parsed gecko code, with the context, any logs, and an array of the lines of gecko code as attributes.