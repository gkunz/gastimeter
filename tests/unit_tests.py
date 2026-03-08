#
# SPDX-FileCopyrightText: 2024 Georg Kunz <der.schorsch@gmail.com>
# SPDX-License-Identifier: MIT
#
import argparse
import cv2 as cv
import json
import logging
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import numpy as np

from gastimeter.analyzer import send_request
from gastimeter.imagegrabber import capture_image
from gastimeter.cli.cli import (
    process_command_line_arguments,
    configure_logging,
    validate_configuration,
)
from gastimeter.configator import Config
from gastimeter.error import exit_with_error
from gastimeter.responseparser import parse_response
from gastimeter.preprocessor import preprocess_image, contrast_and_brightness, correct_rotation

TEST_DIR = os.path.dirname(os.path.abspath(__file__))

class TestResponseParser(unittest.TestCase):
    '''
    Basic unit tests.
    '''

    def test_pre_process_image(self):
        '''
        Test the image pre-processor. There is no assertion, but instead if all
        operations success, the test is assumed to pass.
        '''
        filename = os.path.join(TEST_DIR, 'testdata', 'test-image.jpg')
        if not os.path.exists(filename):
            self.assertTrue(False, f'Image \'{filename}\' not found.')

        image = cv.imread(filename)
        image = preprocess_image(image)


    def test_parsing_static_response(self):
        '''
        Test the response parser on a static reponse json.
        '''
        with open(os.path.join(TEST_DIR, 'testdata', 'test-response.json')) as f:
            content = f.read()
            response = json.loads(content)
            reading = parse_response(response)
            self.assertEqual(reading, 5650.81)


class TestResponseParserEdgeCases(unittest.TestCase):
    '''
    Tests for various code paths in the response parser.
    '''

    def _make_response(self, *line_texts):
        '''Helper to build a minimal Azure OCR response structure.'''
        lines = [{'text': t} for t in line_texts]
        return {'readResult': {'blocks': [{'lines': lines}]}}

    # --- 8 digits with comma/period (decimal detected, len==8) ---

    def test_8_digits_with_period(self):
        response = self._make_response('05650.81')
        self.assertEqual(parse_response(response), 5650.81)

    def test_8_digits_with_comma(self):
        response = self._make_response('05650,81')
        self.assertEqual(parse_response(response), 5650.81)

    def test_8_digits_with_comma_different_value(self):
        response = self._make_response('12345,67')
        self.assertEqual(parse_response(response), 12345.67)

    # --- 8 digits without decimal (misread decimal as digit) ---

    def test_8_digits_no_decimal(self):
        response = self._make_response('05650081')
        # char at index 5 replaced with '.': '05650.81'
        self.assertEqual(parse_response(response), 5650.81)

    def test_8_digits_no_decimal_different_value(self):
        response = self._make_response('12345067')
        # '12345.67'
        self.assertEqual(parse_response(response), 12345.67)

    # --- 7 digits without decimal (all digits found, decimal missed) ---

    def test_7_digits_no_decimal(self):
        response = self._make_response('5650081')
        # '56500' + '.' + '81' = '56500.81'
        self.assertEqual(parse_response(response), 56500.81)

    def test_7_digits_no_decimal_different_value(self):
        response = self._make_response('1234567')
        # '12345' + '.' + '67' = '12345.67'
        self.assertEqual(parse_response(response), 12345.67)

    # --- Whitespace handling ---

    def test_whitespace_in_text(self):
        response = self._make_response('0565 0,81')
        # spaces removed -> '05650,81' (8 chars with comma) -> 5650.81
        self.assertEqual(parse_response(response), 5650.81)

    def test_multiple_spaces(self):
        response = self._make_response('0 5 6 5 0 8 1')
        # spaces removed -> '0565081' (7 chars, no decimal) -> '05650.81'
        self.assertEqual(parse_response(response), 5650.81)

    # --- Multiple lines concatenation ---

    def test_multiple_lines(self):
        response = self._make_response('0565', '0,81')
        # concatenated -> '05650,81' (8 chars with comma) -> 5650.81
        self.assertEqual(parse_response(response), 5650.81)

    def test_multiple_lines_no_decimal(self):
        response = self._make_response('0565', '081')
        # concatenated -> '0565081' (7 chars, no decimal) -> '05650.81'
        self.assertEqual(parse_response(response), 5650.81)

    # --- Error: decimal found but not 8 digits ---

    def test_decimal_wrong_length_too_short(self):
        response = self._make_response('565.08')
        with self.assertRaises(SystemExit):
            parse_response(response)

    def test_decimal_wrong_length_too_long(self):
        response = self._make_response('056500.810')
        with self.assertRaises(SystemExit):
            parse_response(response)

    def test_comma_wrong_length(self):
        response = self._make_response('565,08')
        with self.assertRaises(SystemExit):
            parse_response(response)

    # --- Error: no decimal and wrong digit count ---

    def test_too_few_digits_no_decimal(self):
        response = self._make_response('56508')
        with self.assertRaises(SystemExit):
            parse_response(response)

    def test_too_many_digits_no_decimal(self):
        response = self._make_response('056500810')
        with self.assertRaises(SystemExit):
            parse_response(response)

    def test_single_digit(self):
        response = self._make_response('5')
        with self.assertRaises(SystemExit):
            parse_response(response)

    # --- Error: non-numeric characters causing float conversion failure ---

    def test_non_numeric_8_chars_with_period(self):
        response = self._make_response('abcde.fg')
        with self.assertRaises(SystemExit):
            parse_response(response)

    def test_non_numeric_7_chars(self):
        response = self._make_response('abcdefg')
        with self.assertRaises(SystemExit):
            parse_response(response)


