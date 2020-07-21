import sys
import os
from lib.functional import xproduct, xfilter, xfirst, xmap, FuncList
from lib.asm import assemble
from lib.alias import read_aliases
from lib.compiler import compile, Context

g,d,a = True,True,False
if len(sys.argv) >=2:
    g = sys.argv and 'g' in sys.argv[-1]    # encodes everything into one GCT file
    d = sys.argv and 'd' in sys.argv[-1]    # encodes everything into a Dolphin ini
    a = sys.argv and 'a' in sys.argv[-1]    # runs assemble.sh
commandsText = ''
if g: commandsText += 'g'
if d: commandsText += 'd'
if a: commandsText += 'a'
if not commandsText:
    print('Error: no valid command supplied (among g,d,a)')
    exit(-1)
gameFilter = ''
codeFilter = ''
for arg in sys.argv[1:-1]:
    if arg.startswith('--game='):
        if gameFilter:
            print('Error: duplicate --game argument specified.')
            exit(-1)
        gameFilter = arg[len('--game='):]
    elif arg.startswith('--code='):
        if codeFilter:
            print('Error: duplicate --code argument specified.')
            exit(-1)
        codeFilter = arg[len('--game='):]
    else:
        print(f'Error: unrecognized argument: {arg}')
        exit(-1)

print(f'== encode.py {commandsText} ==')
aliasList = read_aliases('src/aliases.yaml')
gameList = aliasList.getGameList(gameFilter)

if a:
    assemble(aliasList, gameFilter)
    print('Info: assemble finished')

outputs = {}
def read(context):
    with open(f'src/{context.name}.gecko', 'r') as f:
        result = compile(f.read(), context)
        for log in result.logs:
            print (log)
            if log.errlevel >= 3:
                exit(-1)
            elif log.errlevel == 2:
                return result
        return result

results = FuncList(os.listdir('src')).pipe(
    xfilter(lambda filename: filename.endswith('.gecko')),
    xmap(lambda filename: filename[:-6]),
    xfilter(lambda filename: codeFilter in filename),
    xproduct(gameList, lambda filename, game: Context(game, filename, aliasList)),
    xmap(read)
)

for result in results.tolist():
    game = result.context.game
    if result.codetext().strip():
        print(f'Info: will encode: {result.context.name} for {game}')
        outputs[game] = outputs[game] + [result] if game in outputs else [result]
    elif result.errlevel != 2:
        print(f'Warning: ignoring empty code: {result.context.name}')

if outputs:
    if not os.path.exists('build'): os.mkdir('build')
    for game in gameList:
        iniPath = f'build/{game}.ini'
        gctPath = f'build/{game}.gct'
        encode = False
        if game in outputs:
            codes = outputs[game]
            if codes:
                encode = True
                print(f'Encoding {game}...')
                if g:
                    with open(gctPath, 'wb') as gfile:
                        gfile.write(bytes.fromhex('00d0c0de00d0c0de'))
                        for code in codes:
                            print(f'    Encoding {code.context.name} into gct...')
                            gfile.write(bytes.fromhex(''.join(code.codelines)))
                        gfile.write(bytes.fromhex('f000000000000000'))
                if d:
                    with open(iniPath, 'w') as dfile:
                        dfile.write('[Gecko]\n')
                        for code in codes:
                            print(f'    Encoding {code.context.name} into ini...')
                            dfile.write('$sspc | ' + code.context.name + '\n' + code.codetext() + '\n')
        if not encode:
            print(f'No codes found for {game} - not encoding those files')
            if os.path.exists(iniPath): os.remove(iniPath)
            if os.path.exists(gctPath): os.remove(gctPath)
else:
    print('No codes found.')