import unittest
import os
from shutil import copyfile
from shutil import rmtree
from lib.asm import assemblesinglecode
from lib.alias import read_aliases

class AssemblerTestCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists('test'): os.mkdir('test')
        if not os.path.exists('test/src'): os.mkdir('test/src')
        copyfile('src-asm/_macros.asm', 'test/src/_macros.asm')
    @classmethod
    def tearDownClass(cls):
        rmtree('test')
    def setUp(self):
        self.aliases = read_aliases('src/aliases.yaml')
    def run_test(self, asmsrc, expectedgecko, versionfilter='J'):
        with open('test/src/out.asm', 'w') as f:
            f.write(asmsrc)
        assemblesinglecode('out', self.aliases, versionfilter, 'test/build', 'test/src')
        with open('test/build/RVL-SOUJ-0A-0/out.gecko', 'r') as f:
            self.assertEquals(expectedgecko, f.read().strip())
    def testasmsimple(self):
        self.run_test('''lis r3,0x8053
        ori r3,r3,0x3A1A''', '''C0000000 00000002
3C608053 60633A1A
4E800020 00000000''')
    def testasmwithmacro(self):
        self.run_test('push', '''C0000000 00000003
9421FF80 7C0802A6
90010084 BC610008
4E800020 00000000''')
    def testasmwithalias(self):
        self.run_test('liw r4,LinkPtr', '''C0000000 00000002
3C808057 608489EC
4E800020 00000000''')