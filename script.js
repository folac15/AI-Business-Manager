function showMessage(){
    alert("AI Business Manager is ready!");
}
function createPost(){

    let text = document.getElementById("postText").value;

    if(text == ""){

        alert("Please write something first.");

    }
    else{

        let posts = JSON.parse(localStorage.getItem("posts")) || [];

        posts.push(text);

        localStorage.setItem("posts", JSON.stringify(posts));

        alert("Post saved successfully!");

        document.getElementById("postText").value = "";

    }

}
function replyCustomer(){

    let reply = prompt("Write your reply to the customer:");

    if(reply != null && reply != ""){
        alert("Reply sent:\n\n" + reply);
    }
    else{
        alert("No reply written.");
    }

}
function saveSettings(){

    let name = document.getElementById("businessName").value;
    let phone = document.getElementById("phone").value;

    if(name == "" || phone == ""){

        alert("Please complete all information.");

    }
    else{

        localStorage.setItem("businessName", name);
        localStorage.setItem("phone", phone);

        alert("Settings saved successfully!");

    }

}
function loadPosts(){

    let posts = JSON.parse(localStorage.getItem("posts")) || [];

    let postArea = document.getElementById("postList");

    if(posts.length == 0){

        postArea.innerHTML = "No posts available yet.";

    }
    else{

        postArea.innerHTML = "";

        posts.forEach(function(post, index){

            postArea.innerHTML += 
            "<p><b>Post " + (index + 1) + ":</b><br>" 
            + post + 
            "</p><hr>";

        });

    }

}
async function askAI(){

    let question = document.getElementById("question").value;

    let responseBox = document.getElementById("aiResponse");

    responseBox.innerHTML = "Thinking...";

    try {

        let response = await fetch("https://ai-business-manager.onrender.com/api/ai", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                question: question
            })

        });


        let data = await response.json();

        responseBox.innerHTML = data.response;


    } catch(error){

        responseBox.innerHTML = 
        "Unable to connect to AI server.";

    }

}
function generatePost(){

    let request = document.getElementById("marketingRequest").value.toLowerCase();

    let result = "";

    if(request.includes("poultry") || request.includes("chicken")){

        result = "Fresh quality chickens available! Healthy, well-raised birds at affordable prices. Contact us today to place your order.";

    }

    else if(request.includes("school")){

        result = "Give your children the best education experience. Quality teaching, guidance and success-focused learning.";

    }

    else{

        result = "Discover our quality products and services. We are ready to serve you. Contact us today.";

    }


    document.getElementById("marketingResult").innerHTML = result;

}