class TestConfig(unittest.TestCase):
    '''
    Tests for the Config configuration handler.
    '''

    def tearDown(self):
        # Reset class-level state between tests
        Config.args = None
        Config.subscription_key = None
        Config.service_name = None

    @patch.dict(os.environ, {
        'AZURE_SUBSCRIPTION_KEY': 'test-key-123',
        'AZURE_SERVICE_NAME': 'test-service',
    })
    def test_init_config_success(self):
        args = object()
        Config.init_config(args)
        self.assertIs(Config.args, args)
        self.assertEqual(Config.subscription_key, 'test-key-123')
        self.assertEqual(Config.service_name, 'test-service')

    @patch.dict(os.environ, {
        'AZURE_SUBSCRIPTION_KEY': 'test-key-123',
    }, clear=True)
    def test_missing_service_name(self):
        with self.assertRaises(SystemExit):
            Config.init_config(object())

    @patch.dict(os.environ, {
        'AZURE_SERVICE_NAME': 'test-service',
    }, clear=True)
    def test_missing_subscription_key(self):
        with self.assertRaises(SystemExit):
            Config.init_config(object())

    @patch.dict(os.environ, {}, clear=True)
    def test_both_env_vars_missing(self):
        with self.assertRaises(SystemExit):
            Config.init_config(object())

    @patch.dict(os.environ, {
        'AZURE_SUBSCRIPTION_KEY': 'test-key-123',
        'AZURE_SERVICE_NAME': 'test-service',
    })
    def test_missing_key_does_not_set_service_name(self):
        '''When subscription key is missing, service_name should not be set.'''
        # Remove only the key to hit the first exit_with_error
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                Config.init_config(object())
        self.assertIsNone(Config.subscription_key)
        self.assertIsNone(Config.service_name)

    @patch.dict(os.environ, {
        'AZURE_SUBSCRIPTION_KEY': '',
        'AZURE_SERVICE_NAME': '',
    })
    def test_empty_string_env_vars_accepted(self):
        '''os.environ.get returns '' for set-but-empty vars, which is not None.'''
        Config.init_config(object())
        self.assertEqual(Config.subscription_key, '')
        self.assertEqual(Config.service_name, '')


