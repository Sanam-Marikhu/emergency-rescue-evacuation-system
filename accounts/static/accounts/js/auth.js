```javascript
document.addEventListener("DOMContentLoaded", function () {

    // ==================================
    // 1. Show / Hide Password
    // ==================================

    const toggleButtons = document.querySelectorAll(".password-toggle");

    toggleButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            const fieldId = button.dataset.passwordTarget;
            const passwordField = document.getElementById(fieldId);

            if (!passwordField) {
                console.error("Password field not found:", fieldId);
                return;
            }

            const showPassword = passwordField.type === "password";

            passwordField.type = showPassword ? "text" : "password";

            // Change the eye icon.
            button.textContent = showPassword ? "🙈" : "👁";

            button.setAttribute(
                "aria-label",
                showPassword ? "Hide password" : "Show password"
            );

            button.setAttribute(
                "title",
                showPassword ? "Hide password" : "Show password"
            );

        });

    });


    // ==================================
    // 2. Live Password Validation
    // ==================================

    const passwordField = document.getElementById("id_password1");
    const usernameField = document.getElementById("id_username");
    const emailField = document.getElementById("id_email");

    if (!passwordField) {
        return;
    }

    const rules = {
        length: document.getElementById("rule-length"),
        number: document.getElementById("rule-number"),
        common: document.getElementById("rule-common"),
        similar: document.getElementById("rule-similar")
    };


    function updateRule(element, isValid, hasInput) {

        if (!element) {
            return;
        }

        element.classList.toggle("valid", hasInput && isValid);
        element.classList.toggle("invalid", hasInput && !isValid);

        const icon = element.querySelector(".rule-icon");

        if (icon) {
            if (!hasInput) {
                icon.textContent = "○";
            } else {
                icon.textContent = isValid ? "✓" : "✗";
            }
        }

    }


    function checkPassword() {

        const password = passwordField.value;
        const username = usernameField ? usernameField.value : "";
        const email = emailField ? emailField.value : "";

        const hasInput = password.length > 0;

        // Rule 1: At least 8 characters.
        updateRule(
            rules.length,
            password.length >= 8,
            hasInput
        );

        // Rule 2: Not entirely numeric.
        updateRule(
            rules.number,
            !/^\d+$/.test(password),
            hasInput
        );

        // Rule 3: Not in our example list of common passwords.
        const commonPasswords = [
            "password",
            "password123",
            "12345678",
            "qwerty123",
            "admin123"
        ];

        updateRule(
            rules.common,
            !commonPasswords.includes(password.toLowerCase()),
            hasInput
        );

        // Rule 4: Not too similar to username or email.
        const passwordLower = password.toLowerCase();
        const usernameLower = username.toLowerCase();
        const emailName = email.split("@")[0].toLowerCase();

        const similarToUsername =
            usernameLower.length >= 3 &&
            passwordLower.includes(usernameLower);

        const similarToEmail =
            emailName.length >= 3 &&
            passwordLower.includes(emailName);

        updateRule(
            rules.similar,
            !similarToUsername && !similarToEmail,
            hasInput
        );

    }


    // Update indicators while typing.
    passwordField.addEventListener("input", checkPassword);

    if (usernameField) {
        usernameField.addEventListener("input", checkPassword);
    }

    if (emailField) {
        emailField.addEventListener("input", checkPassword);
    }

    // Initialize the indicators.
    checkPassword();

});
```