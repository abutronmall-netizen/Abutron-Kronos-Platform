"""Pure static tests for constrained Qwen3 worker policy.

These tests never import, run or evaluate any model-generated candidate.
"""
import ast
import unittest
from worker import validate, trusted_fallback, repair_naive_aware_comparison

class WorkerPolicyTests(unittest.TestCase):
    def test_reference_is_auditable_static_python(self):
        data = trusted_fallback()
        self.assertGreater(len(data), 120)
        tree = ast.parse(data)
        self.assertEqual([n.name for n in tree.body if isinstance(n, ast.FunctionDef)],
                         ["telemetry_fresh"])
        self.assertFalse(any(isinstance(n, (ast.Import, ast.ClassDef, ast.With,
                                            ast.AsyncWith)) for n in ast.walk(tree)))

    def test_unknown_functions_cannot_execute(self):
        for text in (
            "import os\n" + "def telemetry_fresh(timestamp,now):\n    return True\n",
            "def different(timestamp,now):\n    return True\n",
            "from datetime import datetime\nprint('unauthorized')\ndef telemetry_fresh(timestamp,now):\n    return True\n",
        ):
            with self.assertRaises(ValueError):
                validate(text)

    def test_repair_requires_exact_proven_typeerror(self):
        source=("from datetime import datetime\n"
                "def telemetry_fresh(timestamp: str, now: datetime) -> bool:\n"
                "    parsed = datetime.fromisoformat(timestamp)\n"
                "    return (now - parsed).total_seconds() <= 180\n")
        self.assertIsNone(repair_naive_aware_comparison(source,"timeout"))
        amended=repair_naive_aware_comparison(
            source,"TypeError: can't subtract offset-naive and offset-aware datetimes")
        self.assertIsNotNone(amended)
        self.assertIn("now.tzinfo is None", amended)
        self.assertIn("parsed.tzinfo is None", amended)
        validate(amended)

if __name__=="__main__":
    unittest.main()