class TestExitWithError(unittest.TestCase):
    '''
    Tests for the exit_with_error utility function.
    '''

    def test_exit_code(self):
        with self.assertRaises(SystemExit) as cm:
            exit_with_error('test error')
        self.assertEqual(cm.exception.code, -1)

    def test_prints_zero_to_stdout(self):
        import io
        captured = io.StringIO()
        with patch('sys.stdout', captured):
            with self.assertRaises(SystemExit):
                exit_with_error('test error')
        self.assertEqual(captured.getvalue().strip(), '0')

    def test_logs_error_message(self):
        with self.assertLogs(level='ERROR') as log:
            with self.assertRaises(SystemExit):
                exit_with_error('something went wrong')
        self.assertEqual(len(log.output), 1)
        self.assertIn('something went wrong', log.output[0])


class TestProcessCommandLineArguments(unittest.TestCase):
    '''
    Tests for CLI argument parsing.
    '''

    @patch('sys.argv', ['gastimeter', '-i', 'photo.jpg'])
    def test_image_flag(self):
        args = process_command_line_arguments()
        self.assertEqual(args.image, 'photo.jpg')
        self.assertFalse(args.capture)

    @patch('sys.argv', ['gastimeter', '-c'])
    def test_capture_flag(self):
        args = process_command_line_arguments()
        self.assertTrue(args.capture)
        self.assertIsNone(args.image)

    @patch('sys.argv', ['gastimeter', '-c', '-o', '/tmp/out'])
    def test_output_directory(self):
        args = process_command_line_arguments()
        self.assertEqual(args.output, '/tmp/out')

    @patch('sys.argv', ['gastimeter', '-c'])
    def test_output_defaults_to_current_dir(self):
        args = process_command_line_arguments()
        self.assertEqual(args.output, os.path.curdir)

    @patch('sys.argv', ['gastimeter', '-c', '-p'])
    def test_preprocess_flag(self):
        args = process_command_line_arguments()
        self.assertTrue(args.preprocess)

    @patch('sys.argv', ['gastimeter', '-c'])
    def test_preprocess_defaults_to_false(self):
        args = process_command_line_arguments()
        self.assertFalse(args.preprocess)

    @patch('sys.argv', ['gastimeter', '-c', '-d'])
    def test_debug_flag(self):
        args = process_command_line_arguments()
        self.assertTrue(args.debug)

    @patch('sys.argv', ['gastimeter', '-c'])
    def test_debug_defaults_to_false(self):
        args = process_command_line_arguments()
        self.assertFalse(args.debug)

    @patch('sys.argv', ['gastimeter', '-v'])
    def test_version_flag(self):
        with self.assertRaises(SystemExit) as cm:
            process_command_line_arguments()
        self.assertEqual(cm.exception.code, 0)

    @patch('sys.argv', ['gastimeter', '-i', 'photo.jpg', '-c', '-d', '-p', '-o', '/tmp'])
    def test_all_flags_combined(self):
        args = process_command_line_arguments()
        self.assertEqual(args.image, 'photo.jpg')
        self.assertTrue(args.capture)
        self.assertTrue(args.debug)
        self.assertTrue(args.preprocess)
        self.assertEqual(args.output, '/tmp')


