import mock
from mock import call
import unittest

from movie_runner import MovieRunner

class TestMovieRunner(unittest.TestCase):
    def setUp(self):
        self.movieRunner = MovieRunner()
        self.movieRunner._postMovie = mock.MagicMock()

    @mock.patch('path.requests')
    def test_loadMovies(self,
                        mock_requests):
        test_data = {'results': [{'filename': 'movie1',
                                  'localpath': '/first/path',
                                  'pk': 1},
                                 {'filename': 'movie2',
                                  'localpath': '/second/path',
                                  'pk': 2},
                                 {'filename': 'movie3',
                                  'localpath': '/third/path',
                                  'pk': 3}],
                     'next': None}
        mock_request = mock.MagicMock()
        mock_request.json.return_value = test_data
        mock_requests.get.side_effect = [mock_request]

        self.movieRunner.loadMovies()

        expected = set(['movie1',
                        'movie2',
                        'movie3',
                        ])
        self.assertEquals(expected, self.movieRunner.movies)

    @mock.patch('path.Path.getMoviePathByLocalPathAndRemotePath')
    @mock.patch('path.requests')
    @mock.patch('movie_runner.reencodeFilesInDirectory')
    @mock.patch('movie_runner.commands.getoutput')
    @mock.patch('movie_runner.MovieRunner._getLocalMoviePathsSetting')
    def test_postMovies(self,
                        mock_getLocalMoviePathsSetting,
                        mock_commands_getoutput,
                        mock_reencodeFilesInDirectory,
                        mock_requests,
                        mock_getMoviePathByLocalPathAndRemotePath):
        def gen_test_data(num):
            return [dict(results=[dict(pk=i)]) for i in xrange(1, num + 1)]
        mock_getMoviePathByLocalPathAndRemotePath.side_effect = gen_test_data(5)
        mock_getLocalMoviePathsSetting.return_value = ['/path/to/movies']
        mock_commands_getoutput.return_value = 'movie1\nmovie2\nmovie3'
        mock_reencodeFilesInDirectory.return_value = None

        self.movieRunner.movies = ['/path/to/other/movies']
        self.movieRunner.postMovies()

        self.movieRunner._postMovie.assert_has_calls([call('movie1'),
                                                      call('movie3')],
                                                      any_order=True)
        self.assertEqual(2, self.movieRunner._postMovie.call_count)

        mock_reencodeFilesInDirectory.assert_has_calls([call('movie1'),
                                                        call('movie3')],
                                                        any_order=True)
        self.assertEqual(2, mock_reencodeFilesInDirectory.call_count)

