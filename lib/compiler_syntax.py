import re

validators = []

def formatWithDistance(fmtStr, destLabel):
    def getDist(token):
        fromLine = token.geckoline + 1
        targetLine = token.lookup[destLabel]
        distance = targetLine - fromLine
        if distance < 0:
            distance += 0x10000
            token.addwarning(f'Flow control using negative offset. This code may not work as intended. Label = {destLabel}')
        distance = "{0:04X}".format(distance)
        return fmtStr.format(distance)
    return [getDist]

def flowGoto(match):
    return formatWithDistance("6600{0} 00000000", match.group(1))
validators.append([ re.compile(r'^goto\s+([0-9a-z_]+)$', re.IGNORECASE), flowGoto ])

def flowReturn(match):
    return f'64000000 0000000{match.group(1)}'
validators.append([ re.compile(r'^return\s+([0-9a-f])$', re.IGNORECASE), flowReturn ])

def flowGosub(match):
    return formatWithDistance(f'6800{{0}} 0000000{match.group(1)}', match.group(2))
validators.append([ re.compile(r'^gosub\s+([0-9a-f])\s+([0-9a-z_]+)$', re.IGNORECASE), flowGosub ])

def flowGecko(match):
    return match.group(1).replace('|', '')
validators.append([ re.compile(r'^(?:\|)?([0-9a-f]{8}\s(?:\|)?[0-9a-f]{8})$', re.IGNORECASE), flowGecko ])

def flowEndif(match):
    count = match.group('count')
    if count == '*':
        return 'E0000000 80008000'
    return f'E20000{int(count,16):02X} 00000000'
validators.append([ re.compile(r'^endif\s+(?P<count>(?:[0-9a-f]{1,2}|\*))', re.IGNORECASE), flowEndif])

def flowIf(match, token):
    operators = {
        '==': 0,
        '!=': 2,
        '>': 4,
        '<': 6
    }
    withmask = match.group('if').endswith('m')
    withendif = match.group('if').startswith("'")
    startByte = (0x28 if withmask else 0x20) + operators[match.group('operator')] + (0x10 if match.group('bapo') == 'po' else 0)
    comparand = int(match.group('comparand'), 16)
    offset = int(match.group('offset'), 16) if 'offset' in match.groupdict() else 0
    rightword = comparand
    leftword = startByte * 0x01000000 + offset
    leftword += 1 if withendif else 0
    if startByte & 8 != 0:
        if 'mask' in match.groupdict() and match.group('mask'):
            mask = int(match.group('mask'), 16)
            rightword = mask * 0x10000 + comparand
        else:
            token.addfatal('ifm requires a mask')
            return ''
    elif 'mask' in match.groupdict() and match.group('mask'):
        token.addfatal('if does not support a mask; try using ifm')
        return ''
    return f'{leftword:08X} {rightword:08X}'
validators.append([ re.compile(r"^(?P<if>'?ifm?)\s+\[\s*(?P<bapo>ba|po)(?:\|(?P<offset>[0-9a-f]{1,8}))?\]\s*(?:\/\s*(?P<mask>[0-9a-f]{1,4}))?\s*(?P<operator>==|<|>|!=)\s*(?P<comparand>[0-9a-f]{1,8})$", re.IGNORECASE), flowIf])

def flowIfPtr(match):
    endif = '1' if match.group('endif') else '0'
    return f'DE00000{endif} 80008180' 
validators.append([ re.compile(r"^(?P<endif>')?ifptr$", re.IGNORECASE), flowIfPtr])

def flowAddress(match):
    lhs = match.group('bapo')
    value = match.group("value")
    firstshort = 0x4800 if lhs == 'po' else 0x4000
    if not value.startswith('['):
        firstshort += 0x200
        value = value.strip()
    else:
        value = value[1:-1].strip()
    if value.startswith('ba'):
        firstshort += 1
        value = value[2:].strip()[1:].strip()
    elif value.startswith('po'):
        firstshort += 0x1001
        value = value[2:].strip()[1:].strip()
    value = value.strip()
    return f'{firstshort:04X}0000 {int(value, 16):08X}'
validators.append([ re.compile(r'^(?P<bapo>ba|po)\s*:=\s*(?P<value>(?:\[\s*(?:(?:ba|po)\s*\|\s*)?[0-9a-f]{1,8}\s*\])|(?:\s*(?:(?:ba|po)\s*\|\s*)?[0-9a-f]{1,8}))$', re.IGNORECASE), flowAddress])

