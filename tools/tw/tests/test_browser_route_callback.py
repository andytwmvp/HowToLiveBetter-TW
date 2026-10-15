"""確保Playwright回呼不把第二個Request參數當成測試回應資料。"""
import inspect
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_navigation import mock_json_response


class RouteCallbackTests(unittest.TestCase):
    def test_mock_response_arity_and_payload_are_preserved(self):
        first, second = '{"first":true}', '{"second":false}'
        handlers = [mock_json_response(first), mock_json_response(second)]
        for handler, body in zip(handlers, [first, second], strict=True):
            self.assertEqual(list(inspect.signature(handler).parameters), ['route'])
            route = Mock()
            handler(route)
            route.fulfill.assert_called_once_with(status=200, content_type='application/json', body=body)
        with self.assertRaises(TypeError):
            mock_json_response(object())


if __name__ == '__main__':
    unittest.main()
