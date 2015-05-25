import unittest
import mock
from mock import call

from path import Path

class TestPath(unittest.TestCase):
    def setUp(self):
        self.path = Path('localpath', 'remotepath')

    @mock.patch('path.requests')
    def test_getPaths(self,
                      mock_requests):
        test_data = {'next': None,
                     'results': [{'localpath': 'path1',
                                  'pk': 12},
                                 {'localpath': 'path2',
                                  'pk': 123},
                                 {'localpath': 'path1',
                                  'pk': 234},
                                 ]}

        mock_request = mock.MagicMock()
        mock_request.json.return_value = test_data
        mock_requests.get.return_value = mock_request

        expectedPathDict = {'path1': set([12, 234]),
                            'path2': set([123])}
        actualPathDict = self.path.getPaths()

        self.assertEquals(expectedPathDict, actualPathDict)
