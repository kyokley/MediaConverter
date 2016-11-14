import unittest
import mock
import tempfile
import shutil
import os

from path import Path
from settings import (SERVER_NAME,
                      MEDIAVIEWER_TV_PATH_URL,
                      MEDIAVIEWER_MOVIE_PATH_URL,
                      WAITER_USERNAME,
                      WAITER_PASSWORD,
                      VERIFY_REQUESTS,
                      )

class TestPath(unittest.TestCase):
    def setUp(self):
        self.path = Path('localpath', 'remotepath')

    @mock.patch('path.postData')
    def test_postMovie(self, mock_postData):
        expected = {'localpath': 'localpath',
                    'remotepath': 'remotepath',
                    'skip': False,
                    'server': SERVER_NAME}
        self.path.postMovie()
        mock_postData.assert_called_once_with(expected, MEDIAVIEWER_MOVIE_PATH_URL)

    @mock.patch('path.postData')
    def test_postTVShow(self, mock_postData):
        expected = {'localpath': 'localpath',
                    'remotepath': 'remotepath',
                    'skip': False,
                    'server': SERVER_NAME}
        self.path.postTVShow()
        mock_postData.assert_called_once_with(expected, MEDIAVIEWER_TV_PATH_URL)

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
        actualPathDict = self.path.getTVPaths()

        self.assertEquals(expectedPathDict, actualPathDict)

    @mock.patch('path.Path._getLocalPaths')
    @mock.patch('path.Path._getPaths')
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

        self.assertEquals(expectedDict, self.path.getAllTVPaths())

    @mock.patch('path.Path._buildLocalPaths')
    @mock.patch('path.Path._getLocalMoviePathsSetting')
    @mock.patch('path.Path._getLocalTVShowsPathsSetting')
    def test_getLocalPaths_noMovies(self,
                                    mock_getLocalTVShowsPathsSetting,
                                    mock_getLocalMoviePathsSetting,
                                    mock_buildLocalPaths):
        expected = mock_buildLocalPaths.return_value
        actual = self.path._getLocalPaths()
        self.assertEqual(expected, actual)
        mock_getLocalTVShowsPathsSetting.assert_called_once_with()
        self.assertFalse(mock_getLocalMoviePathsSetting.called)
        mock_buildLocalPaths.assert_called_once_with(
                mock_getLocalTVShowsPathsSetting.return_value)

    @mock.patch('path.Path._buildLocalPaths')
    @mock.patch('path.Path._getLocalMoviePathsSetting')
    @mock.patch('path.Path._getLocalTVShowsPathsSetting')
    def test_getLocalPaths_withMovies(self,
                                      mock_getLocalTVShowsPathsSetting,
                                      mock_getLocalMoviePathsSetting,
                                      mock_buildLocalPaths):
        expected = mock_buildLocalPaths.return_value
        actual = self.path._getLocalPaths(getMovies=True)
        self.assertEqual(expected, actual)
        mock_getLocalMoviePathsSetting.assert_called_once_with()
        self.assertFalse(mock_getLocalTVShowsPathsSetting.called)
        mock_buildLocalPaths.assert_called_once_with(
                mock_getLocalMoviePathsSetting.return_value)

    @mock.patch('path.requests')
    def test_getTVPathByLocalPathAndRemotePath(self,
                                             mock_requests):
        response = mock.MagicMock()
        mock_requests.get.return_value = response

        localpath = '/path/to/local/folder'
        remotepath = '/path/to/remote/folder'
        Path.getTVPathByLocalPathAndRemotePath(localpath,
                                             remotepath)

        mock_requests.get.assert_called_once_with(MEDIAVIEWER_TV_PATH_URL,
                                                  params={'localpath': localpath,
                                                          'remotepath': remotepath},
                                                  verify=VERIFY_REQUESTS,
                                                  auth=(WAITER_USERNAME, WAITER_PASSWORD))
        self.assertTrue(response.json.called)

    @mock.patch('path.requests')
    def test_getMoviePathByLocalPathAndRemotePath(self,
                                             mock_requests):
        response = mock.MagicMock()
        mock_requests.get.return_value = response

        localpath = '/path/to/local/folder'
        remotepath = '/path/to/remote/folder'
        Path.getMoviePathByLocalPathAndRemotePath(localpath,
                                             remotepath)

        mock_requests.get.assert_called_once_with(MEDIAVIEWER_MOVIE_PATH_URL,
                                                  params={'localpath': localpath,
                                                          'remotepath': remotepath},
                                                  verify=VERIFY_REQUESTS,
                                                  auth=(WAITER_USERNAME, WAITER_PASSWORD))
        self.assertTrue(response.json.called)

class TestGetLocalPathsFunctional(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.path = Path('localpath', 'remotepath')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_path_does_not_exist(self):
        filepath = os.path.join(self.temp_dir, 'test_file')
        expected = set()
        actual = self.path._buildLocalPaths([filepath])
        self.assertEqual(expected, actual)

    def test_paths_exist(self):
        files = set([tempfile.mkstemp(dir=self.temp_dir)[1]
                    for i in xrange(3)])
        expected = files
        actual = self.path._buildLocalPaths([self.temp_dir])
        self.assertEqual(expected, actual)
