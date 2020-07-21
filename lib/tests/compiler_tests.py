import unittest
import os
import inspect
from lib.compiler import compile, Context
from lib.alias import read_aliases
import sys

class CompilerTestCases(unittest.TestCase):
    def setUp(self):
        self.aliases = read_aliases('src/aliases.yaml')
        self.doPrint = False    # switch for debugging
    def run_test(self, text, expectedResult, opts = {}):
        maxerror = opts['maxerror'] if 'maxerror' in opts else 0
        expectempty = opts['expectempty'] if 'expectempty' in opts else False
        game = opts['game'] if 'game' in opts else 'RVL-SOUJ-0A-0'
        ctxt = Context(game, self.id().split('.')[-1], self.aliases)
        result = compile(text, ctxt)
        if self.doPrint:
            for item in result.logs:
                print (item)
        self.assertEqual(maxerror, result.errlevel)
        if maxerror < 2:
            codetext = result.codetext()
            if expectempty:
                self.assertEqual('', codetext, 'Expected empty result')
            else:
                self.assertEqual(expectedResult, codetext)
    def run_testAlias(self, text, expectedResult, game = 'RVL-SOUJ-0A-0'):
        self.run_test(text, expectedResult, { 'game': game })
    def test_failed_gameassert(self):
        self.run_test('!assertgame RVL-SOUE-0A-0', '', { 'maxerror': 2 })
    def test_versionfree_gameassert_fail(self):
        self.run_test('''!assertgame *
82000000 <ReloaderPtr>''', '', { 'maxerror': 3 })
    def test_versionfree_gameassert_pass(self):
        self.run_test('''!assertgame *
82000000 <CurrentFiles>''', '82000000 8095545C')
    def test_invalid_syntax(self):
        self.run_test('int main(int argc, char** argv) {', '', { 'maxerror': 3 })
    def test_empty_line(self):
        self.run_test('', '', { 'expectempty': True })
    def test_empty_file(self):
        self.run_test('', '')
    def test_gecko(self):
        self.run_test('0000159C 00010004', '0000159C 00010004')
    def test_gecko_with_comment(self):
        self.run_test('  0000159C 00010004  # A comment of some sort', '0000159C 00010004')
    def test_asm(self):
        tmpfilename = 'tmp-test'
        gameFolder = 'build-asm/RVL-SOUJ-0A-0'
        geckopath = f'{gameFolder}/{tmpfilename}.gecko'
        if not os.path.exists(gameFolder): os.mkdir(gameFolder)
        with open(geckopath, 'w') as asmfile:
            asmfile.write('''C0000000 00000001
4E800020 00000000''')
        self.run_test('''00001500 00000000
{0}
00001501 00000000'''.format('{' + tmpfilename + '.asm}'), '''00001500 00000000
C0000000 00000001
4E800020 00000000
00001501 00000000''')
        os.remove(geckopath)
    def test_gosub(self):
        input = '''gosub 5 a_label
        00001500 000000FF
        a_label:
        E0000000 80008000'''
        expected = '''68000001 00000005
00001500 000000FF
E0000000 80008000'''
        self.run_test(input, expected)
    def test_gosub_negative_offset(self):
        input = '''a_label:
        00001400 000000FF
        00001500 000000FF
        gosub 6 a_label
        E0000000 80008000'''
        expected = '''00001400 000000FF
00001500 000000FF
6800FFFD 00000006
E0000000 80008000'''
        self.run_test(input, expected)
    def test_goto(self):
        input = '''goto a_label
        00001500 000000FF
        a_label:
        E0000000 80008000'''
        expected = '''66000001 00000000
00001500 000000FF
E0000000 80008000'''
        self.run_test(input, expected)
    def test_return(self):
        self.run_test('return A', '64000000 0000000A')
    def test_assign_literal(self):
        self.run_test(' grA := deadbeef', '8000000A DEADBEEF')
        self.run_test('grA:=deadbeef', '8000000A DEADBEEF')
    def test_load_into_gr(self):
        self.run_test('grB:=b[80001500]', '8200000B 80001500')
        self.run_test('grB := b [ 80001500 ]', '8200000B 80001500')
        self.run_test('grB:=h[80001500]', '8210000B 80001500')
        self.run_test('grB := h [ 80001500 ]', '8210000B 80001500')
        self.run_test('grB:=w[80001500]', '8220000B 80001500')
        self.run_test('grB := w [ 80001500 ]', '8220000B 80001500')
    def test_aliases(self):
        self.run_testAlias('28000000|<InputBuffer> 40000001', '2859CF8C 40000001')
        self.run_testAlias('28000000|<InputBuffer> 40000001', '2859B48C 40000001', 'RVL-SOUP-0A-1')
        self.run_testAlias('28000000|<InputBuffer> 40000001', '2859B28C 40000001', 'RVL-SOUP-0A-0')

        self.run_testAlias('[gr5] := [ba|<ReloaderPtr>]', '8C0001F5 005789F4')
        self.run_testAlias('[gr5] := [ba|<ReloaderPtr>]', '8C0001F5 00576ED4', 'RVL-SOUP-0A-1')
        self.run_testAlias('[gr5] := [ba|<ReloaderPtr>]', '8C0001F5 00576D34', 'RVL-SOUP-0A-0')

        self.run_testAlias('grB:=b[<Spawn>]', '8200000B 805B6B0C')
        self.run_testAlias('grB:=b[<Spawn>]', '8200000B 805B4FE0', 'RVL-SOUP-0A-1')
        self.run_testAlias('grB:=b[<Spawn>]', '8200000B 805B4DE0', 'RVL-SOUP-0A-0')
        
        self.run_testAlias('grB:=w<Spawn>', '8020000B 805B6B0C')
        self.run_testAlias('grB:=h[<Spawn>]', '8210000B 805B6B0C')
        self.run_testAlias('grB:=h[ba|<Spawn>]', '8211000B 005B6B0C')
        self.run_testAlias('grB:=h[po|<Spawn>]', '9211000B 005B6B0C')

        self.run_testAlias('[gr5] := [ba|<ReloaderPtr> + A]', '8C0001F5 005789FE')
        self.run_testAlias('[gr5] := [ba|<ReloaderPtr> + A]', '8C0001F5 00576EDE', 'RVL-SOUP-0A-1')
        self.run_testAlias('[gr5] := [ba|<ReloaderPtr> + A]', '8C0001F5 00576D3E', 'RVL-SOUP-0A-0')
    def test_endif(self):
        self.run_test('endif A', 'E200000A 00000000')
        self.run_test('endif 10', 'E2000010 00000000')
        self.run_test('endif *', 'E0000000 80008000')
    def test_ifptr(self):
        self.run_test('ifptr', 'DE000000 80008180')
        self.run_test("'ifptr", 'DE000001 80008180')
    def test_if(self):
        self.run_test('ifm [ba|<SettingsFlags>+4] / FF00 == 0001', '28004204 FF000001')
        self.run_test('if [ba|<Spawn>] == 42323030', '205B6B0C 42323030')
        
        self.run_test('\'ifm [ba|<SettingsFlags>+4] / FF00 == 0001', '28004205 FF000001')
        self.run_test('\'if [ba|<Spawn>] == 42323030', '205B6B0D 42323030')
    def test_address_assign(self):
        self.run_test('ba:=<Spawn>', '42000000 805B6B0C')
        self.run_test('ba:=[<Spawn>]', '40000000 805B6B0C')
        self.run_test('po:=<Spawn>', '4A000000 805B6B0C')
        self.run_test('po:=[<Spawn>]', '48000000 805B6B0C')

        self.run_test('ba:=ba|1500', '42010000 00001500')
        self.run_test('ba:=po|1500', '52010000 00001500')
        self.run_test('po:=ba|1500', '4A010000 00001500')
        self.run_test('po:=po|1500', '5A010000 00001500')

        self.run_test('ba:=[ba|1500]', '40010000 00001500')
        self.run_test('ba:=[po|1500]', '50010000 00001500')
        self.run_test('po:=[ba|1500]', '48010000 00001500')
        self.run_test('po:=[po|1500]', '58010000 00001500')
    def test_write_mem(self):
        tests = [
            [ '[ba|1500]:=bCD', '00001500 000000CD' ],
            [ '[ ba | 1500 ] := b CD', '00001500 000000CD' ],
            [ '[ba|1500]:=bCD**1F', '00001500 001E00CD' ],
            [ '[ ba | 1500 ] := b CD **1F', '00001500 001E00CD' ],
            [ '[ba|1500]:=h1A1A', '02001500 00001A1A' ],
            [ '[ ba | 1500 ] := h 1A1A', '02001500 00001A1A' ],
            [ '[ba|1500]:=h1A1A**1F', '02001500 001E1A1A' ],
            [ '[ ba | 1500 ] := h 1A1A **1F', '02001500 001E1A1A' ],
            [ '[ba|1500]:=w2B2B3C3C', '04001500 2B2B3C3C' ],
            [ '[ ba | 1500 ] := w 2B2B3C3C', '04001500 2B2B3C3C' ]
        ]
        for case in tests:
            self.run_test(case[0], case[1])
            self.run_test(case[0].replace('ba', 'po', 1), '1' + case[1][1:])
            self.run_test(case[0].replace('ba|1500', 'ba', 1).replace('ba | 1500', 'ba', 1), case[1].replace('1500', '0000'))
            self.run_test(case[0].replace('ba|1500', 'po', 1).replace('ba | 1500', 'po', 1), '1' + case[1].replace('1500', '0000')[1:])
    def test_memcpy(self):
        tests = [
            [ '[gr5]:=[ba|1500]', '8C0001F5 00001500' ],
            [ ' [ gr5 ] := [ ba | 1500 ] ', '8C0001F5 00001500' ],
            [ '[gr5]:=[ba|1500]**4', '8C0004F5 00001500' ],
            [ ' [ gr5 ] := [ ba | 1500 ] **4', '8C0004F5 00001500' ],
            [ '[ba|1500]:=[gr3]', '8A00013F 00001500'],
            [ ' [ ba | 1500 ] := [ gr3 ] ', '8A00013F 00001500'],
            [ '[ba|1500]:=[gr3]**A', '8A000A3F 00001500'],
            [ ' [ ba | 1500 ] := [ gr3 ] **A', '8A000A3F 00001500']
        ]
        for case in tests:
            self.run_test(case[0], case[1])
            self.run_test(case[0].replace('ba', 'po', 1), '9' + case[1][1:])
            self.run_test(case[0].replace('ba|1500', 'ba', 1).replace('ba | 1500', 'ba', 1), case[1].replace('1500', '0000'))
            self.run_test(case[0].replace('ba|1500', 'po', 1).replace('ba | 1500', 'po', 1), '9' + case[1].replace('1500', '0000')[1:])
    def test_memcpy_between_registers(self):
        self.run_test('[gr4]:=[gr7]', '8C000174 00000000')
        self.run_test(' [ gr4 ] := [ gr7 ] ', '8C000174 00000000')
        self.run_test('[gr4]:=[gr7]**BB', '8C00BB74 00000000')
        self.run_test(' [ gr4 ] := [ gr7 ] **BB', '8C00BB74 00000000')

        self.run_test('[gr6|3C]:=[gr9]', '8A000196 0000003C')
        self.run_test('[ gr6 | 3C ] := [ gr9 ]', '8A000196 0000003C')
        self.run_test('[gr6|3C]:=[gr9]**F6', '8A00F696 0000003C')
        self.run_test('[ gr6 | 3C ] := [ gr9 ] **F6', '8A00F696 0000003C')
        
        self.run_test('[gr6]:=[gr9|3C]', '8C000196 0000003C')
        self.run_test(' [ gr6 ] := [ gr9 | 3C ]', '8C000196 0000003C')
        self.run_test('[gr6]:=[gr9|3C]**F6', '8C00F696 0000003C')
        self.run_test(' [ gr6 ] := [ gr9 | 3C ] **F6', '8C00F696 0000003C')
    def test_store_gr_edge_case(self):
        # These cases are to make sure that a simple [ba] is interpreted as [base address] and not as [0xBA] but that [0ba] is interpreted as [0xBA]
        self.run_test('[ba]:=bgrA', '8401000A 00000000')
        self.run_test('[ ba ] := b grA', '8401000A 00000000')
        self.run_test('[ba]:=bgrA**3C', '840103BA 00000000')
        self.run_test('[ ba ] := b grA **3C', '840103BA 00000000')

        self.run_test('[0ba]:=bgrA', '8400000A 000000BA')
        self.run_test('[ 0ba ] := b grA', '8400000A 000000BA')
        self.run_test('[0ba]:=bgrA**3C', '840003BA 000000BA')
        self.run_test('[ 0ba ] := b grA **3C', '840003BA 000000BA')
    def test_temp(self):
        self.run_test('[po]:=bgrA', '9401000A 00000000')
    def test_store_gr(self):
        tests = [
            [ '[ba|001500]:=bgrA', '8401000A 00001500' ],
            [ '[ ba | 001500 ] := b grA', '8401000A 00001500' ],
            [ '[ba|001500]:=bgrA**1C', '840101BA 00001500' ],
            [ '[ ba | 001500 ] := b grA **1C', '840101BA 00001500' ],
            [ '[ba|001500]:=hgrA', '8411000A 00001500' ],
            [ '[ ba | 001500 ] := h grA', '8411000A 00001500' ],
            [ '[ba|001500]:=hgrA**1C', '841101BA 00001500' ],
            [ '[ ba | 001500 ] := h grA **1C', '841101BA 00001500' ],
            [ '[ba|001500]:=wgrA', '8421000A 00001500' ],
            [ '[ ba | 001500 ] := w grA', '8421000A 00001500' ],
            [ '[ba|001500]:=wgrA**1C', '842101BA 00001500' ],
            [ '[ ba | 001500 ] := w grA **1C', '842101BA 00001500' ]
        ]
        for case in tests:
            self.run_test(case[0], case[1])
            self.run_test(case[0].replace('ba', 'po', 1), '9' + case[1][1:])
            self.run_test(case[0].replace('ba|001500', 'ba', 1).replace('ba | 001500', 'ba', 1), case[1].replace('1500', '0000'))
            self.run_test(case[0].replace('ba|001500', 'po', 1).replace('ba | 001500', 'po', 1), '9' + case[1].replace('1500', '0000')[1:])
            self.run_test(case[0].replace('ba|', '', 1).replace('ba | ', '', 1), case[1][:3] + '0' + case[1][4:])