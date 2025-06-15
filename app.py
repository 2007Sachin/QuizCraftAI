import gradio as gr
import json
import os
import pandas as pd
from datetime import datetime
from openai import OpenAI
import logging
import config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=config.OPENAI_API_KEY)

RESULTS_FILE = "results.csv"

# Generate quiz questions
def generate_quiz(topic):
    logger.debug(f"Generating quiz for topic: {topic}")
    prompt = """
    Generate exactly 10 multiple-choice questions on the topic '{topic}'. Each question should have:
    - A clear question
    - Four answer options (labeled A, B, C, D)
    - One correct answer
    - A brief explanation for the correct answer
    Format the output as a JSON array of objects, where each object contains:
    - question: string
    - options: object with keys A, B, C, D
    - correct_answer: string (A, B, C, or D)
    - explanation: string
    Ensure the JSON is valid and properly formatted. Example:
    [
        {{
            "question": "What is 2+2?",
            "options": {{"A": "3", "B": "4", "C": "5", "D": "6"}},
            "correct_answer": "B",
            "explanation": "2+2 equals 4."
        }}
    ]
    """.format(topic=topic)

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000
        )
        quiz_json = response.choices[0].message.content
        questions = json.loads(quiz_json)
        logger.debug(f"Generated questions: {json.dumps(questions, indent=2)}")
        return questions
    except Exception as e:
        logger.error(f"Error generating quiz: {str(e)}")
        return None

