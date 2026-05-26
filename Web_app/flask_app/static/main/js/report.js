document.addEventListener('DOMContentLoaded', function() {
    // Get scan_id from report_data
    const scan_id = $('#report_data').data('scan_id');

    // Set up tab switching
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove active class from all tabs
            tabs.forEach(t => t.classList.remove('active'));
            // Add active class to clicked tab
            this.classList.add('active');

            // Hide all tab content
            const tabContents = document.querySelectorAll('.tab-content');
            tabContents.forEach(content => content.classList.remove('active'));

            // Show the selected tab content
            const tabName = this.getAttribute('data-tab');
            document.getElementById(`${tabName}-tab`).classList.add('active');
        });
    });

    // Initialize data
    initializeDashboard(scan_id);
});

// Initialize dashboard with data
async function initializeDashboard(scan_id) {
    try {
        // Show loading indicators
        document.querySelectorAll('.loading-indicator').forEach(indicator => {
            indicator.style.display = 'block';
        });

        // Get website_id from data attribute
        const website_id = $('#report_data').data('web_id');
        console.log("Retrieved website ID:", website_id);
        console.log("Current scan ID:", scan_id);

        // Error check - verify we have valid IDs before proceeding
        if (!website_id || !scan_id) {
            throw new Error("Missing required website_id or scan_id");
        }

        // Fetch data in parallel
        const [comparisonData, vulnerabilityData, websiteData] = await Promise.all([
            fetchComparisonData(scan_id),
            fetchVulnerabilityData(scan_id),
            fetchWebsiteData(website_id)
        ]);

        // Update scan information in header // removed this section to allow html to display website name itself
        //const website_name = ($('#report_data').data('website_name')) || "Website";
        //document.querySelector('.dashboard-header h1').textContent =
        //    `${website_name} Security Report`;
        
        // Calculate summary metrics
        const summaryMetrics = calculateSummaryMetrics(comparisonData, vulnerabilityData);

        // Update summary cards
        updateSummaryCards(summaryMetrics, comparisonData);

        // Update insights section
        updateInsights(summaryMetrics, vulnerabilityData, comparisonData);

        // Create charts
        createCharts(comparisonData, vulnerabilityData, websiteData);

        // chart colors
        const chartColors = {
            high: '#d9534f',
            medium: '#f0ad4e',
            low: '#5bc0de',
            info: '#5cb85c',
            remediated: '#28a745',
            pending: '#dc3545',
            background: '#1c1c1d',
            text: '#ffffff',
            grid: '#444444'
};
        //risk score trend in trends tab
        fetchRiskScoreTrend(website_id, scan_id)
            .then(riskTrendData => {
                drawRiskScoreTrendChart(riskTrendData, chartColors);
                createRiskTrendChart(riskTrendData,chartColors);
                drawRemediationRateChart(riskTrendData, chartColors);

            })
            .catch(error => {
                console.error("Error loading risk score trend:", error);
                document.getElementById('risk-score-trend-chart').innerHTML =
                    `<div class="error-message">Unable to load trend data</div>`;
            });


        // Trends tab, Scan activity
        fetchScanActivity(website_id, scan_id)
            .then(activityData => {
                drawScanActivityChart(activityData, chartColors);
            })
            .catch(error => {
                console.error("Error loading scan activity:", error);
                document.getElementById('scan-activity-chart').innerHTML =
                    `<div class="error-message">Unable to load scan activity</div>`;
            });

        // gets data for the vulnerability discovery rate graph
        fetchVulnerabilityDiscoveryRate(website_id, scan_id)
            .then(data => {
                // draws the vulnerability discovery rate graph
                drawVulnerabilityDiscoveryChart(data, chartColors);
            })
            .catch(error => {
                console.error("Error loading vulnerability discovery rate:", error);
                document.getElementById('vulnerability-discovery-chart').innerHTML =
                    `<div class="error-message">Unable to load discovery data</div>`;
            });

        // gets data for the remediation rate
        fetchRemediationRate(website_id, scan_id)
            .then(rateData => {
                // drawRemediationRateChart(rateData, chartColors);
            })
            .catch(error => {
                console.error("Error loading remediation rate data:", error);
                document.getElementById('remediation-rate-chart').innerHTML =
                    `<div class="error-message">Unable to load remediation rate data</div>`;
            });
        
        // gets data for scanned websites
        fetchScannedWebsites(scan_id)
            .then(scannedData => {
                // creates scanned websites table
                populateScannedWebsiteTable(scannedData);
            })
            .catch(error => {
                 console.error("Error loading scanned websites:", error);
                 document.getElementById('websites-table-body').innerHTML =
                    `<tr><td colspan="7" class="text-center">Unable to load scanned website data</td></tr>`;
            });


        // Populate tables
        populateVulnerabilityTable(vulnerabilityData, comparisonData);
        populateWebsiteTable(websiteData);

        // Hide loading indicators
        document.querySelectorAll('.loading-indicator').forEach(indicator => {
            indicator.style.display = 'none';
        });
    } catch (error) {
        console.error("Error initializing dashboard:", error);

        // Hide loading indicators
        document.querySelectorAll('.loading-indicator').forEach(indicator => {
            indicator.style.display = 'none';
        });

        // Show error message
        document.querySelectorAll('.chart-placeholder').forEach(placeholder => {
            placeholder.innerHTML = `<div class="error-message">Error loading data: ${error.message}. Please try again.</div>`;
        });

        // Update header with error
        const website_name = $('#report_data').data('website_name') || "Website";
        document.querySelector('.dashboard-header h1').textContent =
            `${website_name} Security Report (Error Loading Data)`;
    }
}



