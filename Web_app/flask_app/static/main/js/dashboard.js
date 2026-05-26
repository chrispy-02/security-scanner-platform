document.addEventListener("DOMContentLoaded", function(){
    updateScanData();
    // Update statuses, risk counts, and totals every 5 seconds.
    setInterval(function() {
        if (!filterActive) {
            updateScanData();
        }
    }, 10000);
});

// Scan statuses are refreshed server-side via /api/websites; no client-side
// polling of a CI status endpoint is needed.

function updateScanData() {
    fetch("/api/websites")
        .then(response => response.json())
        .then(scans => {
            let totalHigh = 0;
            let totalMedium = 0;
            let totalLow = 0;
            let totalInfo = 0;
            let totalScans = scans.length;
            let successful = 0;
            let running = 0;
            let failed = 0;

            scans.forEach(scan => {
                const row = document.querySelector(`.dashboard_row[data-website_id="${scan.website_id}"]`);

                if (row) { // if a row already exist set its values
                    const urlBox = row.querySelector('.dashboard_box:nth-child(2)');
                    const dateBox = row.querySelector('.dashboard_box:nth-child(3)');
                    const statusBox = row.querySelector('.dashboard_box:nth-child(4)');
                    const highBox = row.querySelector('.dashboard_box:nth-child(5)');
                    const mediumBox = row.querySelector('.dashboard_box:nth-child(6)');
                    const lowBox = row.querySelector('.dashboard_box:nth-child(7)');
                    const infoBox = row.querySelector('.dashboard_box:nth-child(8)');

                    urlBox.textContent = scan.website_url;
                    if (scan.scan_date) {
                        dateBox.textContent = scan.scan_date.slice(5, 22);
                    } else {
                        dateBox.textContent = "No scans";
                    }
                    // set boxes to scan values
                    statusBox.textContent = scan.status;
                    highBox.textContent = scan.high_risks;
                    mediumBox.textContent = scan.medium_risks;
                    lowBox.textContent = scan.low_risks;
                    infoBox.textContent = scan.informational_risks;
                } else {
                    // Create new row
                    const dashboard = document.querySelector('.dashboard');
                    const newRow = document.createElement('div');
                    newRow.className = 'dashboard_row';
                    newRow.dataset.website_id = scan.website_id;
                    // name box
                    const nameBox = document.createElement('div');
                    nameBox.className = 'dashboard_box name_box';
                    const a = document.createElement("a");
                    a.href = `/website/${scan.website_id}`;
                    a.textContent = scan.website_name;
                    nameBox.appendChild(a);
                    newRow.appendChild(nameBox);
                    // url box
                    const urlBox = document.createElement('div');
                    urlBox.className = 'dashboard_box url_box';
                    urlBox.textContent = scan.website_url;
                    newRow.appendChild(urlBox);
                    // date box
                    const dateBox = document.createElement('div');
                    dateBox.className = 'dashboard_box date_box';
                    // checks if scans have occured
                    if (scan.scan_date) {
                        dateBox.textContent = scan.scan_date.slice(5, 22);
                    } else {
                        dateBox.textContent = "No scans";
                    }
                    newRow.appendChild(dateBox);
                    // set status box
                    const statusBox = document.createElement('div');
                    statusBox.className = 'dashboard_box status_box';
                    statusBox.textContent = scan.status;
                    newRow.appendChild(statusBox);
                    // set high risk box
                    const highBox = document.createElement('div');
                    highBox.className = 'dashboard_box risk_box';
                    highBox.textContent = scan.high_risks;
                    newRow.appendChild(highBox);
                    // set medium risk box
                    const mediumBox = document.createElement('div');
                    mediumBox.className = 'dashboard_box risk_box';
                    mediumBox.textContent = scan.medium_risks;
                    newRow.appendChild(mediumBox);
                    // set low risk box
                    const lowBox = document.createElement('div');
                    lowBox.className = 'dashboard_box risk_box';
                    lowBox.textContent = scan.low_risks;
                    newRow.appendChild(lowBox);
                    // set info risk box
                    const infoBox = document.createElement('div');
                    infoBox.className = 'dashboard_box risk_box';
                    infoBox.textContent = scan.informational_risks;
                    newRow.appendChild(infoBox);
                    // create box for buttons
                    const actionsBox = document.createElement('div');
                    actionsBox.className = 'dashboard_box dashboard_box_right report_box';
                    // checks if the scan was a success before adding the button
                    if (scan.status === "success" || scan.status === "Success" || scan.status === "Completed") {
                        const viewButton = document.createElement("button");
                        viewButton.textContent = "View Latest Report";
                        viewButton.addEventListener("click", function() {
                            window.location.href = `/report/${scan.scan_id}`; // adds routing information to link to newest scan
                        });
                        actionsBox.appendChild(viewButton);
                    }
                    newRow.appendChild(actionsBox);

                    dashboard.append(newRow);
                }

                // counts each risk
                totalHigh += parseInt(scan.high_risks) || 0;
                totalMedium += parseInt(scan.medium_risks) || 0;
                totalLow += parseInt(scan.low_risks) || 0;
                totalInfo += parseInt(scan.informational_risks) || 0;
                // counts number of scans in each state
                let status = scan.status.toLowerCase();
                if (status === "success" || status === "completed") {
                    successful++;
                } else if (status === "running" || status === "in progress") {
                    running++;
                } else if (status === "failed") {
                    failed++;
                }
            });

            // Update summary stats
            document.getElementById("totalHigh").textContent = totalHigh;
            document.getElementById("totalMedium").textContent = totalMedium;
            document.getElementById("totalLow").textContent = totalLow;
            document.getElementById("totalInfo").textContent = totalInfo;
            document.getElementById("totalScans").textContent = totalScans;
            document.getElementById("successfulScans").textContent = "Successful: " + successful;
            document.getElementById("runningScans").textContent = "Running: " + running;
            document.getElementById("failedScans").textContent = "Failed: " + failed;
        })
        .catch(error => {   // catch errors in this place
            console.error("Error updating scan data:", error);
        });
}

