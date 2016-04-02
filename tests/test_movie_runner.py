import mock
from mock import call
import unittest

from movie_runner import MovieRunner

class TestMovieRunner(unittest.TestCase):
    def setUp(self):
        self.movieRunner = MovieRunner()
        self.movieRunner._postMovie = mock.MagicMock()

    @mock.patch('movie_runner.MovieRunner.postMovies')
    def test_run(self,
                 mock_postMovies):
        self.movieRunner.run()
        self.assertEquals(1, mock_postMovies.call_count)

    @mock.patch('path.Path.getMoviePathByLocalPathAndRemotePath')
    @mock.patch('file.requests')
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
        mock_json = mock.MagicMock()
        mock_json.json.return_value = dict(next=None,
                                           results=[{'filename': 'movie1',
                                                     'localpath': '/path/to/movies'},
                                                    {'filename': 'movie3',
                                                     'localpath': '/path/to/movies'}])

        mock_requests.get.return_value = mock_json
        self.movieRunner.postMovies()

        self.movieRunner._postMovie.assert_has_calls([call('movie2', 1)],
                                                      any_order=True)
        self.assertEqual(1, self.movieRunner._postMovie.call_count)

        mock_reencodeFilesInDirectory.assert_has_calls([call('/path/to/movies/movie2')],
                                                        any_order=True)
        self.assertEqual(1, mock_reencodeFilesInDirectory.call_count)
