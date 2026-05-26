document.getElementById("register").addEventListener("click", function(event) {
    event.preventDefault();

    const scan_name = document.getElementById("scan_name").value;
    const scan_url  = document.getElementById("url").value;
    
    if (!scan_url) {
        alert("Please enter a URL.");
        return;
    }

    fetch("/registerWebsite", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            scan_name: scan_name,
            scan_url: scan_url,
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => { throw new Error(text); });
        }
        return response.json();
    })
    .then(result => {
        alert(result['message'] + "\n" + result['site name'] + "\n" + result['website url']);
        console.log("Scan result:", result);
        window.location.href = "/website/" + result['website_id'];
    })
    .catch(error => {
        // I know this is not great, but it works for now
        if (error['error'] === 'Scan canceled')
        {
            //pass
        }
        else
        {
            console.error("Error triggering scan:", error);
            alert("Error triggering scan: " + error.message);
        }
    });
});

// display reocurrance settings when checkbox is clicked
document.getElementById("isRecurring").addEventListener("change", function() {
    let recurranceSettings = document.getElementById("settings");
    if (this.checked) {
        recurranceSettings.style.display = "inline-block";
    } else {
        recurranceSettings.style.display = "none";
    }
})