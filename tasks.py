from models import Task

TASKS = [
    Task("t1", "Which region had the highest total revenue in 2023?", "data/sales.csv", expected_answer="South"),
    Task("t2", "What is the average discount on Technology category orders?", "data/sales.csv", expected_answer="0.0465", tolerance=0.01),
    Task("t3", "In the North region, which product category sold the most units?", "data/sales.csv", expected_answer="Technology"),
    Task("t4", "What was total revenue from Corporate segment customers in 2022?", "data/sales.csv", expected_answer="100154.81", tolerance=1.0),
    Task("t5", "Which product generated the most total revenue overall?", "data/sales.csv", expected_answer="Monitor"),
    Task(
        "t6",
        "Comparing 2022 to 2023, which region had the largest increase in total revenue?",
        "data/sales.csv",
        expected_answer="North",
    ),
    Task(
        "t7",
        "What is the difference in total revenue between the best-selling product and the "
        "second best-selling product, ranked by total revenue?",
        "data/sales.csv",
        expected_answer="15431.35",
        tolerance=1.0,
    ),
    Task(
        "t8",
        "By what percent did total revenue change from 2022 to 2023? Answer as a "
        "percentage number, e.g. 5.0 for a 5% increase.",
        "data/sales.csv",
        expected_answer="3.26",
        tolerance=0.1,
    ),
]