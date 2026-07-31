function showMessage() {
    alert("AI Business Manager is ready!");
}

/* ==========================
   AUTO LOAD
========================== */

window.onload = function () {

    if (typeof loadPosts === "function" && document.getElementById("postList")) {
        loadPosts();
    }

};

/* ==========================
   POSTS MANAGEMENT
========================== */

function createPost() {

    const postText = document.getElementById("postText");

    if (!postText) return;

    let text = postText.value;

    if (text.trim() === "") {
        alert("Please write something first.");
        return;
    }

    let posts = JSON.parse(localStorage.getItem("posts")) || [];

    posts.push(text);

    localStorage.setItem("posts", JSON.stringify(posts));

    alert("Post saved successfully!");

    postText.value = "";

    loadPosts();
}

function loadPosts() {

    let area = document.getElementById("postList");

    if (!area) return;

    let posts = JSON.parse(localStorage.getItem("posts")) || [];

    if (posts.length === 0) {
        area.innerHTML = "No posts available yet.";
        return;
    }

    area.innerHTML = "";

    posts.forEach(function (post, index) {

        area.innerHTML +=
            "<p><b>Post " +
            (index + 1) +
            ":</b><br>" +
            post +
            "</p><hr>";

    });

}

/* ==========================
   SETTINGS
========================== */

function saveSettings() {

    const businessName = document.getElementById("businessName");
    const phone = document.getElementById("phone");

    if (!businessName || !phone) return;

    if (businessName.value === "" || phone.value === "") {

        alert("Please complete all information.");
        return;

    }

    localStorage.setItem("businessName", businessName.value);
    localStorage.setItem("phone", phone.value);

    alert("Settings saved successfully!");

}

/* ==========================
   MARKETING POST GENERATOR
========================== */

function generatePost() {

    const requestBox = document.getElementById("marketingRequest");
    const resultBox = document.getElementById("marketingResult");

    if (!requestBox || !resultBox) return;

    let request = requestBox.value.toLowerCase();

    let result = "";

    if (request.includes("poultry") || request.includes("chicken")) {

        result = "Fresh quality chickens available! Healthy, well-raised birds at affordable prices. Contact us today.";

    } else if (request.includes("school")) {

        result = "Give your children the best education experience with quality teaching and guidance.";

    } else {

        result = "Discover our quality products and services. Contact us today.";

    }

    resultBox.innerHTML = result;

}
