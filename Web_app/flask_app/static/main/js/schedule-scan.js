const scanTimeIntervalButtons = Array.from(document.getElementsByClassName('nav-button'));
const frequencyButtonsContainer = document.getElementById('frequency-buttons');
const frequencyButtons = frequencyButtonsContainer.querySelectorAll('.form-button');
const hourlyFrequencyButton = document.getElementById('one-hour');
const deleteButton = document.getElementById('delete-button');
const descriptionBoxScheduler = document.getElementById('schedule-desc');
let selectedTimeIntervalButton = document.getElementById('hourly');
let clickedHourlyIntervalButton = hourlyFrequencyButton;
const selectedDateDropdown = document.getElementById('date-selector-dropdown');
const frequencyElements = document.getElementsByClassName('frequency');
const specificTImeElements = document.getElementsByClassName('specific-time');
const timeRangeElements = document.getElementsByClassName('time-range');
const dateSelectorElements = document.getElementsByClassName('date-selector');
const daysToRunElements = document.getElementsByClassName('days-to-run');
let selectedDate = '1';

let website_data = $('#website_data').data();
scanTimeIntervalButtons.forEach(button => {
    button.addEventListener('click', function(event) {
        if (selectedTimeIntervalButton !== button){
            selectedTimeIntervalButton.style.color = '#FFFFFF';
        }
        selectedTimeIntervalButton = button;
        const displayFrequency = ['hourly'];
        const displayTimeRange = ['hourly'];
        const displaySpecificTime = ['daily', 'weekly', 'monthly'];
        const displayDateSelection = ['monthly'];
        const displayDaysToRun = ['hourly', 'daily', 'weekly'];
        daysToRunElements[0].style.display = displayDaysToRun.includes(selectedTimeIntervalButton.id) ? 'block' : 'none';
        daysToRunElements[1].style.display = displayDaysToRun.includes(selectedTimeIntervalButton.id) ? 'flex' : 'none';
        frequencyElements[0].style.display = displayFrequency.includes(selectedTimeIntervalButton.id) ? 'block' : 'none';
        frequencyElements[1].style.display = displayFrequency.includes(selectedTimeIntervalButton.id) ? 'flex' : 'none';
        for (let timeRangeElementCount = 0; timeRangeElementCount < timeRangeElements.length; timeRangeElementCount++){
            timeRangeElements[timeRangeElementCount].style.display = displayTimeRange.includes(selectedTimeIntervalButton.id) ? 'block' : 'none';
        }
        for (let specificTImeElementCount = 0; specificTImeElementCount < specificTImeElements.length; specificTImeElementCount++){
            specificTImeElements[specificTImeElementCount].style.display = displaySpecificTime.includes(selectedTimeIntervalButton.id) ? 'block' : 'none';
        }
        for (let dateSelectionElementCount = 0; dateSelectionElementCount < dateSelectorElements.length; dateSelectionElementCount++){
            dateSelectorElements[dateSelectionElementCount].style.display = displayDateSelection.includes(selectedTimeIntervalButton.id) ? 'block' : 'none';
        }    
        selectedTimeIntervalButton.style.color = 'rgb(101, 197, 197)';
    });
});

frequencyButtons.forEach(button => {
    button.addEventListener('click', function(event) {
        if (clickedHourlyIntervalButton !== null){
            clickedHourlyIntervalButton.style.color = '#FFFFFF';
            }
        clickedHourlyIntervalButton = button;
        clickedHourlyIntervalButton.style.color = 'rgb(101, 197, 197)';
    });
});


const slectedButtonsContainer = document.getElementById('day-buttons');
const slectedButtons = slectedButtonsContainer.querySelectorAll('.form-button');
const daysSelected = [];
slectedButtons.forEach(button => {
    button.addEventListener('click', function(event) {
        let isSelected = daysSelected.indexOf(button.id);
        if (isSelected == -1 ){
            daysSelected.push(button.id);
            button.style.color = 'rgb(101, 197, 197)';
        } else {
            daysSelected.splice(isSelected, 1);
            button.style.color = '#FFFFFF';
        }
    });
});

selectedDateDropdown.addEventListener('change', function(event) {
    selectedDate = this.value;
}  )

const startTimeContainer = document.getElementById('start-time');
const endTimeContainer = document.getElementById('end-time');
const specificTImeContainer = document.getElementById('specific-time');
const hourScheduleButton = document.getElementById('hour-button');

// input validation for time that is HH:MM 24 hour time
function checkRangeValidity(times) {
    let startHour = null;
    let startMinute = null;
    for (let i = 0; i < times.length; i++) {
        if ((times[i].length == 0))
            {
                alert("Enter a time");
                return -1;
            }
        
            if ((times[i].length !== 5) || (times[i][2] !== ":")) {
                alert("Improper time format");
                return -1;
            }
        
            try {
                hoursString = times[i].slice(0,2);
                minutesString = times[i].slice(3,5);
                hours = parseInt(hoursString);
                minutes = parseInt(minutesString);
            } catch (error) {
                alert("Time must be integers greater than 0");
                return -1;
            }
            console.log(hours, minutes);

            if ((hours < 0) || (hours > 23)){
                alert("Pick an hour between 0-23");
                return -1;
            }
        
            if ((minutes < 0) || (minutes > 59)){
                alert("Pick a minute between 0-59");
                return -1;
            }
            console.log(hours, minutes);
            console.log(startHour, startMinute);
            if ((startHour == null) && (startMinute == null)) {
                startHour = hours;
                startMinute = minutes;
            } 
            
            if ((startHour > hours) || (startHour === hours) && startMinute > minutes) {
                alert("Start occurs after end");
                return -1;
            }
    };
    return times;
}

