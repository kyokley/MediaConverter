import mock
import unittest

from movie_runner import MovieRunner

class TestMovieRunner(unittest.TestCase):
    def setUp(self):
        self.movieRunner = MovieRunner()

    @mock.patch('movie_runner.requests')
    def test_loadMovies(self,
                        mock_requests):
        test_data = {'results': [{'filename': 'movie1'},
                                 {'filename': 'movie2'},
                                 {'filename': 'movie3'}],
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
