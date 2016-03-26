import unittest
import mock

from path import Path
from settings import (SERVER_NAME,
                      MEDIAVIEWER_PATH_URL,
                      LOCAL_TV_SHOWS_PATH,
                      WAITER_USERNAME,
                      WAITER_PASSWORD,
                      )

class TestPath(unittest.TestCase):
    def setUp(self):
        self.path = Path('localpath', 'remotepath')

    @mock.patch('path.postData')
    def test_post(self, mock_postData):
        expected = {'localpath': 'localpath',
                    'remotepath': 'remotepath',
                    'skip': False,
                    'server': SERVER_NAME}
        self.path.post()
        mock_postData.assert_called_once_with(expected, MEDIAVIEWER_PATH_URL)

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

    @mock.patch('path.Path.getLocalPaths')
    @mock.patch('path.Path.getPaths')
    def test_getAllPaths(self,
                         mock_getPaths,
                         mock_getLocalPaths):
        mock_getPaths.return_value = {'path1': set([123]),
                                      'path2': set([234]),
                                      'path3': set([345])}
        mock_getLocalPaths.return_value = ['localpath1',
                                           'path2',
                                           'path3']

        expectedDict = {'path1': set([123]),
                        'path2': set([234, -1]),
                        'path3': set([345, -1]),
                        'localpath1': set([-1])}

        self.assertEquals(expectedDict, self.path.getAllPaths())

    @mock.patch('path.os')
    @mock.patch('path.commands')
    def test_getLocalPaths(self,
                           mock_commands,
                           mock_os):
        mock_commands.getoutput.return_value = 'tv.show.1\ntv.show.2\ntv.show.3'
        path = mock.MagicMock()
        path.join.side_effect = lambda x,y: '%s/%s' % (x,y)
        mock_os.path = path

        expected = set(['%s/%s' % (LOCAL_TV_SHOWS_PATH, 'tv.show.1'),
                        '%s/%s' % (LOCAL_TV_SHOWS_PATH, 'tv.show.2'),
                        '%s/%s' % (LOCAL_TV_SHOWS_PATH, 'tv.show.3'),
                        ])
        actual = self.path.getLocalPaths()
        self.assertEquals(expected, actual)

    @mock.patch('path.requests')
    def test_getPathByLocalPathAndRemotePath(self,
                                             mock_requests):
        response = mock.MagicMock()
        mock_requests.get.return_value = response

        localpath = '/path/to/local/folder'
        remotepath = '/path/to/remote/folder'
        Path.getPathByLocalPathAndRemotePath(localpath,
                                             remotepath)

        mock_requests.get.assert_called_once_with(MEDIAVIEWER_PATH_URL,
                                                  params={'localpath': localpath,
                                                          'remotepath': remotepath},
                                                  verify=False,
                                                  auth=(WAITER_USERNAME, WAITER_PASSWORD))
        self.assertTrue(response.json.called)
