document.addEventListener("DOMContentLoaded", function(){
    updateScanData();
    // Update statuses, risk counts, and totals every 5 seconds.
    setInterval(function() {
         updateScanData();
    }, 10000);
});

let website_data = $('#website_data').data();

// function updateStatuses() {
//     fetch("/api/gitlab_status")
//     .then(response => response.json())
//     .then(data => {
//          console.log("Pipeline data received:", data);
//          data.pipelines.forEach(pipeline => {
//              console.log("Pipeline", pipeline.pipeline_id, "status:", pipeline.status);
//              const statusCell = document.getElementById("status_" + pipeline.pipeline_id);
//              if (statusCell) {
//                  let displayStatus = pipeline.status;
//                  if (pipeline.status === "created" || pipeline.status === "pending") {
//                      displayStatus = "Created";
//                  } else if (pipeline.status === "running") {
//                      displayStatus = "In Progress";
//                  } else if (pipeline.status === "success") {
//                      displayStatus = "Completed";
//                  } else if (pipeline.status === "failed") {
//                      displayStatus = "Failed";
//                  }
//                  statusCell.textContent = displayStatus;
//              }
//          });
//     })
//     .catch(error => {
//          console.error("Error updating statuses:", error);
//     });
// }

// update the scan data for the dashboard
function updateScanData() {
    fetch(`/api/websites/scans?website_id=${website_data.id}`)
        .then(response => response.json())
        .then(scans => {
            scans.forEach(scan => {
                const row = document.querySelector(`.dashboard_row[data-scan_id="${scan.scan_id}"]`);

                if (row) { 
                    const urlBox = row.querySelector('.dashboard_box:nth-child(1)');
                    const dateBox = row.querySelector('.dashboard_box:nth-child(2)');
                    const statusBox = row.querySelector('.dashboard_box:nth-child(3)');
                    const highBox = row.querySelector('.dashboard_box:nth-child(4)');
                    const mediumBox = row.querySelector('.dashboard_box:nth-child(5)');
                    const lowBox = row.querySelector('.dashboard_box:nth-child(6)');
                    const infoBox = row.querySelector('.dashboard_box:nth-child(7)');

                    urlBox.textContent = scan.website_url;
                    dateBox.textContent = (scan.scan_date).slice(5,22);
                    statusBox.textContent = scan.status;
                    highBox.textContent = scan.high_risks;
                    mediumBox.textContent = scan.medium_risks;
                    lowBox.textContent = scan.low_risks;
                    infoBox.textContent = scan.informational_risks;

                } else {
                    
                    const dashboard = document.querySelector('.dashboard');
                    const newRow = document.createElement('div');
                    newRow.className = 'dashboard_row';
                    newRow.dataset.scan_id = scan.scan_id;

                    const urlBox = document.createElement('div');
                    urlBox.className = 'dashboard_box url_box';
                    urlBox.textContent = scan.website_url;
                    newRow.appendChild(urlBox);

                    const dateBox = document.createElement('div');
                    dateBox.className = 'dashboard_box date_box';
                    dateBox.textContent = (scan.scan_date).slice(5,22);
                    newRow.appendChild(dateBox);

                    const statusBox = document.createElement('div');
                    statusBox.className = 'dashboard_box status_box';
                    statusBox.textContent = scan.status;
                    newRow.appendChild(statusBox);

                    const highBox = document.createElement('div');
                    highBox.className = 'dashboard_box risk_box';
                    highBox.textContent = scan.high_risks;
                    newRow.appendChild(highBox);

                    const mediumBox = document.createElement('div');
                    mediumBox.className = 'dashboard_box risk_box';
                    mediumBox.textContent = scan.medium_risks;
                    newRow.appendChild(mediumBox);

                    const lowBox = document.createElement('div');
                    lowBox.className = 'dashboard_box risk_box';
                    lowBox.textContent = scan.low_risks;
                    newRow.appendChild(lowBox);

                    const infoBox = document.createElement('div');
                    infoBox.className = 'dashboard_box risk_box';
                    infoBox.textContent = scan.informational_risks;
                    newRow.appendChild(infoBox);

                    // creating the box and the view report button
                    const actionsBox = document.createElement('div');
                    actionsBox.className = 'dashboard_box dashboard_box_right data report_box action_box';
                    if (scan.status === "success" || scan.status === "Success" || scan.status === "Completed") {
                        const viewButton = document.createElement("button");
                        viewButton.textContent = "View Report";
                        viewButton.addEventListener("click", function() {
                            window.location.href = `/report/${scan.scan_id}`;
                        });
                        actionsBox.appendChild(viewButton);
                    }

                    // Download JSON button
                    if (scan.status === "success" || scan.status === "Success" || scan.status === "Completed") {
                        const downloadButton = document.createElement("button");
                        downloadButton.textContent = "Download JSON";
                        downloadButton.addEventListener("click", function(e) {
                            e.preventDefault(); // Prevent any default action
                            e.stopPropagation(); // Stop event propagation
                            console.log("Downloading JSON for scan ID:", scan.scan_id);
                            window.location.href = `/api/download_scan_json/${scan.scan_id}`;
                        });
                        actionsBox.appendChild(downloadButton);
                    }

                    const deleteButton = document.createElement("button");
                    deleteButton.textContent = "Delete Scan";
                    deleteButton.addEventListener("click", function(e) {
                        e.preventDefault(); 
                        e.stopPropagation();
                        console.log("Deleting Scan:", scan.scan_id);
                        confirmation_string = `Are you sure you want to delete scan ${scan.scan_id}?`
                        showConfirmationBox(confirmation_string);
                        let currentChecks = 0;
                
                        const checkConfirmation = () => {
                            if (confirmStatus === true) {
                                // user confirmed
                                confirmDiv.style.display = 'none';
                                fetch("/deleteScan", {
                                    method: "POST",
                                    headers: {
                                        "Content-Type": "application/json"
                                    },
                                    body: JSON.stringify({
                                        scan_id: scan.scan_id
                                    })
                                })
                                .then(response => response.json())
                                .then(data => {
                                    console.log(data);
                                    if (data.Deleted_Scan) {
                                        alert(`Scan with ID ${data.Deleted_Scan} has been deleted.`);
                                        window.location.reload();
                                    } else if (data.error) {
                                        alert(`Error deleting scan: ${data.error}`);
                                    } else {
                                        alert("An unexpected error occurred during deletion.");
                                    }
                                })
                                .catch(error => {
                                    console.error("Fetch error:", error);
                                    alert("Failed to connect to the server to delete the scan.");
                                });
                            } else if (confirmStatus === false) {
                                // users didn't confirm
                                confirmDiv.style.display = 'none';
                                // continously check
                            } else if (currentChecks < maxChecks) {
                                currentChecks++;
                                setTimeout(checkConfirmation, checkInterval);
                            } else {
                                // timed out confirmation
                                confirmDiv.style.display = 'none';
                            }
                        };
    
                        setTimeout(checkConfirmation, checkInterval);
                    });

                    actionsBox.appendChild(deleteButton);


                    newRow.appendChild(actionsBox);

                    dashboard.append(newRow);

                }
            });
        })
        .catch(error => {
            console.error("Error updating scan data:", error);
        });
}

