import unittest
import os
from lib.alias import read_aliases

class CompilerTestCases(unittest.TestCase):
    def setUp(self):
        self.aliases = read_aliases('../aliases.yaml')
    def get(self, alias, version):
        value = self.aliases.get(alias, version)
        return f'{value:08X}' if value else None
    def test_readgameuniversalforuniversal(self):
        self.assertEquals('80001500', self.get('EmptyA', '*'))
    def test_readgameuniversalforgame(self):
        self.assertEquals('80001500', self.get('EmptyA', 'RVL-SOUJ-0A-0'))
    def test_readgamemissingforuniversal(self):
        self.assertIsNone(self.get('LinkPtr', '*'))
    def test_readgamepresentforgame(self):
        self.assertEquals('8057578C', self.get('LinkPtr', 'RVL-SOUE-0A-0'))
    def test_readgamemissingformissinggame(self):
        self.assertIsNone(self.get('LinkPtr', 'RVL-SOUP-0A-2'))
    def test_readgamecorrectforpurehex(self):
        self.assertEquals('80575794', self.get('ReloaderPtr', 'RVL-SOUE-0A-0'))
        self.assertEquals('80575C74', self.get('ReloaderPtr', 'RVL-SOUE-0A-1'))
    def test_macro(self):
        self.assertEquals('.set EmptyA, 0x80001500', self.aliases.aliases.get('EmptyA').getmacro('*'))