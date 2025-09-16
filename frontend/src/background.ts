// Runs in the background, Individually bundled by vite.
// Store the state of all the tabs in here.

import type { Message, custResponse, State } from "../types.ts";

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

    GlobalLog.concat(
        getTimeStamp(),
        " [POPUP -> BACKGROUND]",
        ' Message : ',
        String(message),
        "\n"
    );

    if (!isMessage(message)) {
        GlobalLog.concat(
            getTimeStamp(),
            " [ERROR] Failed to understand message",
            String(message),
            "\n"
        );
        return false;
    }
    
    if (message.action === 'GET_STATE') {
        const tabID = message.payload!.tabID!;
        console.log(tabID);
        Promise.resolve(getState(tabID)).then(sendResponse);
        return true;
    } else if (message.action === 'OPEN_LOG') {
        openLogs();
        return false;
    } else if (message.action === 'PROMPT') {

        return true;
    } else if (message.action === 'SET_STATE') {
        const tabID = message.payload!.tabID!;
        console.log(tabID);
        const newState : State = {
            prompt : message.payload!.prompt!,
            button : message.payload!.button!,
            output : message.payload!.output!,
            generating : false
        }
        TabStates.set(tabID, newState);
        return false;
    }

    GlobalLog.concat(
        getTimeStamp(),
        " [ERROR] Unknown action, tabid : ",
        String(message),
        "\n"
    );

    return false;

});

let GlobalLog : string = 'avbauvybaufvyba';
let TabStates = new Map<number, State>();

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

        GlobalLog.concat(getTimeStamp(), " [NEW TAB STATE], tabid : ", String(tabID), " Created\n");
    }

    return TabStates.get(tabID)!;
}

async function openLogs() {
    const encoded = encodeURIComponent(GlobalLog);
    const url = browser.runtime.getURL(`log.html?data=${encoded}`);
    await browser.tabs.create({ url });
} 