// functionality of the run scan button
document.getElementById("run_scan").addEventListener("click", function(event) {
    event.preventDefault();
    
    fetch("/triggerScan", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            scan_name: website_data.name,
            scan_url: website_data.url,
            website_id: website_data.id
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => { throw new Error(text); });
        }
        return response.json();
    })
    .then(result => {
        alert("Scan triggered successfully!\n" + JSON.stringify(result, null, 2));
        console.log("Scan result:", result);
    })
    .catch(error => {
        // I know this is not great, but it works for now
        if (error['error'] === 'Scan canceled') {
            //pass
        }
    });
    location.reload();
});

// functionality of the cancel scan button
document.getElementById("cancel").addEventListener("click", function() {
    fetch("/cancelScan", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => { throw new Error(text); });
        }
        return response.json();
    })
    .then(result => {
        alert(JSON.stringify(result, null, 2));
        console.log("Scan result:", result);
    })
    .catch(error => {
        console.error("Error triggering scan:", error);
        alert("Error triggering scan: " + error.message);
    });
    location.reload(true);
});

// buttons for the filter
const filterMenu = document.querySelector('.filter_options')
const filterBtn = document.querySelector('.filter_button')

let isFilterOpen = false  // boolean to test if filter is open

// opens filter window when button is clicked
filterBtn.addEventListener('click', () => {
    if (isFilterOpen === false) { // do this if menu is closed
        filterMenu.classList.add('open')
        isFilterOpen = true
        document.body.style.overflow = "hidden";
        document.documentElement.style.overflow = "hidden";
        console.log("opened") 

    }
    else { // do this is menu is open
        filterMenu.classList.remove('open')
        isFilterOpen = false
        document.body.style.overflow = "auto";
        document.documentElement.style.overflow = "auto";
    }
    
})

