import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Ensure we can import frontend
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from frontend.main import check_for_updates

class TestAutoUpdate(unittest.TestCase):
    @patch('frontend.main.QApplication')
    @patch('frontend.main.QMessageBox')
    @patch('frontend.main.QTimer')
    @patch('frontend.main.subprocess.Popen')
    @patch('frontend.main.check_updates_api')
    @patch('requests.get')
    def test_auto_install_with_setup(self, mock_get, mock_api, mock_popen, mock_timer, mock_msgbox, mock_qapp):
        # Mock the API response
        mock_api.return_value = {
            'version': 'v1.0.1',
            'path': '/mock/path',
            'setup_url': 'http://mock.url/setup.exe',
            'setup_name': 'setup.exe'
        }
        
        # Mock requests.get response
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [b"fake_data"]
        mock_get.return_value.__enter__.return_value = mock_resp
        
        # We need to capture the _handle callback when singleShot is called
        def timer_side_effect(delay, func):
            func() # execute _handle immediately
            
        mock_timer.singleShot.side_effect = timer_side_effect
        
        # Mock threading to execute synchronously for testing
        with patch('threading.Thread') as mock_thread_cls:
            # Create a mock thread instance
            mock_thread_inst = MagicMock()
            mock_thread_cls.return_value = mock_thread_inst
            
            # When start() is called, execute the target function synchronously
            def start_side_effect():
                # Get the target from the Thread constructor call
                target = mock_thread_cls.call_args.kwargs['target']
                target()
                
            mock_thread_inst.start.side_effect = start_side_effect
            
            # Call the function
            check_for_updates()
            
            # Check api is called
            mock_api.assert_called_once()
            
            # Check the background download was called
            mock_get.assert_called_once_with('http://mock.url/setup.exe', stream=True, timeout=120)
            
            # Check subprocess.Popen was called with correct flags
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            self.assertTrue(args[0].endswith('setup.exe'))
            self.assertIn('/SILENT', args)
            self.assertIn('/CLOSEAPPLICATIONS', args)
            self.assertIn('/RESTARTAPPLICATIONS', args)
            
            # Ensure the app was commanded to quit
            mock_qapp.quit.assert_called_once()
            
            # Ensure no confirmation dialogs were spawned
            mock_msgbox.return_value.exec.assert_not_called()

if __name__ == '__main__':
    unittest.main()
