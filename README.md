# QuizCraftAI

QuizCraftAI is a web application that uses AI to generate multiple-choice quizzes on various topics. Users can test their knowledge, receive instant feedback, and see their scores on a leaderboard.

## Features

- AI-powered quiz generation using OpenAI's GPT-3.5-turbo.
- Multiple-choice questions with four options.
- Explanations for correct answers.
- User scores saved to a leaderboard.
- Personalized feedback based on performance.
- Interactive web interface built with Gradio.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd QuizCraftAI
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up OpenAI API Key:**
    - Create a file named `.env` in the root directory of the project.
    - Add your OpenAI API key to the `.env` file like this:
      ```
      OPENAI_API_KEY='your_actual_api_key_here'
      ```
    - **Important**: Make sure the `.env` file is listed in your `.gitignore` file to prevent accidentally committing your API key. If `.gitignore` doesn't exist or doesn't include `.env`, add `.env` to a new line in `.gitignore`.

## Usage

1.  **Run the application:**
    ```bash
    python app.py
    ```
2.  Open your web browser and go to the URL provided by Gradio (usually `http://127.0.0.1:7860`).
3.  Enter your name and the desired quiz topic.
4.  Click "Generate Quiz" and answer the questions.
5.  View your results, feedback, and the leaderboard.

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.