# Save result to leaderboard
def save_result(name, score, total):
    df = pd.DataFrame([{
        "Name": name,
        "Score": score,
        "Out Of": total,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    if os.path.exists(RESULTS_FILE):
        df.to_csv(RESULTS_FILE, mode='a', header=False, index=False)
    else:
        df.to_csv(RESULTS_FILE, index=False)

# Load leaderboard
def load_leaderboard():
    if os.path.exists(RESULTS_FILE):
        df = pd.read_csv(RESULTS_FILE)
        return df.sort_values(by="Score", ascending=False).head(10)
    return pd.DataFrame()

# Generate feedback
def generate_feedback(score, total, correct_questions, incorrect_questions):
    prompt = """
    The user scored {score} out of {total} on a quiz. Below are the questions they answered correctly:
    {correct_questions}
    
    Below are the questions they answered incorrectly, including explanations:
    {incorrect_questions}
    
    Provide concise feedback (2-3 sentences) to help the user improve. Highlight their performance, praise correct answers, and suggest improvements for incorrect ones. If all answers are correct, congratulate them and encourage continued learning.
    """.format(
        score=score,
        total=total,
        correct_questions=correct_questions or "None",
        incorrect_questions=incorrect_questions or "None"
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Feedback generation error: {str(e)}")
        return "Unable to generate feedback due to an error."

# Main quiz application
def main():
    # Initialize state
    state = {
        "step": "start",
        "quiz": None,
        "current_question": 0,
        "score": 0,
        "user_answers": [],
        "username": "",
        "topic": "",
        "message": "",
        "option_values": {}  # To store option labels to values mapping
    }

    with gr.Blocks(title="AI Quiz Generator", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🎓 AI Quiz Generator")
        state_component = gr.State(value=state)
        output_message = gr.Markdown()

        # Define panels
        with gr.Column(visible=True) as start_panel:
            username = gr.Textbox(label="Your Name")
            topic = gr.Textbox(label="Quiz Topic", value="Python")
            generate_btn = gr.Button("Generate Quiz")

        with gr.Column(visible=False) as quiz_panel:
            question_display = gr.Markdown()
            answer = gr.Radio(label="Choose your answer", choices=[], value=None)
            with gr.Row():
                submit_btn = gr.Button("Submit Answer")
                complete_btn = gr.Button("Complete Quiz")

        with gr.Column(visible=False) as results_panel:
            results_display = gr.Markdown()
            leaderboard_display = gr.DataFrame()
            restart_btn = gr.Button("Restart Quiz")

        # Update interface based on state
        def update_interface(state):
            if state["step"] == "start":
                return (
                    gr.update(visible=True),  # start_panel
                    gr.update(visible=False),  # quiz_panel
                    gr.update(visible=False),  # results_panel
                    gr.update(value=""),  # question_display
                    gr.update(choices=[], value=None),  # answer
                    gr.update(value=state["message"]),  # output_message
                    gr.update(value=""),  # results_display
                    gr.update(value=None)  # leaderboard_display
                )
            elif state["step"] == "quiz" and state["current_question"] < len(state["quiz"]):
                quiz = state["quiz"]
                current = state["current_question"]
                q = quiz[current]
                question_text = f"**Q{current+1} of {len(quiz)}: {q['question']}**"
                # Create display labels like "A: 5" and map to option keys
                option_labels = [f"{key}: {value}" for key, value in q["options"].items()]
                # Store mapping of display labels to option keys (A, B, C, D)
                state["option_values"] = {f"{key}: {value}": key for key, value in q["options"].items()}
                return (
                    gr.update(visible=False),  # start_panel
                    gr.update(visible=True),  # quiz_panel
                    gr.update(visible=False),  # results_panel
                    gr.update(value=question_text),  # question_display
                    gr.update(choices=option_labels, value=None),  # answer
                    gr.update(value=state["message"]),  # output_message
                    gr.update(value=""),  # results_display
                    gr.update(value=None)  # leaderboard_display
                )
            else:  # results
                quiz = state["quiz"]
                score = state["score"]
                total = len(quiz)
                correct_questions = []
                incorrect_questions = []
                
                for i, q in enumerate(quiz):
                    user_answer = state["user_answers"][i]
                    correct_answer = q["correct_answer"].upper()
                    if user_answer and user_answer == correct_answer:
                        correct_questions.append({
                            "question": q["question"],
                            "user_answer": user_answer,
                            "correct_answer": correct_answer,
                            "explanation": q["explanation"]
                        })
                    else:
                        incorrect_questions.append({
                            "question": q["question"],
                            "user_answer": user_answer if user_answer else "Not answered",
                            "correct_answer": correct_answer,
                            "explanation": q["explanation"]
                        })
                
                correct_text = "\n".join([
                    f"Question: {q['question']}\nYour answer: {q['user_answer']}\nCorrect answer: {q['correct_answer']}\nExplanation: {q['explanation']}\n"
                    for q in correct_questions
                ])
                incorrect_text = "\n".join([
                    f"Question: {q['question']}\nYour answer: {q['user_answer']}\nCorrect answer: {q['correct_answer']}\nExplanation: {q['explanation']}\n"
                    for q in incorrect_questions
                ])
                
                feedback = generate_feedback(score, total, correct_text, incorrect_text)
                save_result(state["username"], score, total)
                
                results_text = f"## 🎉 Quiz Complete!\n**Final Score: {score}/{total} ({(score/total)*100:.1f}%)**\n\n### Feedback\n{feedback}"
                if correct_questions:
                    results_text += "\n\n### Correct Answers\n" + "\n".join([
                        f"- **Question**: {q['question']}\n  - **Your Answer**: {q['user_answer']} (Correct)\n  - **Explanation**: {q['explanation']}"
                        for q in correct_questions
                    ])
                if incorrect_questions:
                    results_text += "\n\n### Incorrect Answers\n" + "\n".join([
                        f"- **Question**: {q['question']}\n  - **Your Answer**: {q['user_answer']}\n  - **Correct Answer**: {q['correct_answer']}\n  - **Explanation**: {q['explanation']}"
                        for q in incorrect_questions
                    ])
                
                leaderboard = load_leaderboard()
                leaderboard_output = leaderboard if not leaderboard.empty else "No quiz attempts yet."
                
                return (
                    gr.update(visible=False),  # start_panel
                    gr.update(visible=False),  # quiz_panel
                    gr.update(visible=True),  # results_panel
                    gr.update(value=""),  # question_display
                    gr.update(choices=[], value=None),  # answer
                    gr.update(value=state["message"]),  # output_message
                    gr.update(value=results_text),  # results_display
                    gr.update(value=leaderboard_output)  # leaderboard_display
                )

        # Button actions
        def start_quiz(username, topic, state):
            new_state = state.copy()
            if not username:
                new_state["message"] = "Please enter your name."
                return (new_state, *update_interface(new_state))
            new_state["username"] = username
            new_state["topic"] = topic
            quiz = generate_quiz(topic)
            if quiz is None:
                new_state["message"] = "Failed to generate quiz. Please try again."
                return (new_state, *update_interface(new_state))
            new_state["quiz"] = quiz
            new_state["step"] = "quiz"
            new_state["current_question"] = 0
            new_state["score"] = 0
            new_state["user_answers"] = [None] * len(quiz)
            new_state["message"] = ""
            new_state["option_values"] = {}
            return (new_state, *update_interface(new_state))

        def submit_answer(answer, state):
            new_state = state.copy()
            if not answer:
                new_state["message"] = "Please select an answer."
                return (new_state, *update_interface(new_state))
            quiz = new_state["quiz"]
            current = new_state["current_question"]
            # Map the selected label (e.g., "A: 5") back to the option key (e.g., "A")
            selected_option = new_state["option_values"].get(answer)
            if not selected_option:
                new_state["message"] = "Invalid selection. Please try again."
                return (new_state, *update_interface(new_state))
            new_state["user_answers"][current] = selected_option.upper()
            correct_answer = quiz[current]["correct_answer"].upper()
            logger.debug(f"Q{current+1}: User answer = {selected_option}, Correct answer = {correct_answer}")
            if selected_option.upper() == correct_answer:
                new_state["score"] += 1
            new_state["current_question"] += 1
            new_state["message"] = ""
            new_state["option_values"] = {}
            return (new_state, *update_interface(new_state))

        def complete_quiz(state):
            new_state = state.copy()
            new_state["step"] = "results"
            new_state["message"] = ""
            new_state["option_values"] = {}
            return (new_state, *update_interface(new_state))

        def restart(state):
            new_state = {
                "step": "start",
                "quiz": None,
                "current_question": 0,
                "score": 0,
                "user_answers": [],
                "username": "",
                "topic": "",
                "message": "",
                "option_values": {}
            }
            return (new_state, *update_interface(new_state))

        # Bind button actions
        generate_btn.click(
            fn=start_quiz,
            inputs=[username, topic, state_component],
            outputs=[
                state_component,
                start_panel,
                quiz_panel,
                results_panel,
                question_display,
                answer,
                output_message,
                results_display,
                leaderboard_display
            ]
        )

        submit_btn.click(
            fn=submit_answer,
            inputs=[answer, state_component],
            outputs=[
                state_component,
                start_panel,
                quiz_panel,
                results_panel,
                question_display,
                answer,
                output_message,
                results_display,
                leaderboard_display
            ]
        )

        complete_btn.click(
            fn=complete_quiz,
            inputs=[state_component],
            outputs=[
                state_component,
                start_panel,
                quiz_panel,
                results_panel,
                question_display,
                answer,
                output_message,
                results_display,
                leaderboard_display
            ]
        )

        restart_btn.click(
            fn=restart,
            inputs=[state_component],
            outputs=[
                state_component,
                start_panel,
                quiz_panel,
                results_panel,
                question_display,
                answer,
                output_message,
                results_display,
                leaderboard_display
            ]
        )

    return demo

if __name__ == "__main__":
    logger.info("Starting Gradio application...")
    main().launch()