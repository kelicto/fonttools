from __future__ import print_function, division, absolute_import
from fontTools.misc.py23 import *
from fontTools.ttLib import TTFont
from fontTools.varLib import build
from fontTools.varLib.mutator import main as mutator
import difflib
import os
import shutil
import sys
import tempfile
import unittest


class MutatorTest(unittest.TestCase):
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        # Python 3 renamed assertRaisesRegexp to assertRaisesRegex,
        # and fires deprecation warnings if a program uses the old name.
        if not hasattr(self, "assertRaisesRegex"):
            self.assertRaisesRegex = self.assertRaisesRegexp

    def setUp(self):
        self.tempdir = None
        self.num_tempfiles = 0

    def tearDown(self):
        if self.tempdir:
            shutil.rmtree(self.tempdir)

    @staticmethod
    def get_test_input(test_file_or_folder):
        path, _ = os.path.split(__file__)
        return os.path.join(path, "data", test_file_or_folder)

    @staticmethod
    def get_test_output(test_file_or_folder):
        path, _ = os.path.split(__file__)
        return os.path.join(path, "data", "test_results", test_file_or_folder)

    @staticmethod
    def get_file_list(folder, suffix):
        all_files = os.listdir(folder)
        return [os.path.abspath(os.path.join(folder, p)) for p in all_files
                                                          if p.endswith(suffix)]

    def temp_path(self, suffix):
        self.temp_dir()
        self.num_tempfiles += 1
        return os.path.join(self.tempdir,
                            "tmp%d%s" % (self.num_tempfiles, suffix))

    def temp_dir(self):
        if not self.tempdir:
            self.tempdir = tempfile.mkdtemp()

    def read_ttx(self, path):
        lines = []
        with open(path, "r", encoding="utf-8") as ttx:
            for line in ttx.readlines():
                # Elide ttFont attributes because ttLibVersion may change,
                # and use os-native line separators so we can run difflib.
                if line.startswith("<ttFont "):
                    lines.append("<ttFont>" + os.linesep)
                else:
                    lines.append(line.rstrip() + os.linesep)
        return lines

    def expect_ttx(self, font, expected_ttx, tables):
        path = self.temp_path(suffix=".ttx")
        font.saveXML(path, tables=tables)
        actual = self.read_ttx(path)
        expected = self.read_ttx(expected_ttx)
        if actual != expected:
            for line in difflib.unified_diff(
                    expected, actual, fromfile=expected_ttx, tofile=path):
                sys.stdout.write(line)
            self.fail("TTX output is different from expected")

    def compile_font(self, path, suffix, temp_dir):
        ttx_filename = os.path.basename(path)
        savepath = os.path.join(temp_dir, ttx_filename.replace('.ttx', suffix))
        font = TTFont(recalcBBoxes=False, recalcTimestamp=False)
        font.importXML(path)
        font.save(savepath, reorderTables=None)
        return font, savepath

# -----
# Tests
# -----

    def test_varlib_mutator_ttf(self):
        suffix = '.ttf'
        ds_path = self.get_test_input('Build.designspace')
        ufo_dir = self.get_test_input('master_ufo')
        ttx_dir = self.get_test_input('master_ttx_interpolatable_ttf')

        ttx_paths = self.get_file_list(ttx_dir, '.ttx')
        self.temp_dir()
        for path in ttx_paths:
            self.compile_font(path, suffix, self.tempdir)

        finder = lambda s: s.replace(ufo_dir, self.tempdir).replace('.ufo', suffix)
        varfont, _, _ = build(ds_path, finder)
        varfont_name = 'Mutator'
        varfont_path = os.path.join(self.tempdir, varfont_name + suffix)
        varfont.save(varfont_path)

        args = [varfont_path, 'wght=500', 'cntr=50']
        mutator(args)

        instfont_path = os.path.splitext(varfont_path)[0] + '-instance' + suffix
        instfont = TTFont(instfont_path)
        tables = [table_tag for table_tag in instfont.keys() if table_tag != 'head']
        expected_ttx = self.get_test_output(varfont_name + '.ttx')
        self.expect_ttx(instfont, expected_ttx, tables)


if __name__ == "__main__":
    sys.exit(unittest.main())