// applys filter settings and closes filter window
document.getElementById('apply_filter').addEventListener('click', () => {
    // closes filter window
    filterMenu.classList.remove('open')
    isFilterOpen = false
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
    // resets the filter form
    document.getElementById("filter_form").reset();
});


const shareMenu = document.querySelector('.share_options')
const shareBtn = document.querySelector('.share_button')

let isShareOpen = false  // boolean to test if share window is open

// check if share is an element that exists
if (shareBtn) {
    shareBtn.addEventListener('click', () => {
        if (isShareOpen === false) { // do this if menu is closed
            shareMenu.classList.add('open')
            isShareOpen = true
            document.body.style.overflow = "hidden";
            document.documentElement.style.overflow = "hidden";
            console.log("opened")
    
        }
        else { // do this is menu is open
            shareMenu.classList.remove('open')
            isShareOpen = false
            document.body.style.overflow = "auto";
            document.documentElement.style.overflow = "auto";
        }
    
    })
}

// default unconfirmed
let confirmStatus = null;
const confirmDiv = document.getElementById("confirm");
const confirmText = document.getElementById("confirm-text");
const confirmButton = document.getElementById("confirm-button");
const confirmCancelButton = document.getElementById("confirm-cancel-button");



function showConfirmationBox(confirmation_string) {
    confirmText.textContent = confirmation_string;
    confirmStatus = null;
    confirmDiv.style.display = 'flex';
}

confirmButton.addEventListener("click", () => {
    confirmStatus = true;
    confirmDiv.style.display = 'none';
});

confirmCancelButton.addEventListener("click", () => {
    confirmStatus = false;
    confirmDiv.style.display = 'none';
});

const maxChecks = 100;
const checkInterval = 100;

// functionality for the delete website button
const deleteWebsiteButton = document.getElementById("delete-website");
if (deleteWebsiteButton) {
    deleteWebsiteButton.addEventListener('click', () => {
        confirmation_string = `Are you sure you want to delete ${website_data.name}?`
        showConfirmationBox(confirmation_string);
        let currentChecks = 0;

        const checkConfirmation = () => {
            if (confirmStatus === true) {
                // user confirmed
                confirmDiv.style.display = 'none';
                deleteWebsite();
            } else if (confirmStatus === false) {
                // users didn't confirm
                confirmDiv.style.display = 'none';
                // continously check
            } else if (currentChecks < maxChecks) {
                currentChecks++;
                setTimeout(checkConfirmation, checkInterval);
            } else {
                // timed out confirmation
                confirmDiv.style.display = 'none';
            }
        };

        setTimeout(checkConfirmation, checkInterval);
    });
}

function deleteWebsite() {
    fetch('/deleteWebsite', {
        method: 'POST',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ website_id: website_data.id })
    })
    .then(response => response.json())
    .then(data => {
        if (data.redirect) {
            window.location.href = data.redirect;
        }
    })
    .catch(error => {
        console.error("Error deleting website:", error);
        window.location.href = "/dashboard";
    });
}