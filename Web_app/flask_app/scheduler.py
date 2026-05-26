import threading
import time
import datetime
from requests.exceptions import RequestException
from flask import current_app
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))

# get path to scan_parse.py
sys.path.insert(0, current_dir)
from utility import run_scan

# scheduling class that creates a thread to handle scheduling
class Scheduler:

    # initalizes schedule class
    def __init__(self, app, db):
        self.thread_started = False
        self.stop = threading.Event()
        # used to signal a db change in schedules
        self.scheduling_change = threading.Event()
        self.db = db
        self.app = app
        
    # thread that manages schedules
    def create_scheduler(self):
        with self.app.app_context():
            while not self.stop.is_set():
                # scheduler currently using UTC/GMT time conversions will be done on frontend
                curr_time = datetime.datetime.now(datetime.timezone.utc)
                next_scheduler_run_query = "SELECT * FROM schedules WHERE next_run <= %s"
                schedules_to_run = self.db.query(next_scheduler_run_query, [curr_time])
                if schedules_to_run:
                    for schedule in schedules_to_run:
                        schedule_id = schedule['schedule_id']
                        website_id = schedule['website_id']
                        scan_url = schedule['scan_url']
                        try:
                            # calls the run_scan when the time is correct
                            response = run_scan("scheduled", scan_url, website_id, self.db, 14)
                            print(f"Scan triggered successfully (schedule_id: {schedule_id})")
                        except RequestException as e:
                            print(e)
                        self.generate_next_time(schedule_id)
                # checks every 60 seconds or when a scheduling changes occurs to update the times in the scheduler
                self.scheduling_change.wait(15)

    # creates thread
    def start_scheduler(self):
        if not self.thread_started:
            # creates thread running_create_scheduler
            schedule_thread = threading.Thread(target=self.create_scheduler)
            # ensures that scheduler is destroyed
            schedule_thread.daemon = True
            schedule_thread.start()
            self.thread_started = True

    # stops the scheduling thread
    def stop_scheduler(self):
        self.stop.set()

    # adds hourly scan to db
    def add_hourly_scan(self, frequency, days_of_week, run_times, description, website_id, scan_url):
        # adds schedule to scheduling table
        scan_insertion_query = "INSERT INTO schedules (website_id, scan_url, description, time_interval) values (%s, %s, %s, %s)"
        schedule_id = self.db.query(scan_insertion_query, [website_id, scan_url, description, "hourly"])[0]['LAST_INSERT_ID()']
        
        # adds hourly frequency into frequency table
        hourly_frequency_insertion_query = "INSERT INTO hourly_frequency (schedule_id, hourly_frequency) values (%s, %s)"
        self.db.query(hourly_frequency_insertion_query, [schedule_id, int(frequency)])

         # add schedule information to child tables
        self.add_run_times(run_times, schedule_id)
        self.add_days_of_week(days_of_week, schedule_id)
        
        # sets the next time so scheduler knows when to run
        self.generate_next_time(schedule_id)
        # signals change to the scheduling thread
        self.scheduling_change.set()
        self.scheduling_change.clear()

    # adds daily or weekly scans to db
    def add_daily_or_weekly_scan(self, days_of_week, specific_time, description, website_id, scan_url, time_interval):
        scan_insertion_query = "INSERT INTO schedules (website_id, scan_url, description, time_interval) values (%s, %s, %s, %s)"
        schedule_id = self.db.query(scan_insertion_query, [website_id, scan_url, description, time_interval])[0]['LAST_INSERT_ID()']

        self.add_run_times([specific_time], schedule_id)
        self.add_days_of_week(days_of_week, schedule_id)

        self.generate_next_time(schedule_id)
        
        self.scheduling_change.set()
        self.scheduling_change.clear()

    def add_monthly_scan(self, specific_time, date_selected, description, website_id, scan_url):
        scan_insertion_query = "INSERT INTO schedules (website_id, scan_url, description, time_interval) values (%s, %s, %s, %s)"
        schedule_id = self.db.query(scan_insertion_query, [website_id, scan_url, description, "monthly"])[0]['LAST_INSERT_ID()']

        # add date for monthly scan into db
        monthly_date_insertion_query = "INSERT INTO monthly_date (schedule_id, day_of_month) values (%s, %s)"
        self.db.query(monthly_date_insertion_query, [schedule_id, int(date_selected)])

        self.add_run_times([specific_time], schedule_id)

        self.generate_next_time(schedule_id)
        
        self.scheduling_change.set()
        self.scheduling_change.clear()

    def add_run_times(self, run_times, schedule_id):
        #days of week and run times in seperate tables remove website url not good practice but I am going to store url in here for now
        for time_str in run_times:
            # takes time string from db and turns it into datetime 
            time = datetime.datetime.strptime(time_str, "%H:%M").time()
            time_insertion_query = "INSERT INTO scan_times (scan_time, schedule_id) values (%s, %s)"
            self.db.query(time_insertion_query, [time, schedule_id])
        return

    def add_days_of_week(self, days_of_week, schedule_id):
        for day in days_of_week:
            valid_day_insertion_query = "INSERT INTO valid_days (day, schedule_id) values (%s, %s)"
            self.db.query(valid_day_insertion_query, [day, schedule_id])
        return

    # getter for the schedules for a specific website
    def get_website_schedules(self, website_id):
        website_schedules_query = "SELECT * FROM schedules WHERE website_id = %s"
        website_schedules = self.db.query(website_schedules_query, [website_id])
        return website_schedules

    # helper function to get the time interval for a schedule
    def get_schedule_interval(self, schedule_id):
        time_interval_query = "SELECT time_interval FROM schedules WHERE schedule_id = %s"
        time_interval_result = self.db.query(time_interval_query, [schedule_id])
        time_interval = time_interval_result[0]["time_interval"]
        return time_interval

    # getter for individual schedules
    def get_schedule_data(self, schedule_id):
        schedule_data_query = "SELECT * FROM schedules WHERE schedule_id = %s"
        schedule_data = self.db.query(schedule_data_query, [schedule_id])
        return schedule_data 

    def get_scan_times(self, schedule_id):
        scan_time_query = "SELECT * FROM scan_times where schedule_id = %s"
        scan_times = self.db.query(scan_time_query, [schedule_id])
        return scan_times
    
    # deletes schedules from db by schedule_id
    def delete_schedule(self, schedule_id):
        # delete from dbs that use schedule_id as FK first
        time_interval = self.get_schedule_interval(schedule_id)
        if time_interval == "hourly":
            delete_hourly_frequency_query = "DELETE FROM hourly_frequency WHERE schedule_id = %s"
            self.db.query(delete_hourly_frequency_query, [schedule_id])
        if time_interval == "monthly":
            delete_monthly_date_query = "DELETE FROM monthly_date WHERE schedule_id = %s"
            self.db.query(delete_monthly_date_query, [schedule_id])
        delete_query_valid_days = "DELETE FROM valid_days WHERE schedule_id = %s"
        self.db.query(delete_query_valid_days, [schedule_id])
        delete_query_scan_times_query = "DELETE FROM scan_times WHERE schedule_id = %s"
        self.db.query(delete_query_scan_times_query, [schedule_id])
        delete_query_schedules = "DELETE FROM schedules WHERE schedule_id = %s"
        self.db.query(delete_query_schedules, [schedule_id])
        self.scheduling_change.set()
        self.scheduling_change.clear()
        return "Success"
    
    # generates the next run time for the schedule
    def generate_next_time(self, schedule_id):

        next_run = None
        time_interval = self.get_schedule_interval(schedule_id)   
        run_times = []

        if time_interval == "monthly":
            next_run = self.generate_next_time_monthly(schedule_id)
    
        if next_run == None:
            scan_times = self.get_scan_times(schedule_id)
            for time_str in scan_times:
                # takes total seconds and gets hours, mins, second then creates time object
                total_time_seconds = int(time_str['scan_time'].total_seconds())
                hours = total_time_seconds // 3600
                minutes = (total_time_seconds % 3600) // 60
                seconds = total_time_seconds % 60 
                run_times.append(datetime.time(hour=hours, minute=minutes, second=seconds))

            valid_days_query = "SELECT * FROM valid_days where schedule_id = %s"
            valid_days_list = self.db.query(valid_days_query, [schedule_id])
            days_valid_list = []

            for record in valid_days_list:
                days_valid_list.append(record["day"])

            # gets the day, date, and time to use for generating next run
            current_date = datetime.datetime.now(datetime.timezone.utc)
            current_time = current_date.time()
            current_day = current_date.strftime("%A")
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
            # checks run time to see if there are any times valid in the current day
            for time in run_times:
                if time > current_time and current_day in days_valid_list:
                    next_run = (datetime.datetime.combine(current_date.date(), time))
                    break
        
        # checks if next_run has been set yet
        if next_run == None:
            # attempts to get the current day from the index
            try:
                start_day = days.index(current_day)
            except:
                start_day = 0

            # iterates through each day beginning at the start day to get to first valid day
            for i in range(1, len(days) + 1):
                curr_day_index = (start_day + i) % len(days)
                curr_day_name = days[curr_day_index]
                # checks if the day being indexed is valid
                if curr_day_name in days_valid_list:
                    # checks how many days ahead the valid time is to use as the timedelta on datetime to create a datetime object with delta days in the future
                    days_ahead = (curr_day_index - start_day) % len(days)
                    # combines the date together and uses the timezone of utc for consistency of data
                    attempted_next_run = datetime.datetime.combine(current_date.date() + datetime.timedelta(days=days_ahead), run_times[0], tzinfo=datetime.timezone.utc)
                    # for edge case that scheduling happens on same day in a week but the times that were valid have already been exhausted
                    if attempted_next_run >= current_date:
                        next_run = attempted_next_run
                    else:
                        next_run = datetime.datetime.combine(current_date.date() + datetime.timedelta(days=days_ahead + 7), run_times[0], tzinfo=datetime.timezone.utc)
                    break
        
        # checks if next_run is set and puts it into db
        if next_run:
            update_run_query = "UPDATE schedules SET next_run = %s WHERE schedule_id = %s"
            self.db.query(update_run_query, [next_run, schedule_id])
            return "Success"
        else:
            return "Failed"
    
    def generate_next_time_monthly(self, schedule_id):
        # lengths of months ignoring leap years so date that doesnt exist isn't scheduled
        month_lengths = {
        1: "31", 2: "28", 3: "31", 4: "30",
        5: "31", 6: "30", 7: "31", 8: "31", 
        9: "30", 10: "31", 11: "30", 12: "31"
        }
        next_run = None
        scan_times_result = self.get_scan_times(schedule_id)
        total_time_seconds = int(scan_times_result[0]['scan_time'].total_seconds())
        hours = total_time_seconds // 3600
        minutes = (total_time_seconds % 3600) // 60
        seconds = total_time_seconds % 60 
        scan_times = (datetime.time(hour=hours, minute=minutes, second=seconds))
        monthly_date_query = "SELECT * FROM monthly_date WHERE schedule_id = %s"
        monthly_date = self.db.query(monthly_date_query, [schedule_id])
        monthly_date_int = int(monthly_date[0]["day_of_month"])
        current_date = datetime.datetime.now(datetime.timezone.utc)
        current_month = current_date.month
        current_year = current_date.year
        # runs twice to check the first month then assigns to next month if the time has past in the current
        for _ in range(2):
            # checks to see if the day of month trying to be run is valid
            last_day = int(month_lengths[current_month])
            if last_day < monthly_date_int:
                monthly_date_int = last_day
            attempted_date = datetime.datetime(current_year, current_month, monthly_date_int, 
                                               scan_times.hour, scan_times.minute, scan_times.second, tzinfo=datetime.timezone.utc)
            # checks that the scan for this month hasn't been generated. Useful for first time schedule
            if attempted_date >= current_date:
                return attempted_date
            
            # goes up one more month and checks if it is valid
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
        return None