def flowAsm(match, token):
    try:
        expandname = match.group(1)
        game = '.free' if token.versionfree else token.context.game
        with open(f'build-asm/{game}/{expandname}.gecko', 'r') as expandfile:
            for line in expandfile:
                yield line.upper()
        token.addinfo(f'expanded file: {game}/{expandname}.asm')
    except FileNotFoundError:
        token.addfatal(f'expansion file not found: {expandname}.asm')
validators.append([ re.compile(r'^{([0-9a-z\-]+).asm}$', re.IGNORECASE), flowAsm ])

def flowAssignLiteralToGR(match):
    return f'8000000{match.group(1)} {int(match.group(2), 16):08X}'
validators.append([ re.compile(r'^gr([0-9a-f])\s*:=\s*([0-9a-f]{1,8})$', re.IGNORECASE), flowAssignLiteralToGR ])


typeConvert = {
    'b': 0,
    'h': 1,
    'w': 2
}

def flowLoadMemToGR(match, token):
    register = match.group('register')
    firstshort = 0x8000 + (0x10 * typeConvert[match.group('type')])
    if match.group('bapo'): firstshort += 1
    if match.group('bapo') == 'po': firstshort += 0x1000 
    o = match.group('open') if 'open' in match.groupdict() and match.group('open') else None
    c = match.group('close') if 'close' in match.groupdict() and match.group('open') else None
    if o and c:
        firstshort += 0x0200
    elif o or c:
        token.addfatal('Mismatched brackets')
    return f'{firstshort:04X}000{register} {int(match.group("offset"),16):08X}'
validators.append([ re.compile(r'^gr(?P<register>[0-9a-f])\s*:=\s*(?P<type>[bhw])\s*(?P<open>\[)?\s*(?:(?P<bapo>ba|po)\s*\|\s*)?(?P<offset>[0-9a-f]{1,8})\s*(?P<close>\])?$', re.IGNORECASE), flowLoadMemToGR ])

def flowWriteToMem(match, token):
    match = match.groupdict()
    start = 16 if 'bapo' in match and match['bapo'] == 'po' else 0
    typeChar = typeConvert[match['type']]
    maxValue = 2**(2**(typeChar + 3))               # max (exclusive) value
    typeByte = typeChar * 2 + start                 # first byte of command
    value = match['value']
    valueInt = int(value, 16)
    if valueInt >= maxValue:
        matchType = match['type']
        token.addfatal(f'Error: assigning value {value} is out of bounds for type {matchType}')
        return iter([])
    sourceAddress = int(match['offset'], 16) if 'offset' in match and match['offset'] else 0
    if sourceAddress > 0x01FFFFFF:
        token.addfatal('Error: address offset greater than 0x01FFFFFF cannot be encoded.')
        return iter([])
    if sourceAddress > 0x00FFFFFF:
        typeByte += 1
        sourceAddress -= 0x01000000
    halfline1 = f'{typeByte:02X}{sourceAddress:06X}'
    times = int(match['times'], 16) if 'times' in match and match['times'] else 1
    timeString = f'{times - 1:04X}'
    if typeChar == 0:
        halfline2 = f'{timeString}00{valueInt:02X}'
    elif typeChar == 1:
        halfline2 = f'{timeString}{valueInt:04X}'
    else:
        if times > 1:
            token.addFatal('Cannot specify repeated placement for word-sized values.')
            return iter([])
        halfline2 = f'{valueInt:08X}'
    yield f'{halfline1} {halfline2}'
validators.append([ re.compile(r'^\[\s*(?P<bapo>ba|po)\s*(?:\|\s*(?P<offset>[0-9a-f]{1,8}))?\s*\]\s*:=\s*(?P<type>[bhw])\s*(?P<value>[0-9a-f]{1,8})\s*(?:\*\*(?P<times>[0-9a-f]{1,4}))?$', re.IGNORECASE), flowWriteToMem ])

