from apscheduler.schedulers.blocking import BlockingScheduler
from Norra import fetch_predictions

def schedule_predictions():
    # Create an instance of the scheduler
    scheduler = BlockingScheduler()

    # Add scheduling logic for predictions
    # Example: Run predictions every day at 7 AM
    scheduler.add_job(fetch_predictions, 'cron', hour=7)

    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()

if __name__ == "__main__":
    # Run the prediction scheduler
    schedule_predictions()