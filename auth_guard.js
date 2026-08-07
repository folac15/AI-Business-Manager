// ===============================
// NexaFlow AI Authentication Guard
// ===============================

const token = localStorage.getItem("access_token");

// If user is not logged in
if (!token) {

    window.location.href = "login.html";

}

// Logout function
function logout(){

    localStorage.removeItem("access_token");

    window.location.href = "login.html";

                            }