def flowMemcpy(match, betweenRegisters, offsetOnSource, abortAllCodes):
    times = match['times'] if 'times' in match and match['times'] else '1'
    sourceRegister = match['register']
    destRegister = match['destRegister'] if 'destRegister' in match and match['destRegister'] else '0'
    po = 'bapo' in match and match['bapo'] == 'po'
    offset = match['offset'] if 'offset' in match and match['offset'] else '0'

    firstByte = 0x8A
    lastByte = sourceRegister + 'F'
    if offsetOnSource:
        firstByte += 2
        lastByte = lastByte[::-1]
    if betweenRegisters:
        lastByte = sourceRegister + destRegister
    firstByte += (16 if po else 0)
    pointerOffset = int(offset, 16)
    if pointerOffset > 0x01FFFFFF:
        abortAllCodes('Error: address offset greater than 0x01FFFFFF cannot be encoded.')
        return iter([])
    if pointerOffset > 0x00FFFFFF:
        firstByte += 1
        pointerOffset -= 0x01000000
    yield "{0:X}{1:0{2}X}{3} {4:0{5}X}".format(firstByte, int(times, 16), 4, lastByte, pointerOffset, 8)

def flowMemcpy1(match, token):
    return flowMemcpy(match.groupdict(), False, False, token.addfatal)
validators.append([ re.compile(r'^\[\s*(?P<bapo>ba|po)\s*(?:\|\s*(?P<offset>[0-9a-f]{1,8}))?\s*\]\s*:=\s*\[\s*gr(?P<register>[0-9a-f])\s*\]\s*(?:\*\*(?P<times>[0-9a-f]+))?$', re.IGNORECASE), flowMemcpy1]    )

def flowMemcpy21(match, token):
    return flowMemcpy(match.groupdict(), True, True, token.addfatal)
validators.append([ re.compile(r'^\[\s*gr(?P<destRegister>[0-9a-f])\s*\]\s*:=\s*\[\s*gr(?P<register>[0-9a-f])\s*(?:\|\s*(?P<offset>[0-9a-f]{1,8}))?\s*\]\s*(?:\*\*(?P<times>[0-9a-f]+))?$', re.IGNORECASE), flowMemcpy21])

def flowMemcpy11(match, token):
    return flowMemcpy(match.groupdict(), True, False, token.addfatal)
validators.append([ re.compile(r'^\[\s*gr(?P<destRegister>[0-9a-f])\s*(?:\|\s*(?P<offset>[0-9a-f]{1,8}))?\s*\]\s*:=\s*\[\s*gr(?P<register>[0-9a-f])\s*\]\s*(?:\*\*(?P<times>[0-9a-f]+))?$', re.IGNORECASE), flowMemcpy11])

def flowMemcpy2(match, token):
    return flowMemcpy(match.groupdict(), False, True, token.addfatal)
validators.append([ re.compile(r'^\[\s*gr(?P<register>[0-9a-f])\s*\]\s*:=\s*\[\s*(?P<bapo>ba|po)(?:\s*\|\s*(?P<offset>[0-9a-f]{1,8}))?\s*\]\s*(?:\*\*(?P<times>[0-9a-f]+))?$', re.IGNORECASE), flowMemcpy2])

def flowStoreGR(match):
    match = match.groupdict()
    bapo = 'bapo' in match and match['bapo']
    po = 'bapo' in match and match['bapo'] and match['bapo'].startswith('po')
    offset = match['offset'] if 'offset' in match and match['offset'] else '0'
    if offset.upper() == 'BA' and not bapo:
        # Edge case: interpret BA as base address, not 0xBA
        bapo = True
        offset = '0'
    register = match['register']
    t = match['type']
    times = match['times'] if 'times' in match and match['times'] else '1'
    
    startByte = "{0:02X}".format(0x84 + (16 if po else 0))
    typeDigit = typeConvert[t]
    baseDigit = 1 if bapo else 0
    timesValue = "{0:03X}".format(int(times,16) - 1)
    offset = "{0:08X}".format(int(offset, 16))
    return f"{startByte}{typeDigit}{baseDigit}{timesValue}{register} {offset}"
validators.append([ re.compile(r'^\[\s*(?P<bapo>ba\s*|po\s*)?\s*\|?\s*(?:(?P<offset>[0-9a-f]{1,8}))?\s*\]\s*:=\s*(?P<type>[bhw])\s*gr(?P<register>[0-9a-f])\s*(?:\*\*(?P<times>[0-9a-f]+))?$', re.IGNORECASE), flowStoreGR])

def flowLabel(match, token):
    token.label = match.group(1)
    return ''
validators.append([ re.compile(r'^([0-9a-z_]+):$', re.IGNORECASE), flowLabel ])