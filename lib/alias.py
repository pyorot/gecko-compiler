import re
import yaml
from functools import wraps
from yaml.nodes import ScalarNode,SequenceNode,MappingNode
from collections.abc import Iterable

def defaultctor(basector, node):
    if isinstance(node, ScalarNode):
        return basector.construct_scalar(node)
    elif isinstance(node, SequenceNode):
        return basector.construct_sequence(node)
    elif isinstance(node, MappingNode):
        return basector.construct_mapping(node)
    return None

class AliasData:
    def __init__(self, alias):
        self.alias = alias
        self.data = {}
        self.universal = None
    def setvalue(self, version, scalar):
        if isinstance(scalar, int):
            scalar = str(scalar)
        if version == '*':
            self.universal = scalar
        else:
            self.data[version] = scalar
    def getvalue(self, version):
        toconvert = self.universal if version == '*' or not version in self.data else self.data[version]
        return int(toconvert, 16) if isinstance(toconvert, str) else toconvert
    def getmacro(self, version):
        value = self.getvalue(version)
        return f'.set {self.alias}, 0x{value:08X}' if value else ''

aliasReplacer = re.compile(r'\<\s*(?P<alias>\w+)\s*\>', re.IGNORECASE)
def binaryPattern(separator):
    return r'(?P<addend1>(?<!gr)[0-9a-f]{1,8}(?<!ba))\s*' + separator + r'\s*(?P<addend2>[0-9a-f]{1,8})'
additionReplacer = re.compile(binaryPattern(r'\+'), re.IGNORECASE)
orfinder = re.compile(r'\|\s*(?P<value>[0-9a-f]{1,8})', re.IGNORECASE)
orcombiner = re.compile(binaryPattern(r'\|'), re.IGNORECASE)

class AliasList:
    """Alias collection as parsed from an aliases.yaml file"""
    def __init__(self, games, aliases):
        self.games = games
        self.aliases = aliases
    def get(self, alias, game):
        """Gets the value of a given alias for a given game version. Returns the integer value of the address.
        Returns None if the alias-game combination cannot be resolved.
        
        Keyword arguments:
        alias -- string, alias to search for
        game -- string, game version whose value is desired, use '*' to get the universal value if present, universal
        value will also be used if no value can be found for the specified game"""
        return self.aliases[alias].getvalue(game) if alias in self.aliases else None
    def replace(self, text, version, asm=False):
        """Replaces aliases in a line of gecko text and returns the text with the alias replaced and all subsequent operations performed.
        
        Keyword arguments:
        text -- string, the text possibly containing an alias
        version -- string, current game version"""
        def aliasRepl(matchobj):
            value = self.get(matchobj.group("alias"), version)
            if value:
                return f'{value:08X}' if not asm else f'0x{value:08X}' # asm codes need "0x" to be prefixed to addresses
            return matchobj.group(0)
        def addRepl(matchobj):
            addend1 = int(matchobj.group('addend1'), 16)
            addend2 = int(matchobj.group('addend2'), 16)
            return f'{addend1 + addend2:08X}'
        def orRepl(matchobj):
            value = int(matchobj.group('value'), 16) % 0x02000000
            return f'|{value:08X}'
        text = re.sub(aliasReplacer, aliasRepl, text)
        if not asm: # keep this to gecko to avoid side-effects
            text = re.sub(additionReplacer, addRepl, text)
            text = re.sub(additionReplacer, addRepl, text) # repeat to resolve ternary sums (i know this is big stupid sry)
            text = re.sub(orfinder, orRepl, text)
            text = re.sub(orcombiner, addRepl, text)
        return text
    def getMacrosForGame(self, game):
        for k in self.aliases:
            m = self.aliases[k].getmacro(game)
            if m:
                yield m
    def getGameList(self, filter):
        return [game for game in self.games if filter in game]

def filector(basector, node):
    if len(node.value) > 1 and len(node.value[1]) and node.value[1][0].value == 'addresses':
        games = defaultctor(basector, SequenceNode(yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG, [node.value[0][1]]))
        d = dict()
        for value in MappingNode(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, node.value[1][1].value).value:
            result = AliasData(defaultctor(basector, value[0]))
            nextnode = value[1]
            if isinstance(nextnode, ScalarNode):
                result.setvalue('*', nextnode.value)
            else:
                for v in nextnode.value:
                    result.setvalue(defaultctor(basector, v[0]), defaultctor(basector, v[1]))
            d[result.alias] = result
        return AliasList(games[0], d)
    return defaultctor(basector, node)

def read_aliases(file):
    """Reads an aliases.yaml file and returns the constructed AliasList
    
    Keyword arguments:
    file -- string, path to the yaml file"""
    with open(file) as f:
        return yaml.safe_load(f)

yaml.SafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, filector)