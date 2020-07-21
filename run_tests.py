import unittest
import sys

pattern = sys.argv[-1] if len(sys.argv) > 1 else False
loader = unittest.TestLoader()
loader.testNamePatterns = [pattern] if pattern else None
suite = loader.discover('lib/tests', pattern='*_tests.py')
unittest.TextTestRunner().run(suite)