// buttons for the filter
const filterMenu = document.querySelector('.filter_options')
const filterBtn = document.querySelector('.filter_button')

let isOpen = false  // boolean to test if filter is open

// opens filter window when button is clicked
filterBtn.addEventListener('click', () => {
    if (isOpen === false) { // do this if menu is closed
        filterMenu.classList.add('open')
        isOpen = true
        document.body.style.overflow = "hidden";
        document.documentElement.style.overflow = "hidden";
        console.log("opened") 

    }
    else { // do this is menu is open
        filterMenu.classList.remove('open')
        isOpen = false
        document.body.style.overflow = "auto";
        document.documentElement.style.overflow = "auto";
    }
    
})

// applys filter settings and closes filter window
document.getElementById('apply_filter').addEventListener('click', () => {
    // closes filter window
    filterMenu.classList.remove('open')
    isOpen = false
    document.body.style.overflow = "auto";
    document.documentElement.style.overflow = "auto";
    console.log("close");
    // outputs current values
    console.log("Searched: ", document.getElementById("search").value);
    console.log("Start Time: ", document.getElementById("startTime").value);
    console.log("End Time: ", document.getElementById("endTime").value);
    console.log("Status: ", document.getElementById("selectStatus").value);
})



// clear the filter
document.getElementById("clear_filter").addEventListener("click", () => {
    // disable filter
    filterActive = false;
    document.getElementById("filter_form").reset();

    const dashboard = document.querySelector('.dashboard');
    // clear any existing rows
    dashboard.querySelectorAll('.dashboard_row:not(#header)').forEach(row => row.remove());

    // get original data again after clearing
    updateScanData();
});


// applies the filter
document.getElementById('apply_filter').addEventListener('click', () => {
    filterMenu.classList.remove('open');
    isOpen = false;
    filterActive = true;

    document.body.style.overflow = "auto";
    document.documentElement.style.overflow = "auto";

    const query = document.getElementById('search').value;
    const startTime = document.getElementById('startTime').value;
    const endTime = document.getElementById('endTime').value;
    const status = document.getElementById('selectStatus').value;
    const showHigh = document.getElementById('showHigh').checked;
    const showMedium = document.getElementById('showMedium').checked;
    const showLow = document.getElementById('showLow').checked;
    const showInfo = document.getElementById('showInfo').checked;
    // specificc parameters searched for
    const params = new URLSearchParams({
        q: query,
        start_date: startTime,
        end_date: endTime,
        status: status,
        showHigh: showHigh,
        showMedium: showMedium,
        showLow: showLow,
        showInfo: showInfo
    });

    fetch(`/search?${params}`)
        .then(response => response.json())
        .then(data => {
            const dashboard = document.querySelector('.dashboard');
            dashboard.querySelectorAll('.dashboard_row:not(#header)').forEach(row => row.remove());

            // determines selectable risks
            const selectedRisks = [];
            if (showHigh) selectedRisks.push('high_risks');
            if (showMedium) selectedRisks.push('medium_risks');
            if (showLow) selectedRisks.push('low_risks');
            if (showInfo) selectedRisks.push('informational_risks');

            // sorts data based on selected risks with the website with the highest at the top
            if (selectedRisks.length > 0) {
                data.sort((a, b) => {
                    const maxA = Math.max(...selectedRisks.map(risk => parseInt(a[risk]) || 0));
                    const maxB = Math.max(...selectedRisks.map(risk => parseInt(b[risk]) || 0));
                    return maxB - maxA;
                });
            }

            data.forEach(site => {
                let formattedDate = 'No Scans';
                if (site.scan_date) {
                    const date = new Date(site.scan_date);
                    const day = String(date.getDate()).padStart(2, '0');
                    const month = date.toLocaleString('en-GB', { month: 'short' });
                    const year = date.getFullYear();
                    const hours = String(date.getHours()).padStart(2, '0');
                    const minutes = String(date.getMinutes()).padStart(2, '0');
                    formattedDate = `${day} ${month} ${year} ${hours}:${minutes}`;
                }
                // displays the filtered data on the dashboard page
                dashboard.insertAdjacentHTML('beforeend', `
                    <div class="dashboard_row">
                        <div class="dashboard_box name_box">
                            <a href="/website/${site.website_id}">${site.website_name}</a>
                        </div>
                        <div class="dashboard_box url_box">${site.website_url}</div>
                        <div class="dashboard_box date_box">${formattedDate}</div>
                        <div class="dashboard_box status_box">${site.status}</div>
                        <div class="dashboard_box risk_box">${site.high_risks}</div>
                        <div class="dashboard_box risk_box">${site.medium_risks}</div>
                        <div class="dashboard_box risk_box">${site.low_risks}</div>
                        <div class="dashboard_box risk_box">${site.informational_risks}</div>
                        <div class="dashboard_box dashboard_box_right report_box">
                            <button onclick="location.href='/report/${site.website_id}'">View Report</button>
                        </div>
                    </div>
                `);
            });
        })
        .catch(error => console.error("Error fetching filtered data:", error));
});





