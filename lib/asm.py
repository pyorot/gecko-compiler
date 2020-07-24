import os
import subprocess
from lib.functional import FuncList, xmap, xfilter

def assemblesinglecode(filename, aliases, versionfilter, buildfolder, srcfolder):
    """Assembles a single asm file
    
    Keyword arguments:
    filename -- filename.asm will be assembled into filename.gecko
    aliases -- AliasList, constructed from alias.py
    versionfilter -- string, game version codes must contain this in order to be assembled
    buildfolder -- custom build folder, settable for testing override
    srcfolder -- custom source folder, settable for testing override"""
    def ensuredir(path):
        if not os.path.exists(path): os.mkdir(path)
    # python commands differ between os
    if os.sys.platform == 'win32':
        pycmd = "py -2"
    else:
        pycmd = "python"
    ensuredir(srcfolder)
    ensuredir(buildfolder)
    for game in aliases.getGameList(versionfilter):
        ensuredir(buildfolder + '/' + game)
    ensuredir(f'{buildfolder}/.free')
    os.chdir('pyiiasmh')
    def outputsinglecode(game, filter):
        with open(f'../{buildfolder}/tmp.asm', 'w') as tmpfile:
            contents = list(aliases.getMacrosForGame(filter))
            with open(f'../{srcfolder}/_macros.asm', 'r') as f:
                contents.append(f.read())
            with open(f'../{srcfolder}/{filename}.asm', 'r') as f:
                contents.append(f.read())
            contents = ('\n'.join(contents) + '\n').split('\n')
            contents = map(lambda line: aliases.replace(line, game, asm=True), contents) # run address substitution in asm mode
            tmpfile.write('\n'.join(contents) + '\n')
        output = subprocess.Popen(f'{pycmd} pyiiasmh_cli.py -a -codetype C0 ../{buildfolder}/tmp.asm'.split(), stdout=subprocess.PIPE).communicate()
        with open(f'../{buildfolder}/{game}/{filename}.gecko', 'w') as outfile:
            for line in output[0].decode('utf-8').strip().split('\n'):
                outfile.write(line.strip() + '\n')
        print (f'- Assembled {game}/{filename}.asm')
    for game in aliases.getGameList(versionfilter):
        outputsinglecode(game, game)
    outputsinglecode('.free', '*')
    os.chdir('..')

def assemble(aliases, versionfilter):
    """Assembles the asm files in the src-asm folder, using a given
    alias list
    
    Keyword arguments:
    aliases -- AliasList, constructed from alias.py
    versionfilter -- string, game version codes must contain this in order to be assembled"""
    FuncList(os.listdir('src-asm')).pipe(
        xfilter(lambda x: x.endswith('.asm') and x != '_macros.asm'),
        xmap(lambda x: x[:-4])
    ).foreach(lambda x: assemblesinglecode(x, aliases, versionfilter, 'build-asm', 'src-asm'))