// API data fetching functions
async function fetchComparisonData(scan_id) {
    const response = await fetch(`/api/dashboard/scan_comparison/${scan_id}`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
}

// Fetch vulnerability data from API
async function fetchVulnerabilityData(scan_id) {
    const response = await fetch(`/api/dashboard/scan_vulnerabilities/${scan_id}`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
}

// Fetch website data from API
async function fetchWebsiteData(website_id) {
    const response = await fetch(`/api/dashboard/website/${website_id}`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    // Return as array with single item for compatibility with existing code
    const data = await response.json();
    return [data];
}

// Fetch risk score
async function fetchRiskScoreTrend(website_id, scan_id) {
    const response = await fetch(`/api/trends/risk_scores/${website_id}/${scan_id}`);
    if (!response.ok) {
        throw new Error("Failed to fetch risk score trend");
    }
    return await response.json();
}


// Calculate metrics for the dashboard
function calculateSummaryMetrics(comparisonData, vulnerabilityData) {
    // Extract current scan data
    const current = comparisonData.current;

    const totalHighRisks = current.high_risks || 0;
    const totalMediumRisks = current.medium_risks || 0;
    const totalLowRisks = current.low_risks || 0;
    const totalInfoRisks = current.informational_risks || 0;

    const totalVulnerabilities = totalHighRisks + totalMediumRisks + totalLowRisks + totalInfoRisks;

    // Calculate overall risk score (weighted by severity)
    const overallRiskScore = calculateRiskScore(totalHighRisks, totalMediumRisks, totalLowRisks);

    return {
        totalHighRisks,
        totalMediumRisks,
        totalLowRisks,
        totalInfoRisks,
        totalVulnerabilities,
        overallRiskScore,
        riskLevel: getRiskLevel(overallRiskScore),
        scanDate: formatDate(current.scan_date),
        websiteCount: 1
    };
}

// Calculate risk score based on vulnerabilities
function calculateRiskScore(high, medium, low) {
    return Math.min(100, Math.round((high * 15 + medium * 1 + low * 0.1) / 10));
}

// Get risk level label based on score
function getRiskLevel(score) {
    if (score >= 75) return 'Critical'
    if (score >= 50) return 'High';
    if (score >= 25) return 'Medium';
    return 'Low';
}

// Get CSS class for risk level
function getRiskClass(level) {
    switch(level.toLowerCase()) {
        case 'critical': return 'critical-risk';
        case 'high': return 'high-risk';
        case 'medium': return 'medium-risk';
        case 'low': return 'low-risk';
        default: return 'low-risk';
    }
}

// format the dates into local time strings
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Update summary cards with calculated metrics
function updateSummaryCards(metrics, comparisonData) {
    // Update overall risk score
    const overallRiskScore = document.getElementById('overall-risk-score');
    overallRiskScore.textContent = metrics.overallRiskScore;
    overallRiskScore.className = `score ${getRiskClass(metrics.riskLevel)}`;

    const riskLabel = overallRiskScore.nextElementSibling;
    riskLabel.textContent = metrics.riskLevel + ' Risk';
    riskLabel.className = `risk-label ${getRiskClass(metrics.riskLevel)}`;

    // Update active vulnerabilities
    document.getElementById('active-vulnerabilities').textContent = metrics.totalVulnerabilities;

    // Update risk breakdown
    const riskBreakdown = document.querySelector('.risk-breakdown');
    riskBreakdown.innerHTML = `
        <span class="high-risk">${metrics.totalHighRisks} High</span>
        <span class="medium-risk">${metrics.totalMediumRisks} Medium</span>
        <span class="low-risk">${metrics.totalLowRisks} Low</span>
        <span class="info-risk">${metrics.totalInfoRisks} Info</span>
    `;

    // Update remediation rate
    if (comparisonData.remediation_metrics && comparisonData.previous) {
        const remediationMetrics = comparisonData.remediation_metrics;
        document.getElementById('remediation-rate').textContent = remediationMetrics.remediation_rate + '%';
        document.querySelector('#remediation-rate').nextElementSibling.textContent =
            `${remediationMetrics.fixed_issues} of ${remediationMetrics.total_previous_vulns} issues fixed`;
    } else {
        document.getElementById('remediation-rate').textContent = 'N/A';
        document.querySelector('#remediation-rate').nextElementSibling.textContent = 'Submit More Scans to View Remediation Data';
    }

    // Update scans card on overview
    let totalSites = comparisonData.all_website_scans ? comparisonData.all_website_scans.length : 0;
    if (totalSites >= 1) {
        // getting the lastest scan date
        let date = new Date(metrics.scanDate);
        latestScan = date.toLocaleDateString();
        // getting total scans for site
        const totalScansForSite = document.getElementById('websites-count');
        // outputting total scans to overview card
        totalScansForSite.textContent = totalSites;
        // outputing last scan date to overview card
        document.querySelector('#websites-count').nextElementSibling.textContent =
                `Last Scan: ${latestScan}`;
    } else {    // if site page has no scans
        const totalScansForSite = document.getElementById('websites-count');
        totalScansForSite.textContent = '1';
        let currDate = new Date(comparisonData.current.scan_date).toLocaleDateString()
        document.querySelector('#websites-count').nextElementSibling.textContent = `Last Scan: ${currDate}`
    }

}

// Update insights section with relevant data
function updateInsights(metrics, vulnerabilityData, comparisonData) {
    document.getElementById('insight-risk-score').textContent = metrics.overallRiskScore;

    const riskLevelElement = document.getElementById('insight-risk-level');
    riskLevelElement.textContent = metrics.riskLevel;
    riskLevelElement.className = getRiskClass(metrics.riskLevel);

    document.getElementById('insight-critical-count').textContent = metrics.totalHighRisks;

    // Find the top vulnerability (most instances)
    const sortedVulnerabilities = [...vulnerabilityData].sort((a, b) => b.count - a.count);
    const topVulnerability = sortedVulnerabilities[0];

    document.getElementById('insight-top-vulnerability').textContent =
        topVulnerability ? topVulnerability.vulnerability_name : 'None detected';

    // Update remediation rate insight
    if (comparisonData && comparisonData.remediation_metrics && comparisonData.previous) {
        const remediationMetrics = comparisonData.remediation_metrics;
        document.getElementById('insight-remediation-rate').textContent = remediationMetrics.remediation_rate;

        // Update highest risk asset based on website name
        const websiteName = $('#report_data').data('website_name');
        document.getElementById('insight-highest-risk').textContent = websiteName;

        // Add detailed remediation information to insights
        if (comparisonData.detailed_comparison) {
            const detailedComparison = comparisonData.detailed_comparison;
            const insightsList = document.querySelector('.insights-list');

            // Create and append new insight for vulnerability changes
            const remediationInsight = document.createElement('li');
            remediationInsight.innerHTML = `
                <strong>Vulnerability Changes:</strong> 
                <span class="${detailedComparison.new_vulnerabilities > 0 ? 'high-risk' : 'low-risk'}">
                    ${detailedComparison.new_vulnerabilities} new
                </span> vulnerabilities discovered and 
                <span class="${detailedComparison.fixed_vulnerabilities > 0 ? 'low-risk' : 'medium-risk'}">
                    ${detailedComparison.fixed_vulnerabilities} fixed
                </span> since previous scan.
            `;

            // Replace the existing last element or append
            const existingItems = insightsList.querySelectorAll('li');
            if (existingItems.length >= 4) {
                insightsList.replaceChild(remediationInsight, existingItems[3]);
            } else {
                insightsList.appendChild(remediationInsight);
            }
        }
    } else {
        document.getElementById('insight-remediation-rate').textContent = 'N/A';
    }
}

// Table functions
function populateVulnerabilityTable(vulnerabilityData, comparisonData) {
    const tableBody = document.getElementById('vulnerabilities-table-body');
    if (!tableBody) return;

    // Clear existing rows
    tableBody.innerHTML = '';

    if (vulnerabilityData.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" class="text-center">No vulnerabilities detected.</td></tr>';
        return;
    }

    // Get lists of new and fixed vulnerabilities if available
    let newVulnNames = [];
    let fixedVulnNames = [];

    if (comparisonData.detailed_comparison) {
        newVulnNames = comparisonData.detailed_comparison.new_vuln_list.map(v => v.vulnerability_name);
        fixedVulnNames = comparisonData.detailed_comparison.fixed_vuln_list.map(v => v.vulnerability_name);
    }

    // Add vulnerability rows
    vulnerabilityData.forEach(vuln => {
        const row = document.createElement('tr');

        // Is this a new vulnerability?
        const isNew = newVulnNames.includes(vuln.vulnerability_name);

        // Determine severity class
        const severityClass = vuln.severity.toLowerCase().includes('high (') ? 'high-risk' :
                              vuln.severity.toLowerCase().includes('medium (') ? 'medium-risk' :
                              vuln.severity.toLowerCase().includes('low (') ? 'low-risk' : 'info-risk';

        // Format the display severity
        const displaySeverity = vuln.severity.toLowerCase().includes('high (') ? 'High' :
                               vuln.severity.toLowerCase().includes('medium (') ? 'Medium' :
                               vuln.severity.toLowerCase().includes('low (') ? 'Low' : 'Informational';

        // For remediated column, we'll use N/A since this shows current active vulnerabilities
        const remediated = 0;
        const remediation_percentage = 0;

        row.innerHTML = `
            <td>${vuln.vulnerability_name} ${isNew ? '<span class="new-tag">NEW</span>' : ''}</td>
            <td><span class="${severityClass}">${displaySeverity}</span></td>
            <td class="text-center">${vuln.count}</td>
            <td class="text-center">${remediated}</td>
            <td>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${remediation_percentage}%"></div>
                </div>
            </td>
        `;

        // Add a click event to show vulnerability details
        row.style.cursor = 'pointer';
        row.addEventListener('click', () => {
            showVulnerabilityDetails(vuln);
        });

        tableBody.appendChild(row);
    });

    // If we have fixed vulnerabilities from previous scan, show them too with a "FIXED" tag
    if (fixedVulnNames.length > 0 && comparisonData.detailed_comparison.fixed_vuln_list) {
        const fixedVulns = comparisonData.detailed_comparison.fixed_vuln_list;

        // Add a separator row
        const separatorRow = document.createElement('tr');
        separatorRow.innerHTML = `
            <td colspan="5" class="text-center fixed-separator">
                <strong>Fixed Vulnerabilities (From Previous Scan)</strong>
            </td>
        `;
        tableBody.appendChild(separatorRow);

        // Add each fixed vulnerability
        fixedVulns.forEach(vuln => {
            const row = document.createElement('tr');
            row.className = 'fixed-vulnerability';

            // Determine severity class
            const severityClass = vuln.severity.toLowerCase().includes('high (') ? 'high-risk' :
                                vuln.severity.toLowerCase().includes('medium (') ? 'medium-risk' :
                                vuln.severity.toLowerCase().includes('low (') ? 'low-risk' : 'info-risk';

            // Format the display severity
            const displaySeverity = vuln.severity.toLowerCase().includes('high (') ? 'High' :
                                vuln.severity.toLowerCase().includes('medium (') ? 'Medium' :
                                vuln.severity.toLowerCase().includes('low (') ? 'Low' : 'Informational';

            row.innerHTML = `
                <td>${vuln.vulnerability_name} <span class="fixed-tag">FIXED</span></td>
                <td><span class="${severityClass}">${displaySeverity}</span></td>
                <td class="text-center">${vuln.count}</td>
                <td class="text-center">${vuln.count}</td>
                <td>
                    <div class="progress-bar-container">
                        <div class="progress-bar" style="width: 100%"></div>
                    </div>
                </td>
            `;

            tableBody.appendChild(row);
        });
    }
}

// opens window showing the details of a vulnerability
function showVulnerabilityDetails(vulnerability) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('vulnerability-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'vulnerability-modal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="close">&times;</span>
                <h2 id="modal-title"></h2>
                <div class="modal-body">
                    <div class="modal-section">
                        <h3>Severity</h3>
                        <p id="modal-severity"></p>
                    </div>
                    <div class="modal-section">
                        <h3>Description</h3>
                        <p id="modal-description"></p>
                    </div>
                    <div class="modal-section">
                        <h3>Solution</h3>
                        <p id="modal-solution"></p>
                    </div>
                    <div class="modal-section">
                        <h3>Instances</h3>
                        <p id="modal-count"></p>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        // Add event listener to close button
        const closeBtn = modal.querySelector('.close');
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });

        // Close modal when clicking outside of it
        window.addEventListener('click', (event) => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    }

    // Update modal content
    document.getElementById('modal-title').textContent = vulnerability.vulnerability_name;

    const severityClass = vulnerability.severity.toLowerCase().includes('high (') ? 'high-risk' :
                         vulnerability.severity.toLowerCase().includes('medium (') ? 'medium-risk' :
                         vulnerability.severity.toLowerCase().includes('low (') ? 'low-risk' : 'info-risk';

    document.getElementById('modal-severity').innerHTML =
        `<span class="${severityClass}">${vulnerability.severity}</span>`;

    document.getElementById('modal-description').innerHTML = vulnerability.description || 'No description available.';
    document.getElementById('modal-solution').innerHTML = vulnerability.solution || 'No solution provided.';
    document.getElementById('modal-count').textContent = vulnerability.count;

    // Show modal
    modal.style.display = 'block';
}

// 
function populateWebsiteTable(websiteData) {
    const tableBody = document.getElementById('websites-table-body');
    if (!tableBody) return;

    // Clear existing rows
    tableBody.innerHTML = '';

    // Since we're using a specific endpoint for this website,
    // we should always have the relevant website in the response
    const relevantWebsites = websiteData;

    if (relevantWebsites.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No website data available.</td></tr>';
        return;
    }

    // Add website rows
    relevantWebsites.forEach(site => {
        const row = document.createElement('tr');

        // Calculate risk score
        const riskScore = calculateRiskScore(
            site.high_risks || 0,
            site.medium_risks || 0,
            site.low_risks || 0
        );
        const riskLevel = getRiskLevel(riskScore);
        const riskClass = getRiskClass(riskLevel);

        // Format date
        let scanDate = 'N/A';
        if (site.scan_date) {
            const date = new Date(site.scan_date);
            scanDate = date.toLocaleDateString();
        }

        row.innerHTML = `
            <td>${site.website_url || 'N/A'}</td>
            <td class="text-center">${site.high_risks || 0}</td>
            <td class="text-center">${site.medium_risks || 0}</td>
            <td class="text-center">${site.low_risks || 0}</td>
            <td class="text-center">${site.informational_risks || 0}</td>
            <td class="text-center"><span class="${riskClass}">${riskScore}</span></td>
            <td>${scanDate}</td>
        `;

        tableBody.appendChild(row);
    });
}

// Create all charts for the dashboard
function createCharts(comparisonData, vulnerabilityData, websiteData) {
    // Define chart colors that match your theme
    const chartColors = {
        high: '#d9534f',
        medium: '#f0ad4e',
        low: '#5bc0de',
        info: '#5cb85c',
        remediated: '#28a745',
        pending: '#dc3545',
        background: '#1c1c1d',
        text: '#ffffff',
        grid: '#444444'
    };

    // Create the charts
    createRiskDistributionChart(comparisonData, chartColors);
    createVulnerabilitiesBySeverityChart(vulnerabilityData, chartColors);
    createRemediationStatusChart(comparisonData, chartColors);

    // Additional charts if we have comparison data
    if (comparisonData.previous) {
        createRemediationChart(comparisonData, chartColors);
        createComparisonChart(comparisonData, chartColors);
    } else { // if there is not previous comparison data
        CreateEmptyRemediationCharts();
    }
}

// Populate Remeditation Chart and Website Comparison when no previous scans exist
function CreateEmptyRemediationCharts() {
    // display text in Remediation Progress chart
    const remediationProgress = document.getElementById('remediation-chart');
    remediationProgress.textContent = "Submit More Scans to View Remediation Data";
    // display text in Website Comparison Chart
    const websiteRiskComparison = document.getElementById('website-comparison-chart');
    websiteRiskComparison.textContent = "Submit More Scans to View Remediation Data";
}

// Create Risk Distribution Chart (pie chart)
function createRiskDistributionChart(comparisonData, colors) {
    const container = document.getElementById('risk-distribution-chart');
    if (!container) return;

    // Clear loading indicator
    container.innerHTML = '';

    // Create canvas
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);

    // Get current scan data
    const current = comparisonData.current;

    // Create the chart
    new Chart(canvas, {
        type: 'pie',
        data: {
            labels: ['High', 'Medium', 'Low', 'Info'],
            datasets: [{
                data: [
                    current.high_risks || 0,
                    current.medium_risks || 0,
                    current.low_risks || 0,
                    current.informational_risks || 0
                ],
                backgroundColor: [colors.high, colors.medium, colors.low, colors.info]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: colors.text
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${context.label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}


// draws the remediation chart for the report
function createRemediationChart(comparisonData, colors) {
    const container = document.getElementById('remediation-chart');
    if (!container) return;

    // Clear loading indicator
    container.innerHTML = '';

    // Create canvas
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);

    // Get remediation metrics
    const metrics = comparisonData.remediation_metrics;

    // Create the chart
    new Chart(canvas, {
        type: 'bar',
        data: {
            labels: ['Vulnerabilities'],
            datasets: [
                {
                    label: 'Fixed',
                    data: [metrics.fixed_issues],
                    backgroundColor: colors.remediated
                },
                {
                    label: 'Current',
                    data: [metrics.total_current_vulns],
                    backgroundColor: colors.pending
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    stacked: false,
                    ticks: {
                        color: colors.text
                    },
                    grid: {
                        color: colors.grid
                    }
                },
                x: {
                    stacked: false,
                    ticks: {
                        color: colors.text
                    },
                    grid: {
                        color: colors.grid
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: colors.text
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.raw}`;
                        }
                    }
                }
            }
        }
    });
}

// create the comparison chart for the report
function createComparisonChart(comparisonData, colors) {
    const container = document.getElementById('website-comparison-chart');
    if (!container) return;

    // Clear loading indicator
    container.innerHTML = '';

    // Create canvas
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);

    // Format dates for labels
    const previous = comparisonData.previous;
    const current = comparisonData.current;

    const prevDate = new Date(previous.scan_date);
    const currDate = new Date(current.scan_date);

    const labels = [
        'Previous (' + prevDate.toLocaleDateString() + ')',
        'Current (' + currDate.toLocaleDateString() + ')'
    ];

    // Create the chart
    new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'High',
                    data: [previous.high_risks || 0, current.high_risks || 0],
                    backgroundColor: colors.high
                },
                {
                    label: 'Medium',
                    data: [previous.medium_risks || 0, current.medium_risks || 0],
                    backgroundColor: colors.medium
                },
                {
                    label: 'Low',
                    data: [previous.low_risks || 0, current.low_risks || 0],
                    backgroundColor: colors.low
                },
                {
                    label: 'Info',
                    data: [previous.informational_risks || 0, current.informational_risks || 0],
                    backgroundColor: colors.info
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: colors.text
                    },
                    grid: {
                        color: colors.grid
                    }
                },
                x: {
                    ticks: {
                        color: colors.text
                    },
                    grid: {
                        color: colors.grid
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: colors.text
                    }
                }
            }
        }
    });
}

// display the vulnerabilities for each sevarity
function createVulnerabilitiesBySeverityChart(vulnerabilityData, colors) {
    const container = document.getElementById('vulnerabilities-by-severity-chart');
    if (!container) return;

    // Clear loading indicator
    container.innerHTML = '';

    // Create canvas
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);

    // Count vulnerabilities by severity
    const highCount = vulnerabilityData.filter(v => v.severity.toLowerCase().includes('high (')).length;
    const mediumCount = vulnerabilityData.filter(v => v.severity.toLowerCase().includes('medium (')).length;
    const lowCount = vulnerabilityData.filter(v => v.severity.toLowerCase().includes('low (')).length;
    const infoCount = vulnerabilityData.filter(v => v.severity.toLowerCase().includes('informational (')).length;

    // Create the chart
    new Chart(canvas, {
        type: 'pie',
        data: {
            labels: ['High', 'Medium', 'Low', 'Info'],
            datasets: [{
                data: [highCount, mediumCount, lowCount, infoCount],
                backgroundColor: [colors.high, colors.medium, colors.low, colors.info]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: colors.text
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${context.label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Create Remediation Status Chart
function createRemediationStatusChart(comparisonData, colors) {
    const container = document.getElementById('remediation-status-chart');
    if (!container) return;

    // Clear loading indicator
    container.innerHTML = '';

    // Create canvas
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);

    // Prepare data
    let remediatedCount = 0;
    let openCount = 0;

    if (comparisonData.remediation_metrics && comparisonData.previous) {
        const metrics = comparisonData.remediation_metrics;
        remediatedCount = metrics.fixed_issues;
        openCount = metrics.total_current_vulns;
    } else {
        // If no comparison data, only show current open issues
        openCount = comparisonData.current.high_risks +
                   comparisonData.current.medium_risks +
                   comparisonData.current.low_risks +
                   comparisonData.current.informational_risks;
    }

    // Create the chart
    new Chart(canvas, {
        type: 'pie',
        data: {
            labels: ['Remediated', 'Open'],
            datasets: [{
                data: [remediatedCount, openCount],
                backgroundColor: [colors.remediated, colors.pending]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: colors.text
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${context.label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}


// risk score trend chart in the trends tab
function drawRiskScoreTrendChart(trendData, colors) {
    const container = document.getElementById('risk-score-trend-chart');
    if (!container) return;

    container.innerHTML = ''; // Clear the loading indicator

    const canvas = document.createElement('canvas');
    container.appendChild(canvas);

    const labels = trendData.map(d => {
        // const date = new Date(d.scan_date);
        // return date.toLocaleDateString();
        const date = new Date(d.scan_date);
    const day = String(date.getUTCDate());
    const month = String(date.getUTCMonth() + 1);
    const year = date.getUTCFullYear();
    return `${month}/${day}/${year}`;
    });

    const data = trendData.map(d => d.risk_score);

    new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Risk Score',
                data: data,
                borderColor: colors.low,
                backgroundColor: colors.low,
                fill: false,
                tension: 0.3,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { color: colors.text },
                    grid: { color: colors.grid }
                },
                x: {
                    ticks: { color: colors.text },
                    grid: { color: colors.grid }
                }
            },
            plugins: {
                legend: {
                    labels: { color: colors.text }
                },
                tooltip: {
                    callbacks: {
                        label: context => `Risk Score: ${context.raw}`
                    }
                }
            }
        }
    });
}


// function to get the scan activity data
// Function to fetch scan activity up to a selected scan
async function fetchScanActivity(website_id, scan_id) {
    const response = await fetch(`/api/trends/scan_activity/${website_id}/${scan_id}`);
    if (!response.ok) {
        throw new Error("Failed to fetch scan activity");
    }
    return await response.json();
}


// draws the scan activity chart in the trends tab
function drawScanActivityChart(scanActivityData, colors) {
    const container = document.getElementById('scan-activity-chart');
    if (!container) return;

    container.innerHTML = '';

    const canvas = document.createElement('canvas');
    container.appendChild(canvas);

    const labels = scanActivityData.map(d => {
    const date = new Date(d.scan_day);
    const day = String(date.getUTCDate());
    const month = String(date.getUTCMonth() + 1);
    const year = date.getUTCFullYear();
    return `${month}/${day}/${year}`;
    });

    const data = scanActivityData.map(d => d.scan_count);

    new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Scans',
                data: data,
                backgroundColor: colors.low
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: colors.text },
                    grid: { color: colors.grid }
                },
                x: {
                    ticks: { color: colors.text },
                    grid: { color: colors.grid }
                }
            },
            plugins: {
                legend: {
                    labels: { color: colors.text }
                },
                tooltip: {
                    callbacks: {
                        label: context => `${context.raw} scan(s)`
                    }
                }
            }
        }
    });
}


// Creating the Risk Trend Chart for the Overview page
function createRiskTrendChart(trendData, colors) {
    const container = document.getElementById('risk-trend-chart');
    if (!container) return;

    container.innerHTML = ''; // Clear the loading indicator

    const canvas = document.createElement('canvas');
    container.appendChild(canvas);

    const labels = trendData.map(d => {
        // const date = new Date(d.scan_date);
        // return date.toLocaleDateString();
        const date = new Date(d.scan_date);
        const day = String(date.getUTCDate());
        const month = String(date.getUTCMonth() + 1);
        const year = date.getUTCFullYear();
        return `${month}/${day}/${year}`;
    });

    // hold the data for each level of vulnerability
    const highCount = trendData.map(d => d.high_risks);
    const mediumCount = trendData.map(d => d.medium_risks);
    const lowCount = trendData.map(d => d.low_risks);

    // make the canvas and apply vulnerability data
    new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
            {
                label: 'High Risks',
                data: highCount,
                borderColor: colors.high,
                backgroundColor: colors.high,
                fill: false,
                tension: 0.25,
                pointRadius: 4,
                pointHoverRadius: 6
            },
            {
                label: 'Medium Risks',
                data: mediumCount,
                borderColor: colors.medium,
                backgroundColor: colors.medium,
                fill: false,
                tension: 0.3,
                pointRadius: 4,
                pointHoverRadius: 6
            },
            {
                label: 'Low Risks',
                data: lowCount,
                borderColor: colors.low,
                backgroundColor: colors.low,
                fill: false,
                tension: 0.3,
                pointRadius: 4,
                pointHoverRadius: 6
            }
        ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: colors.text },
                    grid: { color: colors.grid }
                },
                x: {
                    ticks: { color: colors.text },
                    grid: { color: colors.grid }
                }
            },
            plugins: {
                legend: {
                    labels: { color: colors.text }
                },
                tooltip: {
                    callbacks: {
                        label: context => `Risk Trend for each vulnerability: ${context.raw}`
                    }
                }
            }
        }
    });
}


// get data about the discovery rate of scans
async function fetchVulnerabilityDiscoveryRate(website_id, scan_id) {
    const response = await fetch(`/api/trends/vulnerability_discovery/${website_id}/${scan_id}`);
    if (!response.ok) {
        throw new Error("Failed to fetch vulnerability discovery rate");
    }
    return await response.json();
}

// draw the graph display the discovery rate chart
function drawVulnerabilityDiscoveryChart(data, colors) {
    const container = document.getElementById('vulnerability-discovery-chart');
    if (!container) return;

    container.innerHTML = '';
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);

    const labels = data.map(d => {
    const date = new Date(d.date);
    const day = String(date.getUTCDate());
    const month = String(date.getUTCMonth() + 1);
    const year = date.getUTCFullYear();
    return `${month}/${day}/${year}`;
    });

    const values = data.map(d => d.total_discovered);

    new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Vulnerabilities Discovered',
                data: values,
                backgroundColor: colors.medium
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: colors.text },
                    grid: { color: colors.grid }
                },
                x: {
                    ticks: { color: colors.text },
                    grid: { color: colors.grid }
                }
            },
            plugins: {
                legend: {
                    labels: { color: colors.text }
                },
                tooltip: {
                    callbacks: {
                        label: context => `${context.raw} vulnerabilities`
                    }
                }
            }
        }
    });
}

// get data for the remediation rate values
async function fetchRemediationRate(website_id, scan_id) {
    const response = await fetch(`/api/trends/remediation_rate/${website_id}/${scan_id}`);
    if (!response.ok) {
        throw new Error("Failed to fetch remediation rate data");
    }
    return await response.json();
}

// draw the chart with no remediaiton rate
function drawRemediationRateChart(data, colors) {
    const container = document.getElementById('remediation-rate-chart');
    if (!container) return;

    let diff = 0;
    let last_total = 0;

    // count the total vulnerabilities and compare to last scan
    const change = data.map(d => {
        let high = d.high_risks || 0;
        let med = d.medium_risks || 0;
        let low = d.low_risks || 0;
        let total = high + med + low;   // total for this scan

        diff = total - last_total;  // get difference from last scan
        let unrounded = total !== 0 ? (diff / total) * 100 : 0;  // get change in %

        let float = unrounded.toFixed(4);
        let output = parseFloat(float.replace(',', '.'));   // get into right format

        last_total = total;

        return output === 100.0000 ? 0.0000 : output; // return output if not first scan
    });

    container.innerHTML = '';
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);

    let labels = data.map(d => new Date(d.scan_date).toLocaleDateString()); // gets dates for label
    // checks the value of the last element and sets color accordingly
    const rateColor = (change[change.length - 1]) <= 0 ? 'green' : 'red';

    new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Change in Vulnerability (%)',
                data: change,
                borderColor: rateColor,
                backgroundColor: rateColor,
                fill: false,
                tension: 0.25,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        // adds % to y-axis
                        color: colors.text,
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    grid: { color: colors.grid }
                },
                x: {
                    ticks: { color: colors.text },
                    grid: { color: colors.grid }
                }
            },
            plugins: {
                legend: {
                    labels: { color: colors.text }
                },
                tooltip: {
                    callbacks: {
                        label: context => `Remediation: ${context.raw}%`
                    }
                }
            }
        }
    });
}

// get the list of scanned websites from the routes
async function fetchScannedWebsites(scan_id) {
    const response = await fetch(`/api/dashboard/scanned_websites/${scan_id}`);
    if (!response.ok) {
        throw new Error(`Failed to fetch scanned websites`);
    }
    return await response.json();
}

// populate the websites tab with all the websites found
function populateScannedWebsiteTable(scannedData) {
    const tableBody = document.getElementById('websites-table-body');
    tableBody.innerHTML = '';

    if (scannedData.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="2" class="text-center">No scanned websites available.</td></tr>';
        return;
    }

    // group by website url
    const groupedByWebsite = {};
    scannedData.forEach(entry => {
        const site = entry.website_url || 'N/A';
        if (!groupedByWebsite[site]) {
            groupedByWebsite[site] = [];
        }
        groupedByWebsite[site].push(entry.vulnerability_name || 'None');
    });

    // Sort groupedWebsites by most vulnerabilities
    const items = Object.entries(groupedByWebsite);
    items.sort(function([, listA], [, listB]){

        const lengthA = listA[0] === 'None' ? 0 : listA.length;
        const lengthB = listB[0] === 'None' ? 0: listB.length;

        return lengthB - lengthA;
    })

    items.forEach(entry => {
        const [websiteUrl, vulnList] = entry;

        const parentRow = document.createElement('tr');
        parentRow.classList.add('website-row');

        const numVulns = groupedByWebsite[websiteUrl][0] === 'None' ? 0 : groupedByWebsite[websiteUrl].length;
        parentRow.innerHTML = `
            <td>${websiteUrl}</td>
            <td class="text-center">Vulnerabilities: ${numVulns}</td>`;

        const childRow = document.createElement('tr');
        if (groupedByWebsite[websiteUrl][0] !== 'None') {

            childRow.classList.add('child-row');
            childRow.innerHTML = `
                <td colspan="2">
                <ul>
                ${groupedByWebsite[websiteUrl].map(v => `<li>${v}</li>`).join('')}
                </ul>
                </td>`;
            childRow.style.display = 'none';

        }

        parentRow.addEventListener('click', () => {
            if (childRow.style.display === 'none') {
                childRow.style.display = '';
            } else {
                childRow.style.display = 'none';
            }
        });

        tableBody.appendChild(parentRow);
        tableBody.appendChild(childRow);
    });
}



document.addEventListener('DOMContentLoaded', () => {
  initializeWebsiteCharts();
});

// create the charts where the websites will be displayed
async function initializeWebsiteCharts() {
  try {
    const website_id = $('#report_data').data('web_id');
    const scan_id = $('#report_data').data('scan_id');

    // Gets both data sets
    const [riskScores, highRisks] = await Promise.all([
      fetchRiskScoreByWebsite(website_id, scan_id),
      fetchHighRiskIssuesByWebsite(website_id, scan_id)
    ]);
    // Fills in the tables
    drawRiskScoreByWebsiteChart(riskScores);
    drawHighRiskIssuesByWebsiteChart(highRisks);
  } catch (error) {
    console.error("Error initializing website charts:", error);
  }
}

// get risk score data for each website
async function fetchRiskScoreByWebsite(website_id, scan_id) {
  const response = await fetch(`/api/report/risk_score_by_website/${website_id}/${scan_id}`);
  if (!response.ok) {
    throw new Error('Failed to fetch risk score data');
  }
  return await response.json();
}

// get the highest risk issue for the scan
async function fetchHighRiskIssuesByWebsite(website_id, scan_id) {
  const response = await fetch(`/api/report/high_risk_by_website/${website_id}/${scan_id}`);
  if (!response.ok) {
    throw new Error('Failed to fetch high risk data');
  }
  return await response.json();
}

// draw the chart displaying risk score for each site
function drawRiskScoreByWebsiteChart(data) {
  const container = document.getElementById('risk-score-by-website-chart');
  container.innerHTML = ''; 

  const canvas = document.createElement('canvas');
  container.appendChild(canvas);

  const fullLabels = data.map(d => d.website_name);
  // Cutoff for websites with long names
  const truncatedLabels = fullLabels.map(label =>
    label.length > 30 ? label.substring(0, 30) + '...' : label
  );
  const scores = data.map(d => d.risk_score);

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: truncatedLabels,
      datasets: [
        {
          label: 'Risk Score',
          data: scores,
          backgroundColor: '#5bc0de',
        },
      ],
      fullLabels: fullLabels,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: '#ffffff'
          }
        },
        tooltip: {
          callbacks: {
            title: function (context) {
              const index = context[0].dataIndex;
              const chart = context[0].chart;
              return chart.data.fullLabels[index];
            },
          },
        },
      },
      scales: {
        x: {
          ticks: {
            autoSkip: false,
            maxRotation: 45,
            minRotation: 45,
            color: '#ffffff'
          },
          grid: {
            color: '#444444'
          }
        },
        y: {
          beginAtZero: true,
          max: 100,
          ticks: {
            stepSize: 10,
            color: '#ffffff'
          },
          grid: {
            color: '#444444'
          }
        },
      },
    },
  });
}

// draw the highest risk issue for each website
function drawHighRiskIssuesByWebsiteChart(data) {
  const container = document.getElementById('high-risk-by-website-chart');
  container.innerHTML = '';

  const canvas = document.createElement('canvas');
  container.appendChild(canvas);

  const fullLabels = data.map(d => d.website_name);
  // Cutoff for long website names
  const truncatedLabels = fullLabels.map(label =>
    label.length > 30 ? label.substring(0, 30) + '...' : label
  );
  const values = data.map(d => d.high_risks);

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: truncatedLabels,
      datasets: [
        {
          label: 'High Risk Issues',
          data: values,
          backgroundColor: '#d9534f',
        },
      ],
      fullLabels: fullLabels,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: '#ffffff'
          }
        },
        tooltip: {
          callbacks: {
            title: function (context) {
              const index = context[0].dataIndex;
              const chart = context[0].chart;
              return chart.data.fullLabels[index];
            },
          },
        },
      },
      scales: {
        x: {
          ticks: {
            autoSkip: false,
            maxRotation: 45,
            minRotation: 45,
            color: '#ffffff'
          },
          grid: {
            color: '#444444'
          }
        },
        y: {
          beginAtZero: true,
          suggestedMax: Math.max(100, Math.max(...values)),
          ticks: {
            stepSize: 10,
            color: '#ffffff'
          },
          grid: {
            color: '#444444'
          }
        }
      },
    },
  });
}



