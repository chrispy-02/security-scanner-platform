let count = 0
function checkCredentials(event)
{
    // If event is valid, prevent default behavior
    // (Default behavior is refreshing the page
    // therefore stopping execution of jQuery request)
    if (event)
    {
        event.preventDefault();
    }

    // Package data in a JSON object
    const email = $('#email').val()
    const password = $('#password').val()
    const next = $('#next_page').val()

    var data_d = {'email': email, 'password': password}

    // SEND DATA TO SERVER VIA jQuery.ajax({})
    $.ajax(
    {
        url: "/processlogin",
        data: data_d,
        type: "POST",
        success:function(returned_data)
        {
            // Parse returned data and log to console
            returned_data = JSON.parse(returned_data);

            // If returned data is authenticated, send user to homepage
            if (returned_data.success === 1)
            {
                 if (next !== 'None')
                {
                    window.location.href = next;
                }
                 else
                 {
                     window.location.href = "/home";
                 }

            }
        }
    });
}

document.getElementById("google-sign-in-btn").addEventListener("click", function() {
    let nextPage = document.getElementById("next_page").value;
    let url = window.GOOGLE_LOGIN_URL; // We retrieve the global variable
    if (nextPage) {
      url += "?next_page=" + encodeURIComponent(nextPage);
    }
    window.location.href = url;
  });