// Checks the time validity for a signe string
function checkSingleTimeValidity(time){
    if ((time.length == 0)) {
        alert("Enter a time");
        return -1;
    }
    
    if ((time.length !== 5) || (time[2] !== ":")) {
        alert("Improper time format");
        return -1;
        }
    try {
        hoursString = time.slice(0,2);
        minutesString = time.slice(3,5);
        hours = parseInt(hoursString);
        minutes = parseInt(minutesString);
    } catch (error) {
        alert("Time must be integers greater than 0");
        return -1;
    }
    if ((hours < 0) || (hours > 23)) {
        alert("Pick an hour between 0-23");
        return -1;
    }

    if ((minutes < 0) || (minutes > 59)) {
        alert("Pick a minute between 0-59");
        return -1;
    }
    return time;
}

// Generates json body to post to backend
function generateBody(frequency=null, days_to_run=null, start_time=null, end_time=null, specific_time=null, date_selected=null) {
    const timeInterval = selectedTimeIntervalButton.id;
    body = {};
    body["time_interval"] = timeInterval;
    body["description"] = descriptionBoxScheduler.value;
    body["website_id"] = website_data.id;
    body["website_url"] = website_data.url;
    // Checks if the value is set to append it to body
    frequency !== null ? body["frequency"] = frequency: null;
    days_to_run !== null ? body["days_to_run"] = days_to_run: null;
    start_time !== null ? body["start_time"] = start_time: null;
    end_time !== null ? body["end_time"] = end_time: null;
    specific_time !== null ? body["specific_time"] = specific_time: null;
    date_selected !== null ? body["date_selected"] = date_selected: null;
    return JSON.stringify(body);
}

document.getElementById("submit-button").addEventListener("click", function(event) {
    event.preventDefault();
    const timeInterval = selectedTimeIntervalButton.id;
    let body = null;

    if (descriptionBoxScheduler.value === "") {
        alert("Enter a description")
        return;
    }
    // Checks time interval for the schedule type
    if (timeInterval === 'hourly') {
        const hourly_frequency = clickedHourlyIntervalButton.value;

        const daysToRun = daysSelected;
        if (daysToRun.length === 0){
            alert("Select at least one day to run scan");
            return;
        }

        startTime = startTimeContainer.value;
        endTime = endTimeContainer.value;
        times = checkRangeValidity([startTime, endTime]);
        if (times === -1){
            console.log("Improper time inputs");
            return;
        }

        body = generateBody(hourly_frequency, daysToRun, startTime, endTime, null, null);
    }

    if ((timeInterval === 'daily') || (timeInterval === 'weekly')) {
        const daysToRun = daysSelected;
        if (daysToRun.length === 0){
            alert("Select at least one day to run scan");
            return;
        }

        if ((daysToRun.length > 1) && (timeInterval === 'weekly')){
            alert("Select only one day for a weekly scan");
            return;
        } 

        specificTime = specificTImeContainer.value;
        time = checkSingleTimeValidity(specificTime);
        if (time === -1){
            console.log("Improper time input");
            return;
        }

        body = generateBody(null, daysToRun, null, null, specificTime, null);
    }

    if (timeInterval === 'monthly') {
        specificTime = specificTImeContainer.value;
        time = checkSingleTimeValidity(specificTime);
        if (time === -1){
            console.log("Improper time input");
            return;
        }
        body = generateBody(null, null, null, null, specificTime, selectedDate);

    } 

    console.log(body);

    fetch("/scheduleScan", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: body
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => { throw new Error(text); });
        }
        return response.json();
    })
    .then(result => {
        location.reload(true);
    })
    .catch(error => {
        // I know this is not great, but it works for now
        if (error['error'] === 'Scan canceled')
        {
            //pass
        }
        else
        {
            alert("Error scheduling");
        }
    });
});

function loadSchedule() {
    fetch(`/api/websites/schedules?website_id=${website_data.id}`)
        .then(response => response.json())
        .then(schedules => {
            schedules.forEach(schedule => {
                    
                const dashboard = document.querySelector('.dashboard');
                const newRow = document.createElement('div');
                newRow.className = 'dashboard_row';
                

                const intervalBox = document.createElement('div');
                intervalBox.className = 'dashboard_box time_interval';
                intervalBox.textContent = schedule.time_interval;
                newRow.appendChild(intervalBox);

                const nextRunBox = document.createElement('div');
                nextRunBox.className = 'dashboard_box next_run';
                nextRunBox.textContent = schedule.next_run;
                newRow.appendChild(nextRunBox);

                const descriptionBox = document.createElement('div');
                descriptionBox.className = 'dashboard_box description';
                descriptionBox.textContent = schedule.description;
                newRow.appendChild(descriptionBox);

                const deleteBox = document.createElement('div');
                deleteBox.className = 'dashboard_box delete_box';
                // creates delete button with metadata of schedule id
                const deleteButton = document.createElement('button');
                deleteButton.dataset.schedule_id = schedule.schedule_id;
                deleteButton.textContent = "DELETE"
                // deletes schedule in backend
                deleteButton.addEventListener('click', function(event){
                    const schedule_id = event.target.dataset.schedule_id;
                    if (schedule_id) {
                        fetch(`/deleteSchedule?schedule_id=${schedule_id}`)
                        .then(resposne => {
                            if (resposne.ok) {
                                console.log("Deletion succesful");
                                location.reload(true);
                            } else {
                                console.log("Deletion failed");
                            }
                    })
                    } else {
                        console.log("Failed to find schedule_id");
                    }
                });
                deleteBox.appendChild(deleteButton);
                newRow.appendChild(deleteBox);

                dashboard.append(newRow);
            });
        })
        .catch(error => {
            console.error("Error updating schedule data:", error);
        });
}


loadSchedule();