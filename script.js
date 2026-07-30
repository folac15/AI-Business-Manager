function showMessage(){

    alert("AI Business Manager is ready!");

}


/* ==========================
   POSTS MANAGEMENT
========================== */


function createPost(){

    let text =
    document.getElementById("postText").value;


    if(text.trim()==""){

        alert("Please write something first.");
        return;

    }


    let posts =
    JSON.parse(localStorage.getItem("posts")) || [];


    posts.push(text);


    localStorage.setItem(
        "posts",
        JSON.stringify(posts)
    );


    alert("Post saved successfully!");


    document.getElementById("postText").value="";

}



function loadPosts(){

    let posts =
    JSON.parse(localStorage.getItem("posts")) || [];


    let area =
    document.getElementById("postList");


    if(!area){

        return;

    }


    if(posts.length==0){

        area.innerHTML =
        "No posts available yet.";

        return;

    }


    area.innerHTML="";


    posts.forEach(function(post,index){


        area.innerHTML +=

        "<p><b>Post "
        +(index+1)+
        ":</b><br>"
        +post+
        "</p><hr>";


    });


}


/* ==========================
   SETTINGS
========================== */


function saveSettings(){

    let name =
    document.getElementById("businessName").value;


    let phone =
    document.getElementById("phone").value;


    if(name=="" || phone==""){

        alert("Please complete all information.");

        return;

    }


    localStorage.setItem(
        "businessName",
        name
    );


    localStorage.setItem(
        "phone",
        phone
    );


    alert("Settings saved successfully!");

}





/* ==========================
   MARKETING POST GENERATOR
========================== */


function generatePost(){


    let request =
    document
    .getElementById("marketingRequest")
    .value
    .toLowerCase();


    let result="";


    if(
        request.includes("poultry")
        ||
        request.includes("chicken")
    ){

        result =
        "Fresh quality chickens available! Healthy, well-raised birds at affordable prices. Contact us today.";

    }


    else if(
        request.includes("school")
    ){

        result =
        "Give your children the best education experience with quality teaching and guidance.";

    }


    else{


        result =
        "Discover our quality products and services. Contact us today.";

    }


    document
    .getElementById("marketingResult")
    .innerHTML=result;


}
