import unittest
import os
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock
import json # Added import

# Add the parent directory to sys.path to allow importing app
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import functions from app.py
# Assuming app.py is in the same directory or accessible via PYTHONPATH
# For this subtask, we'll define simplified versions or assume they can be imported.
# If direct import of app.py causes issues in the subtask environment,
# the subtask may need to redefine the functions being tested or adjust paths.

# For now, let's assume app.py can be imported or its functions are accessible.
# The subtask might need to create placeholder functions if app cannot be imported directly.
# This is a common challenge in isolated subtask environments.

# Let's assume app.py is in the same directory for the purpose of this subtask.
# If app.py is in the root, and test_app.py is also in the root, direct import should work.
import app

# Define the path to a temporary results file for testing
TEST_RESULTS_FILE = "test_results.csv"

class TestAppFunctions(unittest.TestCase):

    def setUp(self):
        # Ensure a clean state before each test
        if os.path.exists(TEST_RESULTS_FILE):
            os.remove(TEST_RESULTS_FILE)
        # Override the RESULTS_FILE in app module for testing
        self.original_results_file = app.RESULTS_FILE
        app.RESULTS_FILE = TEST_RESULTS_FILE

    def tearDown(self):
        # Clean up created files after tests
        if os.path.exists(TEST_RESULTS_FILE):
            os.remove(TEST_RESULTS_FILE)
        # Restore original RESULTS_FILE in app module
        app.RESULTS_FILE = self.original_results_file

    def test_save_result(self):
        # Test saving a single result
        app.save_result("TestUser1", 8, 10)
        self.assertTrue(os.path.exists(TEST_RESULTS_FILE))
        df = pd.read_csv(TEST_RESULTS_FILE)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["Name"], "TestUser1")
        self.assertEqual(df.iloc[0]["Score"], 8)
        self.assertEqual(df.iloc[0]["Out Of"], 10)

        # Test saving another result (appending)
        app.save_result("TestUser2", 5, 10)
        df = pd.read_csv(TEST_RESULTS_FILE)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[1]["Name"], "TestUser2")

    def test_load_leaderboard_empty(self):
        # Test loading leaderboard when file doesn't exist
        leaderboard = app.load_leaderboard()
        self.assertTrue(isinstance(leaderboard, pd.DataFrame))
        self.assertTrue(leaderboard.empty)

    def test_load_leaderboard_with_data(self):
        # Setup: Create a dummy results file
        data = {
            "Name": ["UserA", "UserB", "UserC"],
            "Score": [7, 9, 6],
            "Out Of": [10, 10, 10],
            "Timestamp": [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]
        }
        dummy_df = pd.DataFrame(data)
        dummy_df.to_csv(TEST_RESULTS_FILE, index=False)

        leaderboard = app.load_leaderboard()
        self.assertEqual(len(leaderboard), 3)
        # Leaderboard should be sorted by Score descending
        self.assertEqual(leaderboard.iloc[0]["Name"], "UserB")
        self.assertEqual(leaderboard.iloc[0]["Score"], 9)
        self.assertEqual(leaderboard.iloc[1]["Name"], "UserA")
        self.assertEqual(leaderboard.iloc[2]["Name"], "UserC")

    def test_load_leaderboard_top_10(self):
        # Setup: Create a dummy results file with 12 entries
        names = [f"User{i}" for i in range(12)]
        scores = [(i % 5) + 5 for i in range(12)] # Scores from 5 to 9
        data = {
            "Name": names,
            "Score": scores,
            "Out Of": [10] * 12,
            "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] * 12
        }
        dummy_df = pd.DataFrame(data)
        # Ensure scores are varied enough for sorting
        dummy_df = dummy_df.sort_values(by="Score", ascending=False)
        dummy_df.to_csv(TEST_RESULTS_FILE, index=False)

        leaderboard = app.load_leaderboard()
        self.assertEqual(len(leaderboard), 10) # Should only load top 10

    @patch('app.client') # Target 'app.client' which is the OpenAI client instance
    def test_generate_quiz_success(self, mock_openai_client):
        # Configure the mock response from OpenAI API
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps([
            {
                "question": "What is 2+2?",
                "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
                "correct_answer": "B",
                "explanation": "2+2 equals 4."
            }
        ])
        mock_completion.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_completion

        questions = app.generate_quiz("math")
        self.assertIsNotNone(questions)
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["question"], "What is 2+2?")
        # Verify that the mock was called
        mock_openai_client.chat.completions.create.assert_called_once()

    @patch('app.client')
    def test_generate_quiz_api_error(self, mock_openai_client):
        # Configure the mock to raise an exception
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

        questions = app.generate_quiz("science")
        self.assertIsNone(questions)
        mock_openai_client.chat.completions.create.assert_called_once()

    @patch('app.client')
    def test_generate_quiz_json_decode_error(self, mock_openai_client):
        # Configure the mock response with invalid JSON
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "This is not valid JSON"
        mock_completion.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_completion

        questions = app.generate_quiz("history")
        self.assertIsNone(questions) # Due to the new error handling
        mock_openai_client.chat.completions.create.assert_called_once()

    @patch('app.client')
    def test_generate_feedback_success(self, mock_openai_client):
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Great job! You did well."
        mock_completion.choices = [mock_choice]
        mock_openai_client.chat.completions.create.return_value = mock_completion

        feedback = app.generate_feedback(8, 10, "Correct questions details", "Incorrect questions details")
        self.assertEqual(feedback, "Great job! You did well.")
        mock_openai_client.chat.completions.create.assert_called_once()

    @patch('app.client')
    def test_generate_feedback_api_error(self, mock_openai_client):
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

        feedback = app.generate_feedback(5, 10, "", "Some incorrect")
        self.assertEqual(feedback, "Unable to generate feedback due to an error.")
        mock_openai_client.chat.completions.create.assert_called_once()

# It's good practice to be able to run tests directly
if __name__ == '__main__':
    unittest.main()
