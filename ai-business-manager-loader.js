// ==========================================
// AI BUSINESS MANAGER LOADER
// FINAL CONNECTOR FILE
// PART 1
// ==========================================


// LOADER CONFIGURATION

const LoaderConfig = {

    name: "AI Business Manager Loader",

    version: "1.0",

    status: "Initializing"

};




// MODULE CHECKER

const ModuleChecker = {


    modules: [],



    check(name, object){


        const result = {


            module: name,


            loaded: typeof object !== "undefined",


            status:
            typeof object !== "undefined"
            ? "Ready"
            : "Missing"


        };


        this.modules.push(result);


        return result;


    },



    getResults(){


        return this.modules;


    }



};




// LOAD SYSTEM MODULES

function initializeBusinessManager(){


    LoaderConfig.status = "Running";



    ModuleChecker.check(

        "Automation Core",

        window.AIBusinessManagerCore

    );



    ModuleChecker.check(

        "Database API",

        window.AIBusinessManagerDatabase

    );



    ModuleChecker.check(

        "AI Services",

        window.AIBusinessManagerAI

    );



    ModuleChecker.check(

        "Integrations",

        window.AIBusinessManagerIntegrations

    );



    ModuleChecker.check(

        "Main Controller",

        window.AIBusinessManagerController

    );



    return ModuleChecker.getResults();


}
// ==========================================
// PART 2
// FINAL STATUS + GLOBAL EXPORT
// ==========================================


// FINAL SYSTEM REPORT

function getLoaderStatus(){

    return {

        system:
        LoaderConfig.name,

        version:
        LoaderConfig.version,

        status:
        LoaderConfig.status,

        modules:
        ModuleChecker.getResults(),

        ready:
        ModuleChecker.modules.every(

            module => module.loaded

        )

    };

}




// MASTER LOADER OBJECT

const AIBusinessManagerLoader = {


    config:
    LoaderConfig,


    check:
    initializeBusinessManager,


    status:
    getLoaderStatus


};




// GLOBAL ACCESS

window.AIBusinessManagerLoader =
AIBusinessManagerLoader;




// START CHECK

initializeBusinessManager();



console.log(

"AI Business Manager Loader Active",

AIBusinessManagerLoader.status()

);
