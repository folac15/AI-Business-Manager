// ==========================================
// NEXAFLOW AI BUSINESS MANAGER
// AI SERVICES
// VERSION 1.1
// ==========================================


// ==========================================
// AI SERVICE CONFIGURATION
// ==========================================

const AIServiceConfig = {

    platform: "NexaFlow AI",

    version: "1.1",

    provider: "OpenRouter",

    status: "Initialized"

};


// ==========================================
// AI ASSISTANT ENGINE
// ==========================================

const AIAssistant = {

    conversationHistory: [],


    // --------------------------------------
    // ASK AI
    // --------------------------------------

    async ask(question) {

        const cleanQuestion =
            String(question || "").trim();


        if (!cleanQuestion) {

            return {

                success: false,

                answer: "Please enter a question."

            };

        }


        try {

            const response = await fetch(
                "/api/ai",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                        "application/json"

                    },

                    body: JSON.stringify({

                        question:
                        cleanQuestion,

                        conversation:
                        this.conversationHistory

                    })

                }
            );


            let result;


            try {

                result =
                    await response.json();

            } catch (error) {

                result = {

                    answer:
                    "The server returned an invalid response."

                };

            }


            if (!response.ok) {

                return {

                    success: false,

                    answer:
                        result.answer ||
                        result.error ||
                        "AI request failed."

                };

            }


            const answer =
                String(
                    result.answer || ""
                ).trim();


            if (!answer) {

                return {

                    success: false,

                    answer:
                        "The AI returned an empty answer."

                };

            }


            // ----------------------------------
            // SAVE USER MESSAGE
            // ----------------------------------

            this.conversationHistory.push({

                role: "user",

                content:
                    cleanQuestion

            });


            // ----------------------------------
            // SAVE AI MESSAGE
            // ----------------------------------

            this.conversationHistory.push({

                role: "assistant",

                content:
                    answer

            });


            // ----------------------------------
            // LIMIT LOCAL HISTORY
            // ----------------------------------

            if (
                this.conversationHistory.length >
                20
            ) {

                this.conversationHistory =
                    this.conversationHistory.slice(
                        -20
                    );

            }


            return {

                success: true,

                question:
                    cleanQuestion,

                answer:
                    answer,

                time:
                    new Date().toISOString()

            };


        } catch (error) {

            console.error(
                "AI service error:",
                error
            );


            return {

                success: false,

                answer:
                    "Sorry, I could not connect to the AI service."

            };

        }

    },


    // --------------------------------------
    // GET HISTORY
    // --------------------------------------

    history() {

        return [
            ...this.conversationHistory
        ];

    },


    // --------------------------------------
    // CLEAR HISTORY
    // --------------------------------------

    clearHistory() {

        this.conversationHistory = [];

    }

};


// ==========================================
// AI REASONING ENGINE
// ==========================================

const AIReasoning = {

    analyze(data) {

        return {

            status:
                "Analysis Complete",

            recommendation:
                "Business optimization recommended.",

            score:
                95,

            analyzedAt:
                new Date().toISOString()

        };

    }

};


// ==========================================
// BUSINESS ANALYSIS AI
// ==========================================

const BusinessAI = {

    generateInsight(businessData) {

        return {

            insight:
                "Revenue and customer engagement can be improved through automation.",

            priority:
                "High",

            generatedAt:
                new Date().toISOString(),

            businessData:
                businessData

        };

    }

};


// ==========================================
// CUSTOMER REPLY AI
// ==========================================

const CustomerReplyAI = {

    generateReply(message) {

        return {

            customerMessage:
                message,

            reply:
                "Thank you for your message. Our AI assistant has received your request and will help you shortly.",

            generatedAt:
                new Date().toISOString()

        };

    }

};


// ==========================================
// RECOMMENDATION AI
// ==========================================

const RecommendationAI = {

    recommend(data) {

        return {

            recommendation:
                "Improve automation, customer follow-up, and business analysis.",

            basedOn:
                data,

            date:
                new Date().toISOString()

        };

    }

};


// ==========================================
// LEARNING AI
// ==========================================

const LearningAI = {

    explain(topic) {

        return {

            topic:
                topic,

            explanation:
                "AI learning assistant is ready to explain this topic with examples.",

            language:
                "English"

        };

    }

};


// ==========================================
// MULTILINGUAL AI
// ==========================================

const LanguageAI = {

    currentLanguage:
        "English",


    changeLanguage(language) {

        this.currentLanguage =
            language;


        return {

            language:
                this.currentLanguage,

            status:
                "Changed"

        };

    }

};


// ==========================================
// AI TASK MANAGER
// ==========================================

const AITaskManager = {

    tasks: [],


    createTask(name) {

        const task = {

            id:
                Date.now(),

            name:
                name,

            status:
                "Created",

            createdAt:
                new Date().toISOString()

        };


        this.tasks.push(task);


        return task;

    },


    getTasks() {

        return [
            ...this.tasks
        ];

    },


    clearTasks() {

        this.tasks = [];

    }

};


// ==========================================
// AI SYSTEM STATUS
// ==========================================

function getAIServiceStatus() {

    return {

        platform:
            AIServiceConfig.platform,

        version:
            AIServiceConfig.version,

        provider:
            AIServiceConfig.provider,

        status:
            AIServiceConfig.status,

        modules: [

            "AI Assistant",

            "AI Reasoning",

            "Business Analysis",

            "Customer Reply",

            "Recommendations",

            "Learning AI",

            "Language AI",

            "Task Manager"

        ]

    };

}


// ==========================================
// MASTER AI OBJECT
// ==========================================

const AIBusinessManagerAI = {

    config:
        AIServiceConfig,

    assistant:
        AIAssistant,

    reasoning:
        AIReasoning,

    business:
        BusinessAI,

    customerReply:
        CustomerReplyAI,

    recommendation:
        RecommendationAI,

    learning:
        LearningAI,

    language:
        LanguageAI,

    tasks:
        AITaskManager,

    status:
        getAIServiceStatus

};


// ==========================================
// MAKE AVAILABLE GLOBALLY
// ==========================================

window.AIBusinessManagerAI =
    AIBusinessManagerAI;


window.AIAssistant =
    AIAssistant;


console.log(
    "NexaFlow AI Services Loaded",
    AIBusinessManagerAI
);
