import time
import random
from lenz_flashtool.utils.progress import percent_complete


def mock_process_with_progress():
    """Demonstrates progress bar with different colors and random delays"""
    tasks = [
        {"name": "Loading data", "steps": 100, "color": "cyan"},
        {"name": "Processing", "steps": 50, "color": "blue"},
        {"name": "Validating", "steps": 80, "color": "yellow"},
        {"name": "Saving results", "steps": 30, "color": "green"},
        {"name": "Cleaning up", "steps": 20, "color": "magenta"}
    ]

    for task in tasks:
        print(f"\nStarting: {task['name']}")
        for i in range(task["steps"] + 1):
            # Random delay between 0.05 and 0.2 seconds
            delay = random.uniform(0.01, 0.05)
            time.sleep(delay)

            percent_complete(
                step=i,
                total_steps=task["steps"],
                title=task["name"],
                color=task["color"]
            )

        # Print completion message in green
        print(f"\n{task['name']} complete!")
        time.sleep(0.5)  # Pause between tasks


if __name__ == "__main__":
    print("=== Mock Process Demonstration ===")
    mock_process_with_progress()
    print("\nAll tasks completed successfully!")
