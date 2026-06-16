# Munters Production Planning Dashboard

This repository contains the prototype and production planning dashboard for Munters. It leverages machine learning to predict task completion times and dynamically schedules work across various machines to optimize production efficiency.

## Features
- **Machine Learning Integration**: Uses models like XGBoost, RandomForest, and GradientBoosting for time predictions.
- **Dynamic Scheduling**: Redistributes workloads automatically based on predicted durations and availability.
- **Interactive Dashboard**: A modern web interface for managing and tracking production statuses.
- **Task Management**: Mark tasks as done, monitor progress in real-time via Gantt charts, and download specific class-level reports.

## Project Structure
- `app.py`: Main Flask application entry point.
- `ml_engine.py` / `classifier.py`: Core machine learning scripts for training models and predicting times.
- `scheduler.py`: Logic for workload distribution and schedule optimization.
- `database.py` / `data_loader.py`: Handles database connections, queries, and initial data population.
- `config.py`: Configuration details and environment settings.
- `static/` and `templates/`: Frontend assets (CSS, JS) and HTML templates.

## Setting Up
1. Ensure you have Python installed.
2. Install the required dependencies (ensure you have a `requirements.txt` or install Flask, Pandas, Scikit-learn, etc.).
3. Run the application:
   ```bash
   python app.py
   ```

## GitHub Update Instructions

To push your latest changes to GitHub from the terminal, follow these steps:

1. **Check the status** of your files (to see what was modified):
   ```bash
   git status
   ```

2. **Add the changed files** to the staging area. To add everything:
   ```bash
   git add .
   ```

3. **Commit the changes** with a descriptive message:
   ```bash
   git commit -m "Your descriptive commit message here"
   ```

4. **Push the changes** to your GitHub repository:
   ```bash
   git push origin main
   ```
   *(If your branch is named `master` instead of `main`, use `git push origin master`)*

---

*Note: Large generated files like database backups (`.db`) and model weights (`.pkl`) are ignored by default via `.gitignore` to keep the repository clean and performant.*