class TestConfigureLogging(unittest.TestCase):
    '''
    Tests for logging configuration.
    '''

    def _make_args(self, debug=False, output=None):
        args = argparse.Namespace()
        args.debug = debug
        args.output = output or tempfile.mkdtemp()
        return args

    def test_creates_output_directory_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, 'newdir')
            args = self._make_args(output=output)
            # Reset logging to allow basicConfig to take effect
            root = logging.getLogger()
            for h in root.handlers[:]:
                root.removeHandler(h)
            configure_logging(args)
            self.assertTrue(os.path.isdir(output))

    def test_log_file_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            args = self._make_args(output=tmpdir)
            root = logging.getLogger()
            for h in root.handlers[:]:
                root.removeHandler(h)
            configure_logging(args)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'gastimeter.log')))

    def test_debug_sets_debug_level(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            args = self._make_args(debug=True, output=tmpdir)
            root = logging.getLogger()
            for h in root.handlers[:]:
                root.removeHandler(h)
            configure_logging(args)
            self.assertEqual(root.level, logging.DEBUG)

    def test_no_debug_sets_info_level(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            args = self._make_args(debug=False, output=tmpdir)
            root = logging.getLogger()
            for h in root.handlers[:]:
                root.removeHandler(h)
            configure_logging(args)
            self.assertEqual(root.level, logging.INFO)


class TestValidateConfiguration(unittest.TestCase):
    '''
    Tests for CLI configuration validation.
    '''

    def tearDown(self):
        Config.args = None
        Config.subscription_key = None
        Config.service_name = None

    @patch.dict(os.environ, {
        'AZURE_SUBSCRIPTION_KEY': 'key',
        'AZURE_SERVICE_NAME': 'name',
    })
    def test_image_only_succeeds(self):
        args = argparse.Namespace(image='photo.jpg', capture=False)
        validate_configuration(args)
        self.assertIs(Config.args, args)

    @patch.dict(os.environ, {
        'AZURE_SUBSCRIPTION_KEY': 'key',
        'AZURE_SERVICE_NAME': 'name',
    })
    def test_capture_only_succeeds(self):
        args = argparse.Namespace(image=None, capture=True)
        validate_configuration(args)
        self.assertIs(Config.args, args)

    def test_both_image_and_capture_exits(self):
        args = argparse.Namespace(image='photo.jpg', capture=True)
        with self.assertRaises(SystemExit):
            validate_configuration(args)

    def test_neither_image_nor_capture_exits(self):
        args = argparse.Namespace(image=None, capture=False)
        with self.assertRaises(SystemExit):
            validate_configuration(args)


class TestAnalyzer(unittest.TestCase):
    '''
    Tests for the Azure OCR analyzer (send_request), with mocked HTTP.
    '''

    def setUp(self):
        Config.subscription_key = 'test-key-123'
        Config.service_name = 'test-service'

    def tearDown(self):
        Config.args = None
        Config.subscription_key = None
        Config.service_name = None

    def _make_image(self):
        '''Create a small dummy image (10x10 black).'''
        import numpy as np
        return np.zeros((10, 10, 3), dtype=np.uint8)

    def _mock_response(self, status=200, body=None):
        '''Build a mock HTTP response object.'''
        if body is None:
            body = {'readResult': {'blocks': [{'lines': [{'text': '05650.81'}]}]}}
        encoded = json.dumps(body).encode('utf-8')
        resp = MagicMock()
        resp.status = status
        resp.read.return_value = encoded
        return resp

    @patch('gastimeter.analyzer.http.client.HTTPSConnection')
    def test_successful_request_returns_parsed_json(self, mock_conn_cls):
        expected_body = {'readResult': {'blocks': [{'lines': [{'text': '05650.81'}]}]}}
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = self._mock_response(200, expected_body)
        mock_conn_cls.return_value = mock_conn

        result = send_request(self._make_image())
        self.assertEqual(result, expected_body)

    @patch('gastimeter.analyzer.http.client.HTTPSConnection')
    def test_connects_to_correct_host(self, mock_conn_cls):
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = self._mock_response()
        mock_conn_cls.return_value = mock_conn

        send_request(self._make_image())
        mock_conn_cls.assert_called_once()
        self.assertEqual(mock_conn_cls.call_args[0][0], 'test-service.cognitiveservices.azure.com')

    @patch('gastimeter.analyzer.http.client.HTTPSConnection')
    def test_sends_correct_headers(self, mock_conn_cls):
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = self._mock_response()
        mock_conn_cls.return_value = mock_conn

        send_request(self._make_image())
        call_args = mock_conn.request.call_args
        headers = call_args[0][3]
        self.assertEqual(headers['Content-Type'], 'application/octet-stream')
        self.assertEqual(headers['Ocp-Apim-Subscription-Key'], 'test-key-123')

    @patch('gastimeter.analyzer.http.client.HTTPSConnection')
    def test_sends_post_request_with_correct_path(self, mock_conn_cls):
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = self._mock_response()
        mock_conn_cls.return_value = mock_conn

        send_request(self._make_image())
        call_args = mock_conn.request.call_args
        method = call_args[0][0]
        path = call_args[0][1]
        self.assertEqual(method, 'POST')
        self.assertIn('/computervision/imageanalysis:analyze', path)
        self.assertIn('api-version=2024-02-01', path)
        self.assertIn('features=read', path)
        self.assertIn('language=en', path)

    @patch('gastimeter.analyzer.http.client.HTTPSConnection')
    def test_sends_jpeg_encoded_body(self, mock_conn_cls):
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = self._mock_response()
        mock_conn_cls.return_value = mock_conn

        send_request(self._make_image())
        call_args = mock_conn.request.call_args
        body = call_args[0][2]
        # JPEG files start with the magic bytes FF D8
        self.assertEqual(body[:2], b'\xff\xd8')

    @patch('gastimeter.analyzer.http.client.HTTPSConnection')
    def test_non_200_status_exits(self, mock_conn_cls):
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = self._mock_response(status=400, body={'error': 'bad request'})
        mock_conn_cls.return_value = mock_conn

        with self.assertRaises(SystemExit):
            send_request(self._make_image())

    @patch('gastimeter.analyzer.http.client.HTTPSConnection')
    def test_500_status_exits(self, mock_conn_cls):
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = self._mock_response(status=500, body={'error': 'server error'})
        mock_conn_cls.return_value = mock_conn

        with self.assertRaises(SystemExit):
            send_request(self._make_image())

    @patch('gastimeter.analyzer.http.client.HTTPSConnection')
    def test_connection_closed_after_request(self, mock_conn_cls):
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = self._mock_response()
        mock_conn_cls.return_value = mock_conn

        send_request(self._make_image())
        mock_conn.close.assert_called_once()


class TestImageGrabber(unittest.TestCase):
    '''
    Tests for capture_image with mocked OpenCV VideoCapture.
    '''

    @patch('gastimeter.imagegrabber.cv.VideoCapture')
    def test_camera_not_opened_exits(self, mock_capture_cls):
        mock_cam = MagicMock()
        mock_cam.isOpened.return_value = False
        mock_capture_cls.return_value = mock_cam

        with self.assertRaises(SystemExit):
            capture_image()

    @patch('gastimeter.imagegrabber.cv.VideoCapture')
    def test_read_failure_exits(self, mock_capture_cls):
        mock_cam = MagicMock()
        mock_cam.isOpened.return_value = True
        mock_cam.read.return_value = (False, None)
        mock_capture_cls.return_value = mock_cam

        with self.assertRaises(SystemExit):
            capture_image()

    @patch('gastimeter.imagegrabber.cv.VideoCapture')
    def test_successful_capture_returns_image(self, mock_capture_cls):
        fake_image = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cam = MagicMock()
        mock_cam.isOpened.return_value = True
        mock_cam.read.return_value = (True, fake_image)
        mock_capture_cls.return_value = mock_cam

        result = capture_image()
        np.testing.assert_array_equal(result, fake_image)

    @patch('gastimeter.imagegrabber.cv.VideoCapture')
    def test_uses_camera_index_zero(self, mock_capture_cls):
        mock_cam = MagicMock()
        mock_cam.isOpened.return_value = True
        mock_cam.read.return_value = (True, np.zeros((10, 10, 3), dtype=np.uint8))
        mock_capture_cls.return_value = mock_cam

        capture_image()
        mock_capture_cls.assert_called_once_with(0)


class TestContrastAndBrightness(unittest.TestCase):
    '''
    Tests for the contrast_and_brightness function.
    '''

    def test_known_pixel_values(self):
        # Single pixel grayscale image with value 100
        image = np.full((1, 1), 100, dtype=np.uint8)
        result = contrast_and_brightness(image)
        # cv.addWeighted(image, 1.2, image, 0, 10) => 100*1.2 + 100*0 + 10 = 130
        self.assertEqual(result[0, 0], 130)

    def test_clamps_at_255(self):
        # Value 250: 250*1.2 + 10 = 310 -> clamped to 255
        image = np.full((1, 1), 250, dtype=np.uint8)
        result = contrast_and_brightness(image)
        self.assertEqual(result[0, 0], 255)

    def test_zero_pixel(self):
        # Value 0: 0*1.2 + 10 = 10
        image = np.full((1, 1), 0, dtype=np.uint8)
        result = contrast_and_brightness(image)
        self.assertEqual(result[0, 0], 10)

    def test_preserves_shape(self):
        image = np.zeros((50, 80), dtype=np.uint8)
        result = contrast_and_brightness(image)
        self.assertEqual(result.shape, (50, 80))


class TestCorrectRotation(unittest.TestCase):
    '''
    Tests for the correct_rotation function.
    '''

    def test_no_lines_detected_returns_unchanged(self):
        # Uniform image — no edges, no Hough lines
        image = np.full((100, 100), 128, dtype=np.uint8)
        result = correct_rotation(image)
        # Returns (image, 0) tuple when no lines found
        if isinstance(result, tuple):
            result_image, angle = result
            self.assertEqual(angle, 0)
            np.testing.assert_array_equal(result_image, image)
        else:
            np.testing.assert_array_equal(result, image)

    def test_horizontal_line_no_rotation_needed(self):
        # Draw a perfectly horizontal line — median angle should be ~0
        image = np.zeros((100, 200), dtype=np.uint8)
        cv.line(image, (10, 50), (190, 50), 255, 2)
        result = correct_rotation(image)
        # Even if rotation is applied, a 0-degree rotation should preserve content
        if isinstance(result, tuple):
            result = result[0]
        self.assertEqual(result.shape, image.shape)


class TestPreprocessImage(unittest.TestCase):
    '''
    Tests for the preprocess_image orchestration function.
    '''

    def _make_bgr_image(self, height=100, width=100):
        return np.zeros((height, width, 3), dtype=np.uint8)

    def test_output_is_grayscale(self):
        image = self._make_bgr_image()
        result = preprocess_image(image)
        # Grayscale images are 2D
        self.assertEqual(len(result.shape), 2)

    def test_output_shape_matches_input_dimensions(self):
        image = self._make_bgr_image(80, 120)
        result = preprocess_image(image)
        self.assertEqual(result.shape, (80, 120))

    def test_flip_180(self):
        # Create an image with a distinct top-left pixel
        image = np.zeros((10, 10, 3), dtype=np.uint8)
        image[0, 0] = [200, 200, 200]  # bright top-left in BGR

        result = preprocess_image(image)
        # After 180 flip, the top-left pixel should end up at bottom-right
        # The bright pixel had BGR (200,200,200) -> gray 200 -> after contrast: 200*1.2+10=250
        # The dark pixels had 0 -> after contrast: 10
        # Verify the bottom-right is brighter than top-left
        self.assertGreater(result[-1, -1], result[0, 0])

    def test_processes_color_image_without_error(self):
        # Random color image should process without crashing
        image = np.random.randint(0, 256, (50, 80, 3), dtype=np.uint8)
        result = preprocess_image(image)
        self.assertEqual(len(result.shape), 2)
        self.assertEqual(result.shape, (50, 80))


if __name__ == '__main__':
    unittest.main()
