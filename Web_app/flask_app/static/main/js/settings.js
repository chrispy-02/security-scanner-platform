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

// adds event listener for each delete button
const deleteUserButtons = document.querySelectorAll("button[name='delete_user']");

deleteUserButtons.forEach(deleteButton => {
    deleteButton.addEventListener('click', (event) => {
        event.preventDefault();

        const userIdToDelete = deleteButton.value;

        const confirmation_string = `Are you sure you want to delete user with ID: ${userIdToDelete}?`;
        showConfirmationBox(confirmation_string);
        let currentChecks = 0;

        const checkConfirmation = () => {
            if (confirmStatus === true) {
                // user confirmed
                confirmDiv.style.display = 'none';
                // finds the cloest delete button
                const formToDelete = deleteButton.closest('form');
                if (formToDelete) {
                    fetch('/delete_user', {
                        method: 'POST',
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({ website_id: website_data.id })
                    })
                    .then(response => response.json())
                } else {
                    console.error("Error: Could not find the parent form for the delete button.");
                }
            } else if (confirmStatus === false) {
                // user canceled
                confirmDiv.style.display = 'none';
                // continously checks
            } else if (currentChecks < maxChecks) {
                currentChecks++;
                setTimeout(checkConfirmation, checkInterval);
            } else {
                // timed out 
                confirmDiv.style.display = 'none';
            }
        };

        setTimeout(checkConfirmation, checkInterval);
    });
});