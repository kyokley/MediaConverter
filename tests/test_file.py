import unittest
import mock
from file import File

class TestFile(unittest.TestCase):
    def setUp(self):
        self.file = File('testfilename',
                         123,
                         234,
                         True)

    @mock.patch('file.requests')
    def test_getFileSet(self,
                        mock_requests):
        test_data = {'next': None,
                     'results': [{'filename': 'file1'},
                                 {'filename': 'file2'},
                                 {'filename': 'file3'}],
                     }
        mock_request = mock.MagicMock()
        mock_request.json.return_value = test_data

        mock_requests.get.return_value = mock_request

        expectedSet = set(['file1',
                           'file2',
                           'file3',
                           ])

        self.assertEquals(expectedSet, self.file.getFileSet(1))
