document.addEventListener("DOMContentLoaded", function () {
    const settingsBtn = document.getElementById("settings-btn");
    const settingsDropdown = document.getElementById("settings-dropdown");
    const profileLink = document.getElementById("profile-link");
    const switchThemeBtn = document.getElementById("toggle-theme");
    const logoImg = document.getElementById("theme-logo");

    function closeDropdownOnClickOutside(event) {
        if (
            !settingsBtn.contains(event.target) &&
            !settingsDropdown.contains(event.target) &&
            event.target.id !== "profile-link"
        ) {
            settingsDropdown.classList.remove("show");
        }
    }

    if (settingsBtn && settingsDropdown) {
        settingsBtn.addEventListener("click", function (event) {
            event.preventDefault();
            settingsDropdown.classList.toggle("show");
        });

        settingsDropdown.addEventListener("click", function (event) {
            event.stopPropagation();
        });

        document.addEventListener("click", closeDropdownOnClickOutside);
    }

    if (profileLink) {
        profileLink.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            document.body.style.pointerEvents = "none";
            window.location.href = "/settings";
            setTimeout(() => {
                document.body.style.pointerEvents = "auto";
            }, 1000);
        });
    }

    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "light") {
        document.body.classList.add("light-mode");
    } else {
        document.body.classList.add("dark-mode");
    }

    function updateLogo() {
        if (!logoImg) return;
        if (document.body.classList.contains("light-mode")) {
            logoImg.src = "/static/main/images/McK-RGB-McK-Logo-4CMYK.png";
        } else {
            logoImg.src = "/static/main/images/McK-Logo-W.png";
        }
    }

    updateLogo();

    if (switchThemeBtn) {
        switchThemeBtn.addEventListener("click", function (e) {
            e.preventDefault();
            document.body.classList.toggle("light-mode");
            document.body.classList.toggle("dark-mode");

            const newTheme = document.body.classList.contains("light-mode") ? "light" : "dark";
            localStorage.setItem("theme", newTheme);
            updateLogo();
        });
    }
});
