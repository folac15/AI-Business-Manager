// ======================================================
// NexaFlow AI - Authentication Guard
// ======================================================

const SUPABASE_URL =
"https://xfjroysinifwncfjvrsg.supabase.co";

const SUPABASE_ANON_KEY =
"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhmanJveXNpbmlmd25jZmp2cnNnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQyNTU3NDAsImV4cCI6MjA5OTgzMTc0MH0.wxKe_cs9n78YhF5nw63crh3pxNnkQW7VGjcqzv3adPs";


// ======================================================
// CHECK LOGIN SESSION
// ======================================================

async function checkAuth(){

    let accessToken =
        localStorage.getItem("access_token");

    let refreshToken =
        localStorage.getItem("refresh_token");


    // No session at all
    if(!accessToken){

        redirectToLogin();

        return;

    }


    try{

        // First, test the current access token
        let response = await fetch(

            SUPABASE_URL + "/auth/v1/user",

            {

                method:"GET",

                headers:{

                    "apikey":
                    SUPABASE_ANON_KEY,

                    "Authorization":
                    "Bearer " + accessToken

                }

            }

        );


        // Current access token is valid
        if(response.ok){

            const user =
                await response.json();


            if(user && user.id){

                localStorage.setItem(
                    "user_id",
                    user.id
                );

                console.log(
                    "NexaFlow session valid:",
                    user.id
                );

                return;

            }

        }


        // ==================================================
        // ACCESS TOKEN EXPIRED
        // TRY REFRESH TOKEN
        // ==================================================

        if(!refreshToken){

            console.log(
                "No refresh token available."
            );

            redirectToLogin();

            return;

        }


        console.log(
            "Access token expired. Refreshing session..."
        );


        const refreshResponse =
        await fetch(

            SUPABASE_URL +
            "/auth/v1/token?grant_type=refresh_token",

            {

                method:"POST",

                headers:{

                    "apikey":
                    SUPABASE_ANON_KEY,

                    "Content-Type":
                    "application/json"

                },

                body:JSON.stringify({

                    refresh_token:
                    refreshToken

                })

            }

        );


        const refreshResult =
        await refreshResponse.json();


        console.log(
            "Supabase refresh response:",
            refreshResult
        );


        if(
            !refreshResponse.ok ||
            !refreshResult.access_token
        ){

            console.log(
                "Session refresh failed."
            );

            redirectToLogin();

            return;

        }


        // ==================================================
        // SAVE NEW SESSION
        // ==================================================

        localStorage.setItem(

            "access_token",

            refreshResult.access_token

        );


        if(refreshResult.refresh_token){

            localStorage.setItem(

                "refresh_token",

                refreshResult.refresh_token

            );

        }


        // Save user ID
        if(
            refreshResult.user &&
            refreshResult.user.id
        ){

            localStorage.setItem(

                "user_id",

                refreshResult.user.id

            );

        }


        console.log(
            "NexaFlow session refreshed successfully."
        );


    }catch(error){

        console.error(
            "Authentication check error:",
            error
        );


        redirectToLogin();

    }

}


// ======================================================
// REDIRECT TO LOGIN
// ======================================================

function redirectToLogin(){

    localStorage.removeItem(
        "access_token"
    );

    localStorage.removeItem(
        "refresh_token"
    );

    localStorage.removeItem(
        "user_id"
    );


    window.location.href =
    "login.html";

}


// ======================================================
// LOGOUT
// ======================================================

function logout(){

    localStorage.removeItem(
        "access_token"
    );

    localStorage.removeItem(
        "refresh_token"
    );

    localStorage.removeItem(
        "user_id"
    );

    localStorage.removeItem(
        "pending_business_profile"
    );


    window.location.href =
    "login.html";

}


// ======================================================
// START AUTHENTICATION CHECK
// ======================================================

checkAuth();
