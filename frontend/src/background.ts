// Runs in the background, Individually bundled by vite.
// Store the state of all the tabs in here.

import type { Message, custResponse, State } from "../types.ts";

const endpoint = 'http://127.0.0.1:5000/prompt'

let GlobalLog : string = '';
const TabStates = new Map<number, State>();

// Makes sure the message is valid;
function isMessage(obj: unknown): obj is Message {
    return (
        typeof obj === 'object' &&
        obj !== null &&
        'action' in obj && 
        typeof (obj as any).action === 'string'
    );
}

// Listen for messages. messages from popup.html.
// Return true only if you are returning something and you want to keep the connection alive.
browser.runtime.onMessage.addListener((
    message : Message, 
    sender, 
    sendResponse: (response : custResponse | string | State) => void
) : boolean => {

    GlobalLog = GlobalLog.concat(
        getTimeStamp(),
        " [POPUP -> BACKGROUND]",
        ' Message : ',
        String(message),
        "\n"
    );

    if (!isMessage(message)) {
        GlobalLog = GlobalLog.concat(
            getTimeStamp(),
            " [ERROR] Failed to understand message",
            String(message),
            "\n"
        );
        return false;
    }
    
    if (message.action === 'GET_STATE') {
        const tabID = message.payload!.tabID!;
        Promise.resolve(getState(tabID)).then(sendResponse);
        return true;
    } else if (message.action === 'OPEN_LOG') {
        openLogs();
        return false;
    } else if (message.action === 'PROMPT') {
        const tabID = message.payload!.tabID!;
        (async () => {
            try {

                browser.tabs.sendMessage(tabID, { action: "GET_HTML" })
                .then(html => fetch(endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ prompt: message.payload!.prompt!, context: html }),
                }))
                .then(raw => raw.json())
                .then(data => sendResponse(data))
                .catch(err => {
                    console.error("Failed to get HTML or fetch:", err);
                          sendResponse({
                              success: false,
                              error: err instanceof Error ? err.message : String(err),
                          } as custResponse);
                });

            } catch (err) {
                console.error("Failed to get HTML or fetch:", err);
                sendResponse({
                    success: false,
                    error: err instanceof Error ? err.message : String(err),
                } as custResponse);
            }
        })();

        return true;    
    } else if (message.action === 'SET_STATE') {
        const tabID = message.payload!.tabID!;
        const newState : State = {
            prompt : message.payload!.prompt!,
            button : message.payload!.button!,
            output : message.payload!.output!,
            generating : false
        }
        TabStates.set(tabID, newState);
        return false;
    }

    GlobalLog = GlobalLog.concat(
        getTimeStamp(),
        " [ERROR] Unknown action, tabid : ",
        String(message),
        "\n"
    );

    return false;

});

function getTimeStamp() : string {
    return new Date().toISOString();
}

/*
    Returns the state of a particular tab.
    args : 
        tabID : number
*/
function getState(tabID : number) : State {
    if (!TabStates.has(tabID)) {
        const initState : State = {
            prompt : "",
            output : "Output will be shown here",
            button : "idle",
            generating : false
        };

        TabStates.set(
            tabID, 
            initState
        );

        GlobalLog = GlobalLog.concat(getTimeStamp(), " [NEW TAB STATE], tabid : ", String(tabID), " Created\n");
    }

    return TabStates.get(tabID)!;
}

async function openLogs() {
    console.log(GlobalLog);